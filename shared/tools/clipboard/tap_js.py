"""
Payload JavaScript del interceptor de portapapeles ("tap") de Guacamole.

Se inyecta UNA vez por sesión web y deja en `window.__rpa` un objeto con:

  - onclipboard interceptado: captura el portapapeles remoto apenas sale del
    túnel, esperando StringReader.onend para no entregar fragmentos parciales.
  - Cola de eventos con número de secuencia monótono (no "último gana").
  - Envío de teclas por el túnel (sendKeyEvent), sin depender del foco del SO.
  - Liberación defensiva de modificadores (si Ctrl queda hundido en el remoto,
    todo lo que siga se convierte en atajos: es un modo de falla catastrófico).
  - Estado de cliente y de túnel, incluida la señal de "inestable" que el
    túnel ya calcula solo (unstableThreshold, 1500 ms por defecto).
  - Operaciones compuestas que hacen TODO adentro del navegador, para gastar
    un solo viaje de red por lectura en vez de cuatro.

Las constantes de estado se leen en runtime desde Guacamole.Client.State y
Guacamole.Tunnel.State: no se hardcodean números, porque la documentación no
los fija y pueden variar entre versiones.
"""

# ---------------------------------------------------------------------------
# Instalación. Devuelve {ok, ...salud} o {ok:false, motivo}.
# Idempotente: si ya hay un tap sano sobre el MISMO cliente, no reinstala.
# ---------------------------------------------------------------------------
TAP_INSTALAR = r"""
(() => {
  "use strict";

  const VERSION = "1.0.0";
  const MODIFICADORES = [0xFFE1, 0xFFE2, 0xFFE3, 0xFFE4, 0xFFE9, 0xFFEA];

  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

  function invertir(obj) {
    const m = {};
    try {
      for (const k of Object.keys(obj || {})) { m[obj[k]] = k; }
    } catch (e) {}
    return m;
  }

  // ---------- Localización del cliente Guacamole ----------
  function esClienteGuac(v) {
    return v && typeof v.createClipboardStream === "function"
             && typeof v.sendKeyEvent === "function";
  }

  function resolverCandidato(c, path) {
    if (!c) return null;
    if (esClienteGuac(c)) return { client: c, managed: null, path: path };
    if (esClienteGuac(c.client)) return { client: c.client, managed: c, path: path + ".client" };
    return null;
  }

  function resolverCliente() {
    if (!window.angular) return null;
    const selectores = [".client-main", ".client-tile", ".display"];
    for (const sel of selectores) {
      const el = document.querySelector(sel);
      if (!el) continue;
      let scope = null;
      try {
        const ng = window.angular.element(el);
        scope = (ng.isolateScope && ng.isolateScope()) || (ng.scope && ng.scope());
      } catch (e) {}
      if (!scope) continue;
      const hit =
        resolverCandidato(scope.client, "iso(" + sel + ").client") ||
        resolverCandidato(scope.focusedClient, "iso(" + sel + ").focusedClient") ||
        resolverCandidato(scope.managedClient, "iso(" + sel + ").managedClient");
      if (hit) return hit;
    }
    return null;
  }

  function resolverTunel(hit) {
    const candidatos = [
      hit.client && hit.client.tunnel,
      hit.managed && hit.managed.tunnel,
      hit.managed && hit.managed.client && hit.managed.client.tunnel
    ];
    for (const t of candidatos) {
      if (t && typeof t.sendMessage === "function") return t;
    }
    return null;
  }

  // ---------- Validación declarativa (espejo de specs.py) ----------
  function cumpleSpec(texto, spec) {
    if (!spec) return true;
    const t = texto == null ? "" : String(texto);
    switch (spec.tipo) {
      case "no_vacio":  return t.trim().length > 0;
      case "igual":     return t === (spec.txt || "");
      case "min_len":   return t.length >= spec.n;
      case "max_len":   return t.length <= spec.n;
      case "contiene":
        return spec.ci
          ? t.toUpperCase().indexOf(String(spec.txt).toUpperCase()) !== -1
          : t.indexOf(String(spec.txt)) !== -1;
      case "en":
        return (spec.valores || []).map(String).indexOf(t.trim()) !== -1;
      case "primer_token_en": {
        const partes = t.trim().split(/\s+/);
        const tok = (partes[0] || "").toUpperCase();
        return (spec.valores || []).map((v) => String(v).toUpperCase()).indexOf(tok) !== -1;
      }
      case "min_lineas": {
        const n = t.split(/\r?\n/).filter((l) => l.trim().length > 0).length;
        return n >= spec.n;
      }
      case "min_columnas": {
        const ls = t.split(/\r?\n/).filter((l) => l.trim().length > 0);
        if (!ls.length) return false;
        const sep = spec.sep || "\t";
        return ls.some((l) => l.split(sep).length >= spec.n);
      }
      case "regex":
        try { return new RegExp(spec.re, spec.flags || "").test(t); }
        catch (e) { return true; }
      case "y": return (spec.de || []).every((s) => cumpleSpec(t, s));
      case "o": return (spec.de || []).some((s) => cumpleSpec(t, s));
      default:  return true;
    }
  }

  // ---------- Instalación ----------
  function instalar() {
    if (!window.Guacamole || !window.Guacamole.StringReader || !window.Guacamole.StringWriter) {
      return { ok: false, motivo: "guacamole_api_incompleta" };
    }

    const hit = resolverCliente();
    if (!hit || !hit.client) return { ok: false, motivo: "client_not_found" };

    const token = "rpa_" + Math.random().toString(36).slice(2) + "_" + Date.now();
    const mapaCliente = invertir(window.Guacamole.Client && window.Guacamole.Client.State);
    const mapaTunel   = invertir(window.Guacamole.Tunnel && window.Guacamole.Tunnel.State);

    const R = {
      version: VERSION,
      token: token,
      seq: 0,
      eventos: [],
      maxEventos: 20,
      ocupado: false,
      modsPresionados: [],
      estadoCliente: null,
      estadoClienteNombre: null,
      estadoTunel: null,
      estadoTunelNombre: null,
      desconexiones: 0,
      inestables: 0,
      ultimoErrorTunel: null,
      clientPath: hit.path,
      tunnelHook: false,
      handler: null
    };

    // --- Interceptor de entrada ---
    const handler = function (stream, mimetype) {
      let buf = "";
      const publicar = function (extra) {
        R.seq += 1;
        const ev = { seq: R.seq, texto: buf, mimetype: mimetype, ts: Date.now() };
        if (extra) ev.error = extra;
        R.eventos.push(ev);
        while (R.eventos.length > R.maxEventos) R.eventos.shift();
      };
      try {
        const reader = new window.Guacamole.StringReader(stream);
        reader.ontext = function (t) { buf += t; };
        reader.onend = function () { publicar(null); };
      } catch (e) {
        publicar(String(e));
      }
    };

    hit.client.onclipboard = handler;
    R.handler = handler;
    try { hit.client.__rpaToken = token; } catch (e) {}

    // --- Estado del cliente ---
    try {
      if (typeof hit.client.currentState === "number") {
        R.estadoCliente = hit.client.currentState;
        R.estadoClienteNombre = mapaCliente[R.estadoCliente] || String(R.estadoCliente);
      }
    } catch (e) {}

    const prevEstadoCliente = hit.client.onstatechange;
    hit.client.onstatechange = function (state) {
      R.estadoCliente = state;
      R.estadoClienteNombre = mapaCliente[state] || String(state);
      if ((R.estadoClienteNombre || "").toUpperCase().indexOf("DISCONNECT") !== -1) {
        R.desconexiones += 1;
      }
      if (prevEstadoCliente) { try { prevEstadoCliente(state); } catch (e) {} }
    };

    // --- Estado del túnel (aviso de inestabilidad y cierre) ---
    const tun = resolverTunel(hit);
    if (tun) {
      R.tunnelHook = true;
      const prevEstadoTunel = tun.onstatechange;
      tun.onstatechange = function (state) {
        R.estadoTunel = state;
        R.estadoTunelNombre = mapaTunel[state] || String(state);
        const n = (R.estadoTunelNombre || "").toUpperCase();
        if (n.indexOf("UNSTABLE") !== -1) R.inestables += 1;
        if (n.indexOf("CLOSED") !== -1) R.desconexiones += 1;
        if (prevEstadoTunel) { try { prevEstadoTunel(state); } catch (e) {} }
      };
      const prevError = tun.onerror;
      tun.onerror = function (status) {
        try {
          R.ultimoErrorTunel = {
            code: status && status.code,
            msg: status && status.message,
            ts: Date.now()
          };
        } catch (e) {}
        if (prevError) { try { prevError(status); } catch (e) {} }
      };
    }

    // ---------- Salud e identidad ----------
    R.sano = function () {
      try {
        const h = resolverCliente();
        if (!h || !h.client) return false;
        if (h.client.__rpaToken !== R.token) return false;
        if (h.client.onclipboard !== R.handler) return false;
        return true;
      } catch (e) { return false; }
    };

    R.conectado = function () {
      const n = (R.estadoClienteNombre || "").toUpperCase();
      if (n === "CONNECTED") return true;
      try {
        const h = resolverCliente();
        if (h && h.client && typeof h.client.currentState === "number") {
          const vivo = (mapaCliente[h.client.currentState] || "").toUpperCase();
          if (vivo) return vivo === "CONNECTED";
        }
      } catch (e) {}
      // Estado desconocido: no bloqueamos (mismo criterio que el bridge previo).
      return n === "";
    };

    R.inestable = function () {
      return (R.estadoTunelNombre || "").toUpperCase().indexOf("UNSTABLE") !== -1;
    };

    R.salud = function () {
      return {
        version: R.version,
        token: R.token,
        seq: R.seq,
        sano: R.sano(),
        conectado: R.conectado(),
        inestable: R.inestable(),
        estadoCliente: R.estadoClienteNombre,
        estadoTunel: R.estadoTunelNombre,
        desconexiones: R.desconexiones,
        inestables: R.inestables,
        ultimoErrorTunel: R.ultimoErrorTunel,
        clientPath: R.clientPath,
        tunnelHook: R.tunnelHook,
        ocupado: R.ocupado,
        enCola: R.eventos.length
      };
    };

    // ---------- Escritura al portapapeles remoto ----------
    R.escribirRemoto = function (texto) {
      try {
        const h = resolverCliente();
        if (!h || !h.client) return false;
        const stream = h.client.createClipboardStream("text/plain");
        const writer = new window.Guacamole.StringWriter(stream);
        writer.sendText(String(texto));
        writer.sendEnd();
        return true;
      } catch (e) { return false; }
    };

    // ---------- Teclado por el túnel ----------
    R.tecla = function (keysym, presionada) {
      const h = resolverCliente();
      if (!h || !h.client) return false;
      h.client.sendKeyEvent(presionada ? 1 : 0, keysym);
      return true;
    };

    R.combinacion = function (keysyms) {
      const enviados = [];
      try {
        for (let i = 0; i < keysyms.length; i++) {
          R.tecla(keysyms[i], true);
          enviados.push(keysyms[i]);
          R.modsPresionados.push(keysyms[i]);
        }
      } finally {
        for (let i = enviados.length - 1; i >= 0; i--) {
          try { R.tecla(enviados[i], false); } catch (e) {}
          const idx = R.modsPresionados.lastIndexOf(enviados[i]);
          if (idx !== -1) R.modsPresionados.splice(idx, 1);
        }
      }
      return true;
    };

    R.tipear = function (keysyms) {
      for (let i = 0; i < keysyms.length; i++) {
        R.tecla(keysyms[i], true);
        R.tecla(keysyms[i], false);
      }
      return true;
    };

    // Nunca dejar un modificador hundido en el remoto.
    R.liberarModificadores = function () {
      const pendientes = R.modsPresionados.slice();
      R.modsPresionados = [];
      for (let i = pendientes.length - 1; i >= 0; i--) {
        try { R.tecla(pendientes[i], false); } catch (e) {}
      }
      for (let i = 0; i < MODIFICADORES.length; i++) {
        try { R.tecla(MODIFICADORES[i], false); } catch (e) {}
      }
      return true;
    };

    // ---------- Espera de evento ----------
    R.eventosDesde = function (seq) {
      return R.eventos.filter(function (e) { return e.seq > seq && !e.__usado; });
    };

    R.resumenDesde = function (seq) {
      return R.eventos.filter(function (e) { return e.seq > seq; }).map(function (e) {
        return {
          seq: e.seq,
          len: (e.texto || "").length,
          prev: (e.texto || "").slice(0, 40),
          ts: e.ts
        };
      });
    };

    // Separa dos preguntas que antes estaban mezcladas:
    //   1) ¿llegó un evento del portapapeles remoto?      -> transporte
    //   2) ¿ese evento tiene la forma esperada?           -> negocio
    //
    // El spec guía los reintentos, NO decide el fracaso. Un vacío confirmado
    // (llegó un evento con texto en blanco) es un dato legítimo: puede ser una
    // grilla sin filas. Devolverlo como falla técnica era un error.
    //
    // Además: una vez que llegó AL MENOS un evento, no tiene sentido agotar el
    // timeout completo esperando uno mejor. Se aplica una gracia corta.
    R.esperarEvento = function (opts) {
      const desdeSeq = opts.desdeSeq;
      const timeoutMs = opts.timeoutMs || 8000;
      const graciaMs = opts.graciaMs === undefined ? 800 : opts.graciaMs;
      const spec = opts.spec || null;
      const veneno = (opts.veneno === undefined) ? null : opts.veneno;

      return new Promise(function (resolve) {
        const t0 = Date.now();
        let descartados = 0;
        let venenoVisto = 0;
        let eventosVistos = 0;
        let ultimo = null;          // último evento recibido, cumpla o no el spec
        let tPrimerEvento = null;

        function buscar() {
          const candidatos = R.eventosDesde(desdeSeq);
          for (let i = 0; i < candidatos.length; i++) {
            const ev = candidatos[i];

            if (veneno !== null && ev.texto === veneno) {
              ev.__usado = true; venenoVisto += 1; continue;
            }

            eventosVistos += 1;
            if (tPrimerEvento === null) tPrimerEvento = Date.now();

            if (!cumpleSpec(ev.texto, spec)) {
              ev.__usado = true;
              descartados += 1;
              ultimo = ev;
              continue;
            }

            ev.__usado = true;
            return ev;
          }
          return null;
        }

        function terminar() {
          resolve({
            ev: null,
            ultimo: ultimo,
            eventosVistos: eventosVistos,
            descartados: descartados,
            venenoVisto: venenoVisto
          });
        }

        function tick() {
          const ev = buscar();
          if (ev) {
            resolve({
              ev: ev, ultimo: ev, eventosVistos: eventosVistos,
              descartados: descartados, venenoVisto: venenoVisto
            });
            return;
          }

          const ahora = Date.now();
          if (ahora - t0 >= timeoutMs) { terminar(); return; }

          // Ya llegó algo: damos una gracia corta por si viene uno mejor,
          // en vez de quemar los 8 s completos.
          if (tPrimerEvento !== null && ahora - tPrimerEvento >= graciaMs) {
            terminar(); return;
          }

          setTimeout(tick, 25);
        }
        tick();
      });
    };

    // ---------- Operaciones compuestas ----------

    // Un solo viaje de red: envenena, dispara Ctrl+C por el túnel, espera,
    // valida y devuelve. Requiere GUACAMOLE_INPUT_MODE=tunnel.
    R.opLeer = function (opts) {
      if (R.ocupado) return Promise.resolve({ ok: false, motivo: "concurrencia" });
      R.ocupado = true;
      const t0 = Date.now();
      const seq0 = R.seq;

      return (async function () {
        try {
          if (!R.conectado()) {
            return { ok: false, motivo: "tunel_no_conectado", estado: R.estadoClienteNombre };
          }

          let venenoPuesto = false;
          if (opts.veneno) {
            venenoPuesto = R.escribirRemoto(opts.veneno);
            if (venenoPuesto) await esperar(opts.venenoSettleMs || 120);
          }

          if (opts.seleccionarTodo) {
            R.combinacion(opts.keysSeleccionar);
            await esperar(60);
          }
          R.combinacion(opts.keysCopiar);

          const r = await R.esperarEvento({
            desdeSeq: seq0,
            timeoutMs: opts.timeoutMs,
            graciaMs: opts.graciaMs,
            spec: opts.spec,
            veneno: venenoPuesto ? opts.veneno : null
          });

          return R.resultadoLectura(r, seq0, t0);
        } catch (e) {
          return { ok: false, motivo: "excepcion", error: String(e && e.stack ? e.stack : e) };
        } finally {
          R.liberarModificadores();
          R.ocupado = false;
        }
      })();
    };

    // Modo compatible (GUACAMOLE_INPUT_MODE=os): Python dispara las teclas
    // con pywinauto entre armar y esperar. Tres viajes, pero sigue usando el
    // tap y por lo tanto NO toca pyperclip.
    R.opArmar = function (opts) {
      const seq0 = R.seq;
      if (!R.conectado()) {
        return { ok: false, motivo: "tunel_no_conectado", estado: R.estadoClienteNombre };
      }
      let venenoPuesto = false;
      if (opts && opts.veneno) venenoPuesto = R.escribirRemoto(opts.veneno);
      return { ok: true, seq0: seq0, venenoPuesto: venenoPuesto };
    };

    // Traduce el resultado de esperarEvento a la respuesta que consume Python.
    //
    //   ok:true,  cumplioSpec:true   -> dato bueno
    //   ok:true,  cumplioSpec:false  -> LLEGÓ un evento pero no tiene la forma
    //                                  esperada (p.ej. grilla vacía: '\r\n').
    //                                  Es dato legítimo; decide la acción.
    //   ok:false, motivo:sin_eventos -> no llegó NADA: falla de transporte real
    //   ok:false, motivo:copia_vacia -> volvió el veneno: el Ctrl+C no copió
    R.resultadoLectura = function (r, seq0, t0) {
      const comun = {
        ms: Date.now() - t0,
        eventosVistos: r.eventosVistos,
        descartados: r.descartados,
        venenoVisto: r.venenoVisto,
        inestable: R.inestable()
      };

      if (r.ev) {
        return Object.assign(comun, {
          ok: true, cumplioSpec: true, texto: r.ev.texto, seq: r.ev.seq
        });
      }

      if (r.ultimo) {
        return Object.assign(comun, {
          ok: true,
          cumplioSpec: false,
          motivo: "sin_coincidencia_spec",
          texto: r.ultimo.texto,
          seq: r.ultimo.seq,
          vistos: R.resumenDesde(seq0)
        });
      }

      return Object.assign(comun, {
        ok: false,
        cumplioSpec: false,
        motivo: r.venenoVisto > 0 ? "copia_vacia" : "sin_eventos",
        vistos: R.resumenDesde(seq0)
      });
    };

    R.opEsperar = function (opts) {
      const t0 = Date.now();
      return R.esperarEvento({
        desdeSeq: opts.seq0,
        timeoutMs: opts.timeoutMs,
        graciaMs: opts.graciaMs,
        spec: opts.spec,
        veneno: opts.venenoPuesto ? opts.veneno : null
      }).then(function (r) {
        return R.resultadoLectura(r, opts.seq0, t0);
      });
    };

    // Escritura. El eco de onclipboard es OPORTUNISTA: si llega, seguimos
    // antes; si no llega, esperamos el settle. Nunca decide correctitud —
    // eso lo hace la verificación en destino, en Python.
    R.opEscribir = function (opts) {
      if (R.ocupado) return Promise.resolve({ ok: false, motivo: "concurrencia" });
      R.ocupado = true;
      const t0 = Date.now();
      const seq0 = R.seq;

      return (async function () {
        try {
          if (!R.conectado()) {
            return { ok: false, motivo: "tunel_no_conectado", estado: R.estadoClienteNombre };
          }
          if (!R.escribirRemoto(opts.texto)) {
            return { ok: false, motivo: "escritura_fallida" };
          }

          let eco = false;
          let msEco = null;
          if (opts.esperarEco) {
            const r = await R.esperarEvento({
              desdeSeq: seq0,
              timeoutMs: opts.ecoTimeoutMs || 1200,
              spec: { tipo: "igual", txt: String(opts.texto) },
              veneno: null
            });
            eco = !!r.ev;
            if (eco) msEco = Date.now() - t0;
          }

          // La espera del eco NUNCA agrega latencia sobre el settle: si el eco
          // llega antes, seguimos antes; si no llega, el tiempo ya consumido
          // cuenta como settle.
          if (!eco) {
            const restante = (opts.settleMs || 250) - (Date.now() - t0);
            if (restante > 0) await esperar(restante);
          }

          if (opts.pegar) {
            if (opts.seleccionarTodo) {
              R.combinacion(opts.keysSeleccionar);
              await esperar(60);
            }
            R.combinacion(opts.keysPegar);
          }

          return { ok: true, eco: eco, msEco: msEco, ms: Date.now() - t0, inestable: R.inestable() };
        } catch (e) {
          return { ok: false, motivo: "excepcion", error: String(e && e.stack ? e.stack : e) };
        } finally {
          R.liberarModificadores();
          R.ocupado = false;
        }
      })();
    };

    // Tipeo por el túnel (reemplaza el campo: selecciona todo y escribe).
    R.opTipear = function (opts) {
      if (R.ocupado) return Promise.resolve({ ok: false, motivo: "concurrencia" });
      R.ocupado = true;
      const t0 = Date.now();

      return (async function () {
        try {
          if (!R.conectado()) {
            return { ok: false, motivo: "tunel_no_conectado", estado: R.estadoClienteNombre };
          }
          if (opts.seleccionarTodo) {
            R.combinacion(opts.keysSeleccionar);
            await esperar(60);
          }
          R.tipear(opts.keysyms);
          return { ok: true, ms: Date.now() - t0, inestable: R.inestable() };
        } catch (e) {
          return { ok: false, motivo: "excepcion", error: String(e && e.stack ? e.stack : e) };
        } finally {
          R.liberarModificadores();
          R.ocupado = false;
        }
      })();
    };

    window.__rpa = R;
    const s = R.salud();
    s.ok = true;
    s.yaEstaba = false;
    return s;
  }

  // Reinstala si el cliente cambió (reconexión de Angular) o si alguien
  // sobrescribió nuestro handler. Un reload de página borra window.__rpa y
  // cae naturalmente a instalar().
  try {
    if (window.__rpa && typeof window.__rpa.sano === "function" && window.__rpa.sano()) {
      const s = window.__rpa.salud();
      s.ok = true;
      s.yaEstaba = true;
      return s;
    }
  } catch (e) {}

  return instalar();
})()
"""


# ---------------------------------------------------------------------------
# Operaciones. Cada una es una función flecha que recibe un dict de opciones.
# ---------------------------------------------------------------------------

OP_SALUD = r"""
() => (window.__rpa && typeof window.__rpa.salud === "function")
        ? Object.assign(window.__rpa.salud(), { ok: true })
        : { ok: false, motivo: "tap_ausente" }
"""

OP_LEER = r"""
(o) => (window.__rpa && window.__rpa.sano && window.__rpa.sano())
         ? window.__rpa.opLeer(o)
         : { ok: false, motivo: "tap_invalido" }
"""

OP_ARMAR = r"""
(o) => (window.__rpa && window.__rpa.sano && window.__rpa.sano())
         ? window.__rpa.opArmar(o)
         : { ok: false, motivo: "tap_invalido" }
"""

OP_ESPERAR = r"""
(o) => (window.__rpa && window.__rpa.sano && window.__rpa.sano())
         ? window.__rpa.opEsperar(o)
         : { ok: false, motivo: "tap_invalido" }
"""

OP_ESCRIBIR = r"""
(o) => (window.__rpa && window.__rpa.sano && window.__rpa.sano())
         ? window.__rpa.opEscribir(o)
         : { ok: false, motivo: "tap_invalido" }
"""

OP_TIPEAR = r"""
(o) => (window.__rpa && window.__rpa.sano && window.__rpa.sano())
         ? window.__rpa.opTipear(o)
         : { ok: false, motivo: "tap_invalido" }
"""

OP_LIBERAR_MODS = r"""
() => (window.__rpa && window.__rpa.liberarModificadores)
        ? { ok: !!window.__rpa.liberarModificadores() }
        : { ok: false, motivo: "tap_ausente" }
"""

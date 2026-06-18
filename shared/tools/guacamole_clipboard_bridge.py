import hashlib
import logging
from typing import Any

logger_default = logging.getLogger(__name__)


GUAC_REMOTE_CLIPBOARD_JS = """
async (texto) => {
    const result = {
        ok: false,
        reason: null,
        error: null,
        hasGuacamole: !!window.Guacamole,
        hasStringWriter: !!(window.Guacamole && window.Guacamole.StringWriter),
        foundClient: false,
        clientPath: null,
        connected: null
    };

    try {
        if (!window.Guacamole || !window.Guacamole.StringWriter) {
            result.reason = "guacamole_string_writer_not_found";
            return result;
        }

        function isGuacClient(v) {
            return v && typeof v.createClipboardStream === "function";
        }

        // Acepta un ManagedClient (managed.client) o un Guacamole.Client directo.
        function resolverCliente(candidato, basePath) {
            if (!candidato) {
                return null;
            }

            if (isGuacClient(candidato)) {
                return { client: candidato, managed: null, path: basePath };
            }

            if (isGuacClient(candidato.client)) {
                return { client: candidato.client, managed: candidato, path: basePath + ".client" };
            }

            return null;
        }

        let hit = null;

        // 1) Lookup determinista: el cliente vive en el scope aislado de .client-main.
        if (window.angular) {
            const selectores = [".client-main", ".client-tile", ".display"];

            for (const sel of selectores) {
                const el = document.querySelector(sel);

                if (!el) {
                    continue;
                }

                let scope = null;

                try {
                    const ng = window.angular.element(el);
                    scope = (ng.isolateScope && ng.isolateScope()) || (ng.scope && ng.scope());
                } catch (_) {}

                if (!scope) {
                    continue;
                }

                hit =
                    resolverCliente(scope.client, "isolateScope(" + sel + ").client") ||
                    resolverCliente(scope.focusedClient, "isolateScope(" + sel + ").focusedClient") ||
                    resolverCliente(scope.managedClient, "isolateScope(" + sel + ").managedClient");

                if (hit) {
                    break;
                }
            }
        }

        // 2) Fallback: barrido acotado para tolerar otras versiones del webapp.
        if (!hit) {
            const seen = new WeakSet();

            function scan(obj, path, depth) {
                if (!obj || (typeof obj !== "object" && typeof obj !== "function")) {
                    return null;
                }

                if (seen.has(obj) || depth > 6) {
                    return null;
                }

                seen.add(obj);

                if (isGuacClient(obj)) {
                    return { client: obj, managed: null, path };
                }

                let keys = [];

                try {
                    keys = Object.keys(obj);
                } catch (_) {
                    return null;
                }

                for (const key of keys) {
                    let value;

                    try {
                        value = obj[key];
                    } catch (_) {
                        continue;
                    }

                    const kl = String(key).toLowerCase();

                    const likely =
                        kl.includes("client") ||
                        kl.includes("guac") ||
                        kl.includes("connection") ||
                        kl.includes("focused") ||
                        kl.includes("managed") ||
                        kl.includes("session") ||
                        kl.includes("tunnel");

                    if (!likely && depth >= 3) {
                        continue;
                    }

                    const encontrado = scan(value, path + "." + key, depth + 1);

                    if (encontrado) {
                        return encontrado;
                    }
                }

                return null;
            }

            const roots = [];

            if (window.angular) {
                const selectores = [
                    ".client-main",
                    ".client-tile",
                    ".menu-body",
                    "#clipboard-settings",
                    "#connection-settings",
                    "body"
                ];

                for (const sel of selectores) {
                    for (const el of Array.from(document.querySelectorAll(sel))) {
                        try {
                            const ng = window.angular.element(el);

                            const scopes = [
                                ng.scope && ng.scope(),
                                ng.isolateScope && ng.isolateScope()
                            ].filter(Boolean);

                            for (const sc of scopes) {
                                roots.push({ obj: sc, path: "scope(" + sel + ")" });

                                if (sc.client) {
                                    roots.push({ obj: sc.client, path: "scope(" + sel + ").client" });
                                }

                                if (sc.focusedClient) {
                                    roots.push({ obj: sc.focusedClient, path: "scope(" + sel + ").focusedClient" });
                                }
                            }
                        } catch (_) {}
                    }
                }
            }

            for (const key of Object.keys(window)) {
                if (/guac|client|connection|session|tunnel/i.test(key)) {
                    try {
                        roots.push({ obj: window[key], path: "window." + key });
                    } catch (_) {}
                }
            }

            for (const root of roots) {
                hit = scan(root.obj, root.path, 0);

                if (hit) {
                    break;
                }
            }
        }

        if (!hit || !hit.client) {
            result.reason = "guacamole_client_not_found";
            return result;
        }

        result.foundClient = true;
        result.clientPath = hit.path;

        // 3) Estado de conexión: si SABEMOS que no está conectado, no afirmamos éxito.
        //    Si el estado es desconocido (null), seguimos adelante para no descartar
        //    una escritura que sí podría funcionar.
        let connected = null;

        try {
            if (typeof hit.client.currentState === "number") {
                connected = hit.client.currentState === 3; // 3 = CONNECTED
            }

            if (hit.managed && hit.managed.clientState && hit.managed.clientState.connectionState) {
                connected = hit.managed.clientState.connectionState === "CONNECTED";
            }
        } catch (_) {}

        result.connected = connected;

        if (connected === false) {
            result.reason = "not_connected";
            return result;
        }

        const stream = hit.client.createClipboardStream("text/plain");
        const writer = new window.Guacamole.StringWriter(stream);

        writer.sendText(texto);
        writer.sendEnd();

        result.ok = true;
        result.reason = "ok";
        return result;

    } catch (e) {
        result.ok = false;
        result.reason = "exception";
        result.error = String(e && e.stack ? e.stack : e);
        return result;
    }
}
"""


GUAC_MENU_CLIPBOARD_JS = """
async (texto) => {
    const result = {
        ok: false,
        reason: null,
        error: null,
        menuFound: false,
        menuVisible: false,
        selectedClass: null,
        valueMatches: false
    };

    try {
        const el =
            document.querySelector("#clipboard-settings textarea.clipboard") ||
            document.querySelector("textarea.clipboard:not(.clipboard-service-target)");

        if (!el) {
            result.reason = "menu_clipboard_not_found";
            return result;
        }

        result.menuFound = true;
        result.menuVisible = !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
        result.selectedClass = String(el.className || "");

        try {
            if (el.disabled) {
                el.disabled = false;
            }
        } catch (_) {}

        const descriptor = Object.getOwnPropertyDescriptor(
            HTMLTextAreaElement.prototype,
            "value"
        );

        if (descriptor && descriptor.set) {
            descriptor.set.call(el, texto);
        } else {
            el.value = texto;
        }

        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));

        try {
            if (window.angular) {
                const scope = window.angular.element(el).scope();

                if (scope && scope.$applyAsync) {
                    scope.$applyAsync();
                } else if (scope && scope.$apply) {
                    scope.$apply();
                }
            }
        } catch (_) {}

        result.valueMatches = el.value === texto;

        if (!result.valueMatches) {
            result.reason = "value_mismatch";
            return result;
        }

        result.ok = true;
        result.reason = "ok";
        return result;

    } catch (e) {
        result.ok = false;
        result.reason = "exception";
        result.error = String(e && e.stack ? e.stack : e);
        return result;
    }
}
"""


BROWSER_CLIPBOARD_JS = """
async (texto) => {
    const result = {
        ok: false,
        reason: null,
        error: null
    };

    try {
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
            result.reason = "clipboard_api_not_available";
            return result;
        }

        await navigator.clipboard.writeText(texto);

        result.ok = true;
        result.reason = "ok";
        return result;

    } catch (e) {
        result.ok = false;
        result.reason = e && e.name ? e.name : "write_error";
        result.error = String(e && e.message ? e.message : e);
        return result;
    }
}
"""


async def _evaluar_estrategia(page: Any, script: str, texto: str, error_reason: str) -> dict:
    try:
        resultado = await page.evaluate(script, texto)

        if isinstance(resultado, dict):
            return resultado

        return {"ok": bool(resultado), "reason": "non_dict_result", "error": None}

    except Exception as e:
        return {"ok": False, "reason": error_reason, "error": str(e)}


async def copiar_en_guacamole_por_debajo(
    page: Any,
    texto: str,
    logger=None,
) -> bool:
    log = logger or logger_default

    if page is None:
        log.warning("📋 Clipboard bridge omitido: page=None")
        return False

    texto = "" if texto is None else str(texto)
    fingerprint = hashlib.sha1(texto.encode("utf-8")).hexdigest()[:10]

    log.info(
        "📋 Clipboard bridge iniciado | len=%s | sha=%s",
        len(texto),
        fingerprint,
    )

    try:
        await page.bring_to_front()
    except Exception:
        pass

    # 1) Vía principal: escribir directo al portapapeles REMOTO por el túnel.
    #    Es la única que realmente cruza al escritorio remoto.
    remote_result = await _evaluar_estrategia(
        page, GUAC_REMOTE_CLIPBOARD_JS, texto, "playwright_remote_eval_error"
    )
    remote_ok = bool(remote_result.get("ok"))

    # 2) Fallback: portapapeles del menú Guacamole (empuja al remoto vía Angular).
    #    Solo se intenta si la vía principal no confirmó éxito.
    if remote_ok:
        menu_result = {"ok": False, "reason": "skipped_remote_ok", "error": None}
    else:
        menu_result = await _evaluar_estrategia(
            page, GUAC_MENU_CLIPBOARD_JS, texto, "playwright_menu_eval_error"
        )
    menu_ok = bool(menu_result.get("ok"))

    # 3) Espejo local en el portapapeles del navegador. NO cruza al remoto,
    #    por eso no cuenta como éxito. Se mantiene por paridad con la versión previa.
    browser_result = await _evaluar_estrategia(
        page, BROWSER_CLIPBOARD_JS, texto, "playwright_browser_eval_error"
    )
    browser_ok = bool(browser_result.get("ok"))

    log.info(
        "📋 Clipboard bridge resultado | "
        "remote=%s reason=%s connected=%s clientFound=%s clientPath=%s | "
        "menu=%s reason=%s menuFound=%s menuVisible=%s | "
        "browser=%s reason=%s (espejo local, no cuenta) | "
        "len=%s sha=%s",
        remote_ok,
        remote_result.get("reason"),
        remote_result.get("connected"),
        remote_result.get("foundClient"),
        remote_result.get("clientPath"),
        menu_ok,
        menu_result.get("reason"),
        menu_result.get("menuFound"),
        menu_result.get("menuVisible"),
        browser_ok,
        browser_result.get("reason"),
        len(texto),
        fingerprint,
    )

    for etiqueta, res in (
        ("remote", remote_result),
        ("menu", menu_result),
        ("browser", browser_result),
    ):
        if res.get("error"):
            log.warning("⚠️ Clipboard bridge %s error: %s", etiqueta, res.get("error"))

    # Retorno honesto: solo cuentan las vías que llegan al portapapeles REMOTO.
    return remote_ok or menu_ok

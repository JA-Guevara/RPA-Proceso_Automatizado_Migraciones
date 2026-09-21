# Análisis técnico — Bot Tigo (Migraciones / Bajas)

**Fecha:** 14/09/2026 · **Alcance:** `Bot Python - Tigo\Bot - Tigo` (los proyectos `Orquestador`, `Exportador` y `Bot - zendesk NOC` quedaron fuera) · **Enfoque:** arquitectura y flujo, calidad y deuda técnica, seguridad y configuración, documentación.

Este informe complementa —no reemplaza— a `docs/INFORME_LIMPIEZA.md`. Varios puntos de aquel siguen abiertos y se marcan como **[pendiente del informe previo]**.

---

## 0. Qué se analizó

**Leído completo (84 archivos):**

| Área | Archivos |
|---|---|
| Raíz | `main.py`, `requirements.txt`, `.gitignore`, `.env` (solo nombres de clave), `README.md` |
| Docs | `docs/BOT_DOCUMENTACION.md`, `docs/TRAZABILIDAD.md`, `docs/INFORME_LIMPIEZA.md` (índices y secciones clave) |
| Orquestación | `task/manager.py`, `application/use_cases/preparar_contexto.py` |
| Config | `config/config.py`, `config/images.py`, `config/selectors.py` |
| Negocio | `core/action_base/` (3), `core/actions/` (21), `core/action_executor/desktop_executor.py` |
| Flows | `flows/*.json` (los 18) |
| Infraestructura | `infrastructure/database/` (15: database, models, repositories, adapters), `infrastructure/remote_desktop/conexion_escritorio.py`, `infrastructure/services/mail_service.py` |
| Herramientas | `shared/tools/` (12) + `shared/tools/clipboard/` (8), `shared/logger/logger_config.py` |
| Scripts | `scripts/test_runner.py`, `scripts/variables_base.json` |

**No se pudo leer:** `infrastructure/browser/browser_manager.py`, `browser_profiles.py`, `browser_session.py` — OneDrive los tiene como *hardlinks* y la transferencia los rechaza. Todo lo referido al navegador en este informe se infiere de sus puntos de uso, no del código. También quedó fuera el historial de `git` (no fue posible ejecutar `git` sobre la carpeta en esta sesión).

---

## 1. Arquitectura: lo que el código realmente hace

La arquitectura descrita en el `README.md` es fiel. En capas, de afuera hacia adentro:

```
main.py
  └─ TaskManagerMigracion (task/manager.py)        ciclo, lotes, reintentos, recuperación, alertas
       ├─ VistaSQLAdapter                          ¿hay pendientes? → siguiente registro
       ├─ PreparadorDeContextos                    registro → contexto (7 claves)
       └─ MigracionActions (core/actions/migracion_action.py)
            ├─ Actions de negocio (20)             una por pantalla/validación de BCCS
            │    └─ DesktopExecutor                interpreta flows/*.json por imagen
            │         └─ ClickTools / ExtractionTools / ServiceTools / ImageLocator / clipboard_service
            ├─ ConexionEscritorio                  fachada rdp (mstsc) | web (Guacamole + Playwright)
            ├─ EstadoSQLAdapter · MigracionesSQLAdapter   persistencia del resultado
            └─ MailService                          alerta y detención ante falla técnica
```

La regla rectora del proyecto (**desktop = data-driven con flows JSON; web = code-driven con Playwright**) se respeta en todo el código revisado. Es una buena decisión y está bien sostenida.

### 1.1 El proceso de negocio, reconstruido desde el código

El bot ejecuta **bajas/migraciones de líneas pospago a prepago sobre BCCS**, un terminal legacy que se conduce por imagen y OCR a través de escritorio remoto:

1. **Pendientes** → vista SQL filtrada por `BOT_NAME`/lote (el reparto lo hace el Orquestador, no este bot).
2. **Buscar línea** → si la cuenta ya migró a Qvantel, cierre inmediato como *Baja Observada*.
3. **Plan inicial** contra catálogo SQL: válido como INICIAL → sigue; válido como FINAL → *Baja Realizada por Otro Canal*; ninguno → observada.
4. **Consumo**: facturas pendientes > 0 → *Con Deuda* → reclamo.
5. **Estado de cuenta**: `EL`/`PO`/`PP` → desestimada; `PK` → pre-eliminación; ≠ `AC` → flujo de cambio a AC.
6. **Forma de pago**: si ≠ CREDITO, la cambia.
7. **Captura de datos**: fecha hábil, antigüedad, identificación, tipo de cuenta, producto.
8. **Estado controlado / CNS**: si la situación no es PROPIO, exige CNS cancelado y cambia la cuenta a PROPIO.
9. **Migración** según `tipo_baja`:
   - *Migración de Post Pago a Pre Pago* → saldo/billetera, paso post→pre, eliminación de servicios restringidos, eliminación y recreación de cuenta.
   - *Cambio de Post Pago a Pre Pago R* → validación IDCTL, baja de LDI/LDN/900, alta de Factura Fija LTE, programación del cambio.
10. **Plan final** contra catálogo como FINAL → *Baja Procesada*.
11. **Cierre**: carga de reclamo/memo, derivación SMS al cliente, persistencia de estado y detalle, salida de la pantalla.

### 1.2 El motor de flows (`DesktopExecutor`)

- **18 tipos de acción** despachados por `getattr(self, f"_action_{action}")` (`desktop_executor.py:66`).
- **Variables:** solo sustitución total de un valor que empiece por `$` (`_parse_value`, `:92-116`). No hay interpolación dentro de cadenas ni recursión en dicts anidados — por eso los `target` tipo dict de `buscar_y_seleccionar*` (`:336,359,381`) nunca se resuelven.
- **Reintentos:** no existen a nivel de paso. Viven en `ImageLocator.localizar` (polling + un intento con confianza reducida) y en los bucles de `service_tools`.
- **Fallos:** toda excepción no tipificada se envuelve en `FlujoException` y aborta el bloque (`:82-89`). No hay continuación condicional.

El `TaskManagerMigracion` es la pieza mejor resuelta del proyecto: separa falla **técnica** (reintentable) de cierre de **negocio** (no reintentable), tiene guardarraíl anti-doble-migración (`manager.py:145`), recuperación por logout+login, freno sistémico por fallas consecutivas y cortafuegos de túnel antes de tocar cada registro (`:101`). Esa lógica está a otro nivel que el resto del código.

---

## 2. Hallazgos por severidad

### P0 — Atender esta semana

#### P0-1 · Las contraseñas se escriben en texto plano en el log, en cada arranque

```python
# task/manager.py:57
safe = {k: ("****" if "PASS" in k else v) for k, v in vb.items()}
```

Las claves del diccionario están en **minúscula** (`guacamole_password`, `terminal_password`, `bccs_password`, `sms_password`), así que `"PASS" in k` **nunca** es verdadero. El `json.dumps(safe)` de la línea 58 escribe las cuatro contraseñas sin enmascarar en `storage/logs/server.log` (hoy 3,6 MB) en cada inicio del servicio.

`scripts/test_runner.py:127-138` implementa el mismo enmascarado **correctamente** (normaliza a minúscula). Portar esa lógica.

**Acción:** corregir el filtro (`if "pass" in k.lower()` o una lista explícita de claves sensibles), **rotar** las cuatro credenciales y purgar/rotar los logs existentes.

#### P0-2 · Credencial de BD en texto plano en la raíz del proyecto — **[pendiente del informe previo]**

`Pruebas o test - Bot tigo.txt` (raíz de `Bot Python - Tigo`) contiene la cadena de conexión completa a SQL Server: servidor, base, usuario `bot_bajas` y contraseña. **No** está cubierto por `.gitignore` y está sincronizado en OneDrive corporativo. Existe ya una versión `*.SANITIZADO.txt` al lado, pero el original sigue ahí.

**Acción:** rotar la contraseña de `bot_bajas`, eliminar el archivo original, agregar `Pruebas o test*.txt` al `.gitignore` y verificar el historial de git (si alguna vez se commiteó, la contraseña sigue en el historial aunque el archivo se borre).

#### P0-3 · La rama R nunca ejecuta su flujo — **[pendiente del informe previo]**

`ProgramarCambioAction` invoca bloques que no existen en su flow:

| La acción invoca | `flows/programar_cambio.json` define | Resultado |
|---|---|---|
| `validation` | `validation` (5 pasos) | corre |
| **`flow_post_a_pre`** | **no existe** (el bloque real se llama `flow`, 10 pasos) | **0 pasos, en silencio** |
| **`desbloqueo`** | **no existe** (está como `flow_desbloqueo`, 4 pasos) | **0 pasos, en silencio** |
| `reboot_validation` | `reboot_validation` (1 paso) | corre |

`ejecutar_bloque` hace `self.flow_data.get(bloque, [])` (`desktop_executor.py:45`): un bloque inexistente es una lista vacía, no un error. La acción devuelve `True` y `MigracionActions` continúa hacia la validación de plan final creyendo que programó el cambio.

Verificación cruzada de los 18 flows contra las 18 actions (anexo A): este es el único caso funcional; `logout_action.py` invoca `reboot_validation` cuando su flow define `reboot_logout` (0 pasos), sin efecto práctico pero igual de mudo.

**Acción:** corregir los nombres de bloque **y** blindar `ejecutar_bloque()` para que un bloque inexistente lance en vez de no hacer nada. Lo segundo es lo que impide que el error se repita.

#### P0-4 · `tipo_baja` no reconocido → registro marcado como procesado sin haber migrado

```python
# core/actions/migracion_action.py:126-135
tipo = self.contexto.get("tipo_baja")
if tipo == "Migración de Post Pago a Pre Pago":   ...
elif tipo == "Cambio de Post Pago a Pre Pago R":  ...
# sin else
if not self._validar_plan_final(): ...
return self._finalizar_ok()
```

Si `tipo_baja` llega con otro texto (tilde distinta, espacio, tipo nuevo cargado en la vista), **no se ejecuta ninguna migración** y el flujo cae directo a la validación final. Si esa validación pasa, `_finalizar_ok()` persiste la línea como *Baja Procesada*, carga el reclamo y envía el SMS al cliente. Un falso positivo silencioso con impacto en el cliente final.

**Acción:** `else` explícito que lance o cierre con reclamo, y comparar contra los identificadores (`id_tipo_baja`) en lugar de literales de texto.

### P1 — Corregir en el próximo ciclo

#### P1-1 · La validación CNS compara siempre contra valores por defecto

`ValidationEstadoControladoAction` lee del contexto `valor_residual` (default `"0"`) y `tipo_cns` (default `"CNS"`) en `validation_estado_controlado_action.py:257-275`. **Ninguna de esas claves se escribe nunca**: `PreparadorDeContextos.preparar()` puebla exactamente 7 claves (`id_migracion`, `id_sharepoint`, `nro_linea`, `id_tipo_baja`, `tipo_baja`, `id_tipo_lista`, `lote`) y no incluye el saldo, pese a que la vista sí lo trae (`vista_repository.py:25` → `monto_valor_residual`) y el modelo lo mapea (`vista_migracion_model.py:39`).

Consecuencia: el `match_saldo` de `:356` solo acierta cuando el saldo leído es literalmente `"0"`. La validación existe pero no valida.

#### P1-2 · Errores técnicos que se convierten en decisiones de negocio

Este es el patrón más peligroso del código, y se repite:

| Dónde | Qué hace | Cómo se lee aguas arriba |
|---|---|---|
| `extraction_tools.py:406-409` | en el `except`, `contexto["existe_error"] = False` | "no hay error en pantalla" |
| `validation_estado_controlado_action.py:440` | en el `except`, `cnsCancelado = False` | `migracion_action.py:120` → cerrar con reclamo |
| `estado_migracion_adapter.py:21-23,61-63` | traga la excepción y devuelve `False`/`None` | "no hay pendientes" / "no se pudo actualizar" |
| `planes_adapter.py:34-45` | ídem | "plan inválido" → baja observada |
| `vista_sql_adapter.py:40-45` | ídem | "no hay pendientes" → el bot duerme |
| `extraction_tools.py:220-223` | devuelve `""` ante excepción | texto vacío guardado en contexto |
| `app_tools.py` (8 sitios) | `False`/`None` silencioso | — |
| `mail_service.py:90-91` | traga la excepción de envío | el canal de alertas falla en silencio |

Una caída de BD o de red se vuelve indistinguible de un resultado de negocio. `migraciones_adapter.py:29` sí re-lanza — la inconsistencia entre adapters hace el comportamiento impredecible.

**Acción:** que la capa de datos y de OCR propaguen el fallo técnico (para eso existe la distinción técnico/negocio de `TaskManagerMigracion`), y reservar el valor por defecto para casos genuinamente ambiguos.

#### P1-3 · Rama muerta en la validación final

`migracion_action.py:137-146`: dentro del `if not self._validar_plan_final():` el `else` solo se alcanza si `validacion_exitosa` es `True`, cosa que el propio `if` ya descartó. Es código inalcanzable y, más importante, señal de que el triple estado (`retorno`, `validacion_exitosa`, `plan_valido`) es difícil de razonar. `ValidationPlanAction` devuelve `True` con `validacion_exitosa=False` en `:136-145`, semántica que el caller vuelve a desenredar.

#### P1-4 · Parseo posicional frágil en CNS

`validation_estado_controlado_action.py:286-311`: se hace `linea.split()` y se toma `partes[5]` como cuenta y `partes[-1]` como estado. Un espacio de más en la salida del terminal desplaza todas las columnas. Conviene parsear por posición de carácter (el terminal es de ancho fijo) o por expresión regular anclada.

#### P1-5 · Reintento de extracción sin verificación

`ValidationPlanAction:37-40` y `:97-100` reintentan la extracción una sola vez y **no comprueban si el segundo intento también falló**: continúan con `plan_actual_rpa=""`, que se envía al catálogo SQL y vuelve como "plan inválido" → baja observada por un problema de OCR, no de negocio.

#### P1-6 · `SMTP` sin timeout

`mail_service.py:84`: `smtplib.SMTP(host, port)` sin `timeout`. Si el relay no responde, el bot queda colgado indefinidamente justo en el camino de alerta de error. Agregar `timeout=10`.

#### P1-7 · Detalle de migración: *read-then-insert* sin restricción única

`migracion_detalle_repository.py:122-143` consulta y luego inserta; `migracion_detalle_model.py:14` tiene índice pero no constraint único sobre `id_migracion`. Dos bots corriendo a la vez pueden duplicar filas. Además, en la actualización se ignoran los `None` (`:131`), por lo que un campo nunca puede volver a NULL.

### P2 — Deuda técnica acumulada

#### P2-1 · ~680 líneas de código muerto en el puente de portapapeles

Coexisten tres generaciones del mismo mecanismo:

| Módulo | Líneas | Estado |
|---|---|---|
| `shared/tools/guacamole_clipboard_bridge.py` | 451 | **inalcanzable** |
| `shared/tools/guacamole_clipboard_sync.py` | 231 | shims marcados "OBSOLETO" + funciones `_legacy` sin llamador |
| `shared/tools/clipboard/` (8 archivos) | ~2.060 | **el vigente** |

Búsqueda en todo el proyecto: **cero importadores** de los dos primeros fuera de sí mismos. El único llamador de `copiar_en_guacamole_por_debajo` está dentro de una función que nadie invoca. El `README.md` (sección "Puente de portapapeles") todavía documenta estos dos módulos como si fueran la implementación activa.

**Acción:** eliminar ambos archivos y actualizar esa sección del README para describir `clipboard/` (`ClipboardService` + `GuacamoleBackend` con tap sobre `onclipboard` y números de secuencia).

#### P2-2 · Duplicación estructural en las actions

- **Bloque `except` idéntico** (`manejar_excepcion` + reboot + `raise`) en 9 actions: `logout:16-23`, `eliminacion_servicios:24-30`, `validation_consumo:51-57`, `validation_forma_pago:50-57`, `validation_idctl_actual:50-57`, `validation_estado_cuenta:112-119`, `crear_servicio_fflte:49-56`, `eliminacion_creacion:18-24`, `paso_post_a_pre:53-59`. → extraer `_ejecutar_con_reboot(bloque)` a `ActionBase`.
- **Preámbulo de captura de texto** (click + esperar + tecla + `copiar_texto_actual(spec=...)`) repetido en 6 actions. → `self.capturar_texto(paso, spec, tecla=...)`.
- **Marcado de "Baja Observada"** (`f"Baja observada - ID solicitud: {id_sharepoint}"` + `baja_realizada`) repetido en ~10 sitios. → `marcar_baja(tipo, motivo)`.
- **Dos implementaciones de la misma función:** `_agregar_observacion` (`validation_estado_controlado:463`) y `_anexar_observacion` (`migracion_action:246`).

#### P2-3 · Monkey-patching del executor

Seis actions inyectan handlers en tiempo de ejecución: `self.executor._action_extraer_validar_estado = ...` (`validation_estado_cuenta_action.py:14`, y equivalentes en consumo, forma_pago, idctl, saldo y controlado). Funciona, pero rompe la posibilidad de conocer el contrato del motor leyendo el motor. Un registro de handlers (`executor.registrar_accion(nombre, fn)`) da lo mismo de forma explícita.

#### P2-4 · Configuración contradictoria o inerte

| Variable | Problema |
|---|---|
| `CLIPBOARD_GUARD_CLICS` | se lee en `clipboard/service.py:85` pero **`config.py` nunca la define** → siempre `None` → el guard está permanentemente apagado, aunque esté puesta en el `.env` |
| `CLIPBOARD_GRACIA_MS` | ídem (`service.py:89`) |
| `CLIPBOARD_POISON`, `CLIPBOARD_MEDIR_ECO` | `config.py:80,83` las fija en `"true"`; `service.py:73,77` documenta y asume `False` por defecto. Como `EnvConfig` siempre entrega valor, el default del servicio es inalcanzable |
| `LOCATOR_CONFIDENCE` | `ClickTools.__init__` fija `confidence=0.9` (`click_tools.py:62`) y lo pasa siempre al locator (`:99,238`), anulando el valor configurado |
| `BROWSER_ESCRITORIO_WEB` | importado y no usado (`conexion_escritorio.py:9`) |
| booleanos en general | se guardan como *string* (`"true"`) y se evalúan por verdad de cadena en varios puntos: `"false"` es `True` |

#### P2-5 · Funciones demasiado largas

`extraction_tools.extraer_texto_de_region` ~134 líneas (`:90-223`, captura + preproceso + OCR + fuzzy + tri-estado en un solo `try`); `extraer_fecha_y_antiguedad` ~129 (`:241-369`); `click_tools.hacer_clic` ~83 (`:69-151`); `image_locator.localizar` ~64 (`:51-114`).

#### P2-6 · Valores mágicos dispersos

Umbral binario 150, escala `fx=2`, `--psm 7` (`extraction_tools.py:145,146,161`); umbral de similitud 0.70 en el executor (`:292`) vs 0.75 por defecto en la función (`extraction_tools.py:103`), con `EnvConfig.OCR_UMBRAL_SIMILITUD` como tercera fuente; códigos de negocio `186 if meses > 6 else 184` (`:349-351`); regla `len<=100 and "plan"` (`:550-551`); formato `%m/%d/%Y` (`:289`) contra `%Y-%m-%d` en `calcular_antiguedad` (`basic_tools.py:142`).

#### P2-7 · Otros

- `requirements.txt` está codificado en **UTF-16** → `pip install -r` puede fallar según el entorno. **[pendiente del informe previo]**
- `ConexionEscritorio.esta_activa()` devuelve `True` incondicionalmente en modo RDP (`:65-69`).
- `flow_loader.load` devuelve `None` ante fichero ausente o JSON inválido → `AttributeError` aguas abajo en lugar de un error claro.
- `calcular_antiguedad` (`basic_tools.py:152-154`) devuelve `(0,0,0)` para fechas futuras, indistinguible de una antigüedad real de cero.
- Bloques de flow vacíos o nunca invocados: `login.reboot_login` (0 pasos), `logout.reboot_logout` (0), `validation_consumo.flow` (0), `validation_plan.reboot_extraer_*` (0), `captura_datos.reboot_captura_datos` (definido, nunca invocado), `captura_datos._acciones_desactivadas` (5 pasos).
- `task/manager.py`: `self.flow_loader`, `self.app_tools` y `self.imagenes` se instancian y nunca se usan. **[pendiente del informe previo]**

---

## 3. Seguridad y configuración

### Lo que está bien

- **Cero credenciales hardcodeadas en el código.** Todo pasa por `EnvConfig` → `.env`, y `.env` está en `.gitignore:7`.
- `DATABASE_URL` es obligatoria y `database.py:13-22` lanza `RuntimeError` si falta — falla temprano y claro.
- **Capa de datos 100% ORM.** Cero SQL crudo, cero `text()`, cero f-strings en consultas: **no hay superficie de inyección SQL**. La única interpolación de identificadores son nombres de tabla/esquema desde entorno, que es configuración confiable.
- `MailService` toma credenciales y destinatarios del entorno y usa `starttls()`.
- Los nombres de tabla y la vista son parametrizables, lo que permite separar ambientes sin tocar código.

### Lo que hay que corregir

| # | Hallazgo | Severidad |
|---|---|---|
| 1 | Contraseñas sin enmascarar en el log (`manager.py:57`) — ver P0-1 | **Alta** |
| 2 | `Pruebas o test - Bot tigo.txt` con la cadena de conexión completa, fuera de `.gitignore`, en OneDrive — ver P0-2 | **Alta** |
| 3 | `app_tools.py:161`: la contraseña de RDP se pasa como argumento de línea de comandos a `cmdkey` → visible en la tabla de procesos; además queda persistida en el almacén de credenciales de Windows sin `cmdkey /delete` posterior | Media |
| 4 | `app_tools.py:174`: `subprocess.Popen(f"mstsc /v:{host}", shell=True)` — interpolación en shell. Hoy `host` viene de configuración confiable, pero el patrón invita al problema. Usar lista de argumentos sin `shell=True` | Media |
| 5 | `conexion_escritorio.py:15`: `storage/cookies/escritorio_state.json` guarda cookies y localStorage de la sesión del portal **en claro** en el host RPA (directorio gitignorado, pero legible por cualquiera con acceso a la máquina) | Media |
| 6 | `manager.py:41-55`: las 14 credenciales se copian a un dict plano `variables_base` que circula por todo el flujo y por cada contexto, multiplicando los puntos donde pueden terminar en un log o en un mensaje de error | Media |
| 7 | Sin verificar: si `.env` o el `.txt` fueron commiteados alguna vez, siguen en el historial de git aunque hoy estén ignorados | Por confirmar |

### Separación de ambientes

Hoy no existe distinción entre desarrollo y producción: un solo `.env` en la raíz y las mismas credenciales de servicio. Para un bot que **modifica datos de clientes en el sistema productivo de Tigo**, vale la pena un `.env.produccion` / `.env.pruebas` explícito, con usuario de BD de solo lectura en pruebas, y un `BOT_NAME` distinto para que un bot de prueba nunca tome registros reales de la vista.

---

## 4. Documentación

El `README.md`, `BOT_DOCUMENTACION.md` y `TRAZABILIDAD.md` están claramente por encima del promedio: diagramas Mermaid, tabla de "qué hace / qué NO hace", decisiones de diseño con su porqué (D1–D14), contratos a no romper. `TRAZABILIDAD.md` en particular es el documento más valioso del repositorio, porque conserva el razonamiento detrás de las decisiones.

Tres desajustes con el código actual:

1. **Puente de portapapeles** (`README.md`, sección "Puente de portapapeles Guacamole"): describe `guacamole_clipboard_sync` y `guacamole_clipboard_bridge` como las piezas activas. Son código muerto; el vigente es `shared/tools/clipboard/`.
2. **Estructura del proyecto** (`README.md`, árbol): no menciona el paquete `shared/tools/clipboard/` ni `docs/INFORME_LIMPIEZA.md`.
3. **`.env` documentado vs real**: el README lista `LOCATOR_*` pero no los ~20 `CLIPBOARD_*` / `OCR_*` / `BOT_MAX_*` que `config.py` sí lee. Conviene un `.env.example` versionado, generado a partir de `config.py`, que sea la fuente única de verdad de qué variables existen.

Lo que falta documentar y hoy no está en ningún lado: el **contrato del `DesktopExecutor`** (las 18 acciones soportadas, sus parámetros y la regla de sustitución `$variable`). Es lo que alguien necesita para escribir o corregir un flow JSON sin leer el executor entero.

---

## 5. Plan de acción propuesto

| # | Acción | Por qué en ese orden | Esfuerzo |
|---|---|---|---|
| 1 | Rotar las credenciales expuestas (`bot_bajas` y las cuatro de `variables_base`); sanear el `.txt` de la raíz y agregarlo al `.gitignore`; revisar el historial de git | Es la única exposición real y activa hoy | 1-2 h |
| 2 | Corregir el enmascarado de `manager.py:57` y purgar los logs actuales | Sin esto, la rotación del punto 1 se pierde en el siguiente arranque | 15 min |
| 3 | Blindar `ejecutar_bloque()`: bloque inexistente → excepción | Convierte P0-3 y sus futuras repeticiones en un fallo ruidoso | 30 min |
| 4 | Corregir los nombres de bloque de `ProgramarCambioAction` y `LogoutAction` | Devuelve a la vida la rama R | 30 min |
| 5 | `else` explícito para `tipo_baja` no reconocido (P0-4) | Evita marcar como procesada una línea no migrada | 30 min |
| 6 | Poblar `valor_residual` y `tipo_cns` en `PreparadorDeContextos` (P1-1) | Pone a funcionar una validación que hoy es decorativa | 1 h |
| 7 | Que los adapters y el OCR propaguen el fallo técnico en vez de devolver un valor de negocio (P1-2) | Es el cambio con mayor impacto sobre la confiabilidad | 3-4 h |
| 8 | Eliminar `guacamole_clipboard_bridge.py` y `guacamole_clipboard_sync.py`; actualizar el README | Cosmético pero elimina la ambigüedad sobre cuál es el camino vigente | 1 h |
| 9 | Extraer a `ActionBase` los tres patrones duplicados (P2-2) | Reduce ~200 líneas y hace que un cambio de política se haga en un solo lugar | 3-4 h |
| 10 | `.env.example` versionado + documentar el contrato del executor | Cierra la brecha entre documentación y código | 2 h |
| 11 | Regenerar `requirements.txt` en UTF-8; limpiar config inerte (P2-4) | Cosmético | 1 h |

---

## Anexo A — Verificación flows ↔ actions

Contraste programático de los bloques que cada action invoca contra los que su flow define:

| Action | Flow | Bloques invocados | Resultado |
|---|---|---|---|
| `programar_cambio` | `programar_cambio` | validation, **flow_post_a_pre**, **desbloqueo**, reboot_validation | ❌ 2 bloques inexistentes |
| `logout` | `logout` | flow, **reboot_validation** | ❌ 1 inexistente (el flow define `reboot_logout`, vacío) |
| Las otras 16 | — | — | ✅ coinciden |

Bloques definidos pero nunca invocados: `programar_cambio.flow` (10 pasos), `programar_cambio.flow_desbloqueo` (4), `captura_datos.reboot_captura_datos` (1), `captura_datos._acciones_desactivadas` (5), `logout.reboot_logout` (0), `login.reboot_login` (0), `validation_consumo.flow` (0), `validation_plan.reboot_extraer_plan_actual` (0), `validation_plan.reboot_extraer_plan_asignado` (0).

---

<sub>Informe generado a partir de la lectura del código en `Bot Python - Tigo\Bot - Tigo` al 14/09/2026. No se modificó ningún archivo del proyecto.</sub>

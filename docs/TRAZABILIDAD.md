# Trazabilidad — Bot Tigo Migraciones

Registro de arquitectura y decisiones de diseño. El código se mantiene sin
docstrings-ensayo: el "por qué" vive acá. Documentación funcional completa en
`docs/BOT_DOCUMENTACION.md`.

---

## 1. Arquitectura por capas

```
config/         → EnvConfig (.env), selectores web tipados, rutas de imágenes
core/
  action_base/  → BaseAction (común) · ActionBase (desktop) · WebActionBase (web)
  actions/      → acciones de negocio (una por paso del proceso)
  action_executor/ → DesktopExecutor (ejecuta flows JSON por imágenes)
infrastructure/
  browser/      → BrowserManager, BrowserSession, browser_profiles
  remote_desktop/ → ConexionEscritorio (fachada rdp|web)
  database/     → database.py (engine/SessionLocal) + models + repositories + adapters (fachada)
  services/     → mail_service
shared/tools/   → ImageLocator, ClickTools, ExtractionTools, etc. (RDP/píxeles)
flows/          → *.json (pasos visuales declarativos del lado desktop)
task/           → TaskManagerMigracion (orquestador del servicio)
```

Regla rectora: **desktop = data-driven** (flows JSON + imágenes) · **web = code-driven** (Playwright directo). No mezclar responsabilidades.

---

## 2. Decisiones de diseño

### D1 — Eliminación del caché de regiones → `ImageLocator` (jun/2026)
Se eliminó `RegionLocator`. Toda búsqueda es full-screen con polling hasta timeout. **Por qué:** el caché guardaba la posición exacta del último match (sin margen), así que cualquier desplazamiento de la ventana RDP daba un miss con penalidad de ~3s por elemento; además ~14 instancias simultáneas se pisaban `regions.json` entre sí. El full-screen (~0.1–0.3s con OpenCV) es más predecible y se adapta a cualquier cambio de pantalla. El bot opera contra escritorio remoto (solo píxeles, sin UIA ni selectores), por eso el template matching está centralizado en un único módulo con telemetría.

### D2 — Anti-volatilidad de imágenes
- **Variantes de plantilla:** junto a `boton.png` se pueden guardar `boton@v2.png`, `boton@rdp16.png`, etc. Se prueban automáticamente en cada intento, sin tocar flows ni config.
- **Evidencia de fallos:** al agotar el timeout de un elemento requerido se guarda la pantalla completa en `storage/debug_failures/`, para re-recortar la plantilla desde la pantalla real sin reproducir el fallo.

### D3 — Semántica de errores en `ClickTools`
- `raise_error` se respeta: un elemento requerido que no aparece lanza `ImagenNoEncontradaException` (antes devolvía `False` y el flow seguía sobre la pantalla equivocada).
- `transitorio` = opcional/no crítico: se busca con polling (timeout corto) y si no aparece devuelve `False` sin lanzar.
- Parámetros legacy (`t_region`, `wait_timeout`) se aceptan y se ignoran, para no romper llamadas viejas.

### D4 — Stack web code-driven
Se retiró `WebExecutor` + intérprete JSON web. Las acciones web usan Playwright directo (`page.locator(...)`) con selectores tipados (`WebSelectors`). Razón: Playwright ya es un buen DSL legible; el intérprete JSON era una capa extra sin valor para web.

### D5 — Jerarquía de bases de acción
`BaseAction` concentra lo común (logger, `var()`, `hora_inicio/fin`, `manejar_excepcion`). Heredan `ActionBase` (desktop: carga flow + DesktopExecutor) y `WebActionBase` (web: solo lo común). Elimina la duplicación previa.

### D6 — `BrowserSession` + perfiles
Ciclo de vida como configuración: `vida="registro"` (abre/usa/cierra por registro, ej. derivación) y `vida="sesion"` (navegador persistente en hilo + event loop propio, ej. escritorio web). Los perfiles (`browser_profiles.py`: REGISTRO, ESCRITORIO_WEB, ESCRITORIO_WEB_FULLSCREEN, KIOSK, BACKGROUND) centralizan `launch_args`/`no_viewport`/`ignore_https_errors`/`fullscreen`/`permissions`. El escritorio web usa el perfil **FULLSCREEN** (pantalla completa por CDP, sin pulsar F11, para template matching 1:1) con permisos de portapapeles concedidos.

### D7 — `ConexionEscritorio` = infraestructura pura
Responsable solo de abrir/cerrar el escritorio según `CONEXION_ESCRITORIO` y exponer `page` / `session` / `run()`. Par simétrico **`conectar()` / `desconectar()`**, ambos *mode-aware*: `conectar()` abre mstsc (RDP) o el navegador Guacamole (WEB); `desconectar()` mata el proceso `DESKTOP_PROCCESS` (RDP) o cierra el navegador (WEB). **No** hace login Guacamole, ni terminal, ni BCCS. La espera previa al flujo visual la da `esperar_ancla()` (imagen ancla en pantalla; si no hay `DESKTOP_ANCHOR_IMAGE`, cae a espera fija).

### D8 — Login: separación de responsabilidades
- `LoginEscritorioWebAction`: solo login al portal Guacamole (selectores web). No toca terminal/BCCS, no reemplaza `login.json`.
- `login.json`: flujo visual por imágenes del terminal + BCCS (usuario, password, módulos, telefonía, búsqueda). Es el mismo en ambos modos.
- `LoginAction`: orquesta → conectar → (si web) login Guacamole → esperar escritorio → `ejecutar_bloque("flow")`.

### D9 — Negocio vs técnico (TaskManager)
Cierre con reclamo = resultado de negocio mapeado. Falla técnica (imagen/OCR/RDP/BD) se propaga: el TaskManager reintenta con recuperación de sesión, frena tras N fallas, y respeta el guardarraíl `migracion_ejecutada` para no duplicar migración en el remoto.

### D10 — Capa BD a ORM/repositories (jun/2026)
Se migró el acceso a datos de SQL crudo (`text()`) a **SQLAlchemy ORM + repositories**, manteniendo los adapters como **fachada de compatibilidad** (firmas públicas intactas; consumidores sin cambios). Detalle en la sección 6.

### D11 — Teardown simétrico del escritorio (jun/2026)
El cierre del escritorio se movió del paso `cerrar_app` de `logout.json` a `ConexionEscritorio.desconectar()`, gemelo de `conectar()`. **Por qué:** el "arrancar" ya vivía en infraestructura (fachada rdp/web) pero el "matar" quedaba hardcodeado en el flujo visual compartido. Ahora `LogoutAction` hace el logout visual de BCCS (`logout.json`) y luego `desconectar()`. Web replica la intención de RDP: *salir* (BCCS visual) + *cerrar* (navegador), equivalente a matar mstsc. La sesión web **no se persiste** (`remember_session=False`): cada login arma un contexto nuevo, evitando que un token viejo saltee la pantalla de login del portal. Ambos modos reconectan por lote.

### D12 — Puente de portapapeles Guacamole (jun/2026)
En modo web, BCCS se alimenta por portapapeles (más veloz/fiable que tipear o el OCR). Un `Ctrl+V` sintético no dispara el puente del navegador hacia el remoto (el problema está en el "llevar", no en el "traer"), así que se escribe **directo al portapapeles remoto** por el túnel usando el cliente JS de Guacamole (`createClipboardStream`), antes del `Ctrl+V`. Cadena: `basic_tools.escribir_texto_clipboard` → `guacamole_clipboard_sync` (puente síncrono, solo web) → `guacamole_clipboard_bridge` (localiza `.client-main`, verifica conexión, escribe; fallbacks: menú Guacamole y espejo local). El retorno es **honesto**: solo cuentan las vías que llegan al portapapeles remoto.

---

## 3. Flujo de login y logout

```
LOGIN
RDP:  ConexionEscritorio.conectar() [mstsc]                       → login.json
WEB:  ConexionEscritorio.conectar() [navegador] → LoginEscritorioWebAction [portal] → login.json

LOGOUT
Ambos: logout.json (salir BCCS + menú, visual) → ConexionEscritorio.desconectar()
RDP:  desconectar() → mata DESKTOP_PROCCESS (mstsc)
WEB:  desconectar() → cierra el navegador
```

En login, `LoginAction` espera el escritorio (`esperar_ancla`) antes de `ejecutar_bloque("flow")`.

---

## 4. Contratos a NO romper

- `DerivacionSmsAction`: nombre de clase fijo — el detalle mapea `fecha_hora_fin_derivacionsmsaction`. Contrato: `__init__(variables_base, contexto)`, `ejecutar() -> bool`, setea `notificacion_baja_rpa`.
- `MigracionDetalleRepository.MAPEO`: acopla claves de contexto (varias derivadas del nombre de clase) a columnas. Renombrar una acción puede romper la persistencia en silencio.
- Firmas públicas de los adapters de BD (ver sección 6) — los consumidores dependen de ellas.
- `test_runner.py <NombreClase>`: instancia `Clase(variables_base, contexto)` y llama `ejecutar()`. Cada módulo se prueba aislado.

---

## 5. Knobs de `.env`

- Conexión: `CONEXION_ESCRITORIO=rdp|web`, `GUACAMOLE_URL/USER/PASSWORD`, `DESKTOP_ANCHOR_IMAGE`, `TERMINAL_*`.
- Localizador: `LOCATOR_TIMEOUT`, `LOCATOR_TIMEOUT_TRANSITORIO`, `LOCATOR_POLL_INTERVAL`, `LOCATOR_CONFIDENCE`, `LOCATOR_GRAYSCALE`, `LOCATOR_CONFIDENCE_FALLBACK`, `LOCATOR_EVIDENCIA`, `LOCATOR_EVIDENCIA_MAX`.
- BD: `DATABASE_URL` (requerido), `BOT_VISTA`, `BOT_TABLA_*`, `PRIORIDAD_BAJAS`, `BOT_NAME` (= lote). `DB_SERVER/NAME/USER/PASSWORD` quedan como **legacy** (ya no son la vía principal).

---

## 6. Estado actual de capa BD

La capa de datos se migró de SQL crudo (`text()`) a **ORM + repositories**, con los adapters conservados como **fachada de compatibilidad**. La sección antigua que decía "SQLAlchemy Core ejecutando SQL crudo, sin modelos ORM" **ya no es el estado actual**.

Cadena: `TaskManagerMigracion / Actions → Adapters → Repositories → Models ORM → BD`.

- **Migración a ORM/repositories completada** para `estado`, `migracion`, `migracion_detalle` y `planes`.
- **Adapters conservados como fachada** (`VistaSQLAdapter`, `EstadoSQLAdapter`, `MigracionesSQLAdapter`, `PlanesSQLAdapter`): abren `SessionLocal`, delegan en repositories, logean y devuelven lo mismo que antes. **Sin SQL crudo de negocio.**
- **Repositories concentran la lógica de BD** (`EstadoRepository`, `MigracionRepository`, `MigracionDetalleRepository`, `PlanRepository`, `VistaRepository`).
- **Models representan tablas** (`EstadoModel`, `MigracionModel`, `MigracionDetalleModel`, `PlanModel`); `__tablename__` desde `BOT_TABLA_*`.
- **`VistaRepository` conserva SQL de lectura por seguridad** (`text()` con `TOP`/`NOLOCK`): la vista es dinámica/configurable y no garantiza una primary key real. Es la **única lectura especial legacy**; el SQL de vista está aislado solo ahí. La vista solo se consulta.
- **Configuración moderna mediante `DATABASE_URL`** (requerido).
- **Riesgos revisados manualmente y aceptados**: `id_migracion` como clave lógica del detalle (una migración = una ejecución = un detalle, insert/update por `id_migracion`); planes corregidos en BD + validación tolerante a espacios; vista como lectura especial.
- **Pruebas disponibles** con `scripts/test_database_orm.py` (read-only por defecto; escritura solo con `--write` + `--id-migracion`).

---

## 7. Pendientes / known issues

- `DESKTOP_READY` (selector web) y `_validar_inicio` vacíos; la espera real del canvas depende de `DESKTOP_ANCHOR_IMAGE` (imagen). Definir el ancla para confirmación robusta.
- `requirements.txt` en UTF-16 + `dotenv` duplicado (junto a `python-dotenv`).
- `.env`, `variables_base.json` y `contexto_prueba.json` no deben versionarse si contienen datos sensibles.
- Pendiente: pruebas integrales de BD con registros reales para `BOT_NAME` (conexión y firmas ya se validan con `test_database_orm.py`).

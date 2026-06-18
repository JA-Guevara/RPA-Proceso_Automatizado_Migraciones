<div align="center">

# 🤖 Bot Tigo — Migraciones / Bajas

**RPA que ejecuta migraciones/bajas asignadas por lote sobre un escritorio remoto (RDP o Guacamole web), valida planes y persiste resultados en base de datos.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![Playwright](https://img.shields.io/badge/Playwright-1.55-2EAD33?logo=playwright&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL%20Server-ODBC%2017-CC2927?logo=microsoftsqlserver&logoColor=white)
![RPA](https://img.shields.io/badge/RPA-PyAutoGUI%20%2B%20OCR-FF6F00)
![Escritorio](https://img.shields.io/badge/escritorio-RDP%20%7C%20Guacamole-1565C0)
![Capa BD](https://img.shields.io/badge/capa%20BD-ORM%2Frepositories-2E7D32)

</div>

---

## 📑 Contenido

[Propósito](#-propósito) · [Arquitectura](#-arquitectura) · [Ciclo del servicio](#-ciclo-del-servicio) · [Flujo de un registro](#-flujo-de-un-registro) · [Escritorio remoto](#-escritorio-remoto-rdp--web) · [Portapapeles Guacamole](#-puente-de-portapapeles-guacamole) · [Stack](#-stack-técnico) · [Estructura](#-estructura-del-proyecto) · [Capa BD](#-capa-de-base-de-datos) · [Configuración](#-configuración-env) · [Ejecución](#-ejecución) · [Pruebas BD](#-pruebas-de-base-de-datos) · [Decisiones recientes](#-decisiones-de-diseño-recientes) · [Documentación](#-documentación)

---

## 🎯 Propósito

El bot **consume registros ya asignados** a su `BOT_NAME`/lote (la asignación la hace un orquestador externo), ejecuta el proceso **visual/RPA** sobre el terminal/BCCS y guarda el resultado en BD.

| ✅ Qué hace | 🚫 Qué NO hace |
|---|---|
| Consume registros asignados a su lote | Crear o repartir lotes |
| Automatiza escritorio (RDP o web) por imágenes | Decidir qué bot procesa qué lista |
| Valida planes, consumo, estado de cuenta y forma de pago | Modificar la vista de pendientes |
| Ejecuta la migración Post→Pre y deriva SMS | Administrar credenciales desde código |
| Actualiza el estado y registra el detalle de la ejecución | Recalcular datos externos |

---

## 🏗 Arquitectura

```mermaid
flowchart TB
    M[main.py] --> TM[TaskManagerMigracion]
    TM --> PC[PreparadorDeContextos]
    TM --> MA[MigracionActions]
    MA --> ACT[Actions de negocio]
    ACT --> EXE[DesktopExecutor - flows JSON por imagen]
    ACT --> WEBP[Acciones web - Playwright]

    EXE --> RD[ConexionEscritorio - rdp o web]
    WEBP --> RD
    RD --> BR[Browser - Manager y Session]

    MA --> AD[Adapters BD - fachada]
    AD --> RP[Repositories]
    RP --> MO[Models ORM]
    MO --> DB[(SQL Server)]

    MA --> SV[MailService - alertas de error]
```

> **Regla rectora:** `desktop = data-driven` (flows JSON + imágenes) · `web = code-driven` (Playwright directo). **No se mezclan responsabilidades.**

Las capas, de afuera hacia adentro:

| Capa | Carpeta | Responsabilidad |
|---|---|---|
| Orquestación | `task/` | Ciclo del servicio: pendientes, lotes, reintentos, recuperación, alertas |
| Casos de uso | `application/use_cases/` | Preparación del contexto a partir del registro |
| Negocio | `core/actions/` | Acciones (login, validaciones, migración, derivación, logout) |
| Ejecución visual | `core/action_executor/` | `DesktopExecutor` interpreta los `flows/*.json` por imágenes |
| Infraestructura | `infrastructure/` | Navegador, escritorio remoto, base de datos, correo |
| Herramientas | `shared/tools/` | Localización de imágenes, clicks, OCR, portapapeles, excepciones |

---

## 🔄 Ciclo del servicio

`TaskManagerMigracion.ejecutar()` es el bucle de vida del bot. Procesa en **lotes** y se **autorrecupera** ante fallas técnicas.

```mermaid
flowchart TD
    A{¿Hay pendientes?} -->|no| W[Esperar ciclo y reintentar]
    A -->|sí| L[Login inicial - ejecutar_inicio]
    L --> P[Obtener siguiente migración]
    P --> C[Preparar contexto]
    C --> E[MigracionActions.ejecutar]
    E -->|éxito o cierre de negocio| N{¿Fin de lote o sin pendientes?}
    E -->|falla técnica| RT{¿Quedan reintentos?}
    RT -->|sí| REC[Recuperar sesión - logout + login]
    REC --> E
    RT -->|no| MAIL[Alerta por correo y detener]
    N -->|no| P
    N -->|sí| LO[Logout - ejecutar_final]
    LO --> A
```

**Parámetros de resiliencia** (en `TaskManagerMigracion`):

| Parámetro | Valor | Significado |
|---|---|---|
| `lote_max` | 30 | Registros por lote antes del logout temporal |
| `reintentos_max` | 3 | Reintentos ante falla **técnica** (no de negocio) |
| `max_registros_con_fallas` | 3 | Freno sistémico: N registros consecutivos con fallas = entorno inestable |
| `espera_post_logout` | 60 s | Pausa tras logout / sin pendientes |
| `espera_recuperacion` | 10 s | Pausa entre logout y login de recuperación |

> 🛡 **Guardarraíl anti-doble-migración:** si el contexto ya marcó `migracion_ejecutada`, una falla posterior **no se reintenta** (requiere revisión manual) para evitar aplicar dos veces la migración en el sistema remoto.

---

## 🧭 Flujo de un registro

`MigracionActions.ejecutar()` recorre validaciones en cascada; cualquier validación fallida deriva a **cierre con reclamo** (igual persiste estado y detalle).

```mermaid
flowchart TD
    B[Buscar línea - entrar] --> Q{¿Error QVANTEL?}
    Q -->|sí| RC[Cerrar con reclamo]
    Q -->|no| V1[Validar plan inicial]
    V1 --> V2[Validar consumo / deuda]
    V2 --> V3[Validar estado de cuenta]
    V3 --> V4[Validar forma de pago]
    V4 --> CD[Captura de datos]
    CD --> V5[Validar estado controlado]
    V5 --> T{tipo_baja}
    T -->|Post a Pre Pago| MIG3[Saldo, paso Post a Pre, eliminación y creación de servicios]
    T -->|Post a Pre Pago R| MIGR[idctl, LDI 900, crear servicio FFLTE, programar cambio]
    MIG3 --> VF[Validar plan final]
    MIGR --> VF
    VF --> OK[Finalizar OK - reclamo + derivación SMS]
    OK --> PERS[(Actualizar estado + registrar detalle)]
    RC --> PERS
```

Las migraciones marcan `migracion_ejecutada = True` **antes** de tocar el sistema remoto, activando el guardarraíl. El cierre (OK o con reclamo) siempre llama a `EstadoSQLAdapter.actualizar_estado_migracion()` y `MigracionesSQLAdapter.registrar_detalle()`.

---

## 🖥 Escritorio remoto (RDP / Web)

`ConexionEscritorio` es **infraestructura** y actúa como fachada según `CONEXION_ESCRITORIO`. Expone el par simétrico **`conectar()` / `desconectar()`**, ambos *mode-aware*. El login del terminal/BCCS lo hace **siempre** `login.json` por imágenes, en ambos modos.

```mermaid
flowchart TD
    subgraph LOGIN[LoginAction]
      A[conectar] --> B{CONEXION_ESCRITORIO}
      B -->|rdp| C[Abrir mstsc]
      B -->|web| D[Abrir navegador Guacamole]
      D --> E[LoginEscritorioWebAction - login del portal]
      C --> F[esperar_ancla]
      E --> F
      F --> G[flow login.json - terminal + BCCS por imagen]
    end

    subgraph LOGOUT[LogoutAction]
      H[flow logout.json - salir BCCS y menú] --> I[desconectar]
      I --> J{modo}
      J -->|rdp| K[Matar proceso DESKTOP_PROCCESS]
      J -->|web| L[Cerrar navegador]
    end
```

| | **RDP** | **WEB (Guacamole)** |
|---|---|---|
| Abrir (`conectar`) | `mstsc /v:host` | Navegador Playwright a pantalla completa + login del portal |
| Conducir | PyAutoGUI + imágenes sobre el escritorio | PyAutoGUI + imágenes sobre el `<canvas>` de Guacamole |
| Cerrar (`desconectar`) | Mata el proceso `DESKTOP_PROCCESS` (mstsc) | Cierra el navegador (cae el túnel y guacd desarma la conexión) |
| Sesión entre lotes | Reconecta cada lote | Reconecta cada lote (`remember_session=False` → contexto nuevo) |

> El modo web usa `BrowserSession(vida="sesion")` con perfil **pantalla completa** y permisos de portapapeles concedidos. La pantalla completa se fuerza por CDP (sin pulsar F11) para que el *template matching* funcione 1:1.

---

## 📋 Puente de portapapeles Guacamole

En modo web, BCCS se alimenta por **portapapeles** (es más veloz y fiable que tipear o que el OCR). El problema: un `Ctrl+V` sintético **no** dispara el puente portapapeles del navegador hacia el escritorio remoto, así que el remoto quedaría con un valor viejo (el problema está en el **"llevar"**, no en el "traer").

**Solución:** escribir **directo al portapapeles remoto** por el túnel, usando el cliente JS de Guacamole (`Guacamole.Client.createClipboardStream`), antes del `Ctrl+V`.

```mermaid
sequenceDiagram
    participant BOT as Bot (PyAutoGUI)
    participant NAV as Navegador (Playwright)
    participant GUAC as Guacamole Client JS
    participant REM as Escritorio remoto (BCCS)
    BOT->>NAV: pyperclip.copy + bridge JS
    NAV->>GUAC: createClipboardStream(texto)
    GUAC->>REM: portapapeles remoto actualizado
    BOT->>REM: Ctrl+V (pywinauto)
    REM-->>BOT: texto pegado en BCCS
```

Piezas (`shared/tools/`):

| Módulo | Rol |
|---|---|
| `basic_tools.escribir_texto_clipboard` | Copia local (`pyperclip`) + refuerzo Guacamole + `Ctrl+A`/`Ctrl+V` reales |
| `guacamole_clipboard_sync` | Puente síncrono: obtiene la `page` activa de `ConexionEscritorio` (solo modo web) |
| `guacamole_clipboard_bridge` | Lógica JS: localiza el cliente Guacamole (`.client-main`), verifica conexión y escribe al portapapeles remoto. *Fallbacks:* menú de Guacamole y espejo local |

> El retorno del puente es **honesto**: solo cuentan las vías que realmente llegan al portapapeles **remoto**; el espejo del navegador no se considera éxito.

---

## 🧰 Stack técnico

| Área | Tecnología |
|---|---|
| Lenguaje | Python 3.10+ |
| RPA desktop | PyAutoGUI 0.9.54 · OpenCV 4.12 (template matching) · Tesseract / pytesseract 0.3.13 (OCR) |
| Teclado/foco | pywinauto 0.6.9 · pyperclip 1.11 |
| Automatización web | Playwright 1.55 (Chromium) |
| Base de datos | SQLAlchemy 2.0.44 (ORM + repositories) · SQL Server vía `pyodbc` 5.3 (ODBC 17) |
| Escritorio remoto | mstsc (RDP) · Apache Guacamole (web) |
| Proceso/SO | psutil 7.1 · pywin32 |
| Config | python-dotenv |

---

## 📂 Estructura del proyecto

<details>
<summary><b>Ver árbol de carpetas</b></summary>

```
main.py                      Entrypoint: arranca TaskManagerMigracion (Ctrl+C seguro)
requirements.txt             Dependencias (playwright install chromium aparte)

task/
  manager.py                 TaskManagerMigracion: ciclo, lotes, reintentos, recuperación, alertas
application/use_cases/
  preparar_contexto.py       PreparadorDeContextos: arma el contexto del registro
config/
  config.py                  EnvConfig (.env)
  selectors.py               Selectores web tipados (SmsBajas, Conexion)
  images.py                  Rutas de imágenes por proceso
core/
  action_base/               BaseAction (común) · ActionBase (desktop) · WebActionBase (web)
  actions/                   Acciones de negocio (login, validaciones, migración, SMS, logout…)
  action_executor/
    desktop_executor.py      Interpreta los flows JSON por imágenes
infrastructure/
  browser/                   BrowserManager · BrowserSession · browser_profiles
  remote_desktop/
    conexion_escritorio.py   Fachada rdp|web: conectar() / desconectar() / esperar_ancla()
  database/
    database.py              engine / SessionLocal / Base (DATABASE_URL requerida)
    models/                  EstadoModel · MigracionModel · MigracionDetalleModel · PlanModel
    repositories/            Estado · Migracion · MigracionDetalle · Plan · Vista
    adapters/                Vista · EstadoMigracion · Migraciones · Planes (fachada)
  services/
    mail_service.py          Alertas de error por correo
shared/
  tools/                     ImageLocator · ClickTools · BasicTools · AppTools · Extraction ·
                             guacamole_clipboard_bridge/sync · FlowLoader · exceptions
  logger/                    logger_config
flows/                       *.json (pasos visuales del lado desktop/web)
assets/images/               Plantillas de imagen por proceso (login, logout, validations…)
scripts/                     test_database_orm.py · test_runner.py
docs/                        BOT_DOCUMENTACION.md · TRAZABILIDAD.md
storage/                     Runtime: logs, cookies, evidencias (NO documentación)
```

</details>

---

## 🗄 Capa de base de datos

Arquitectura **ORM + repositories**, con los adapters conservados como **fachada de compatibilidad** (firmas públicas intactas → los consumidores no cambiaron).

```
Adapters (fachada)  →  Repositories (lógica)  →  Models ORM  →  BD
```

**Models** (nombre de tabla desde `.env`):

| Modelo | Tabla (`.env`) |
|---|---|
| `EstadoModel` | `BOT_TABLA_ESTADOS` |
| `MigracionModel` | `BOT_TABLA_MIGRACION` |
| `MigracionDetalleModel` | `BOT_TABLA_MIGRACION_DETALLE` |
| `PlanModel` | `BOT_TABLA_PLANES` |

**Adapters** (firmas públicas estables):

| Adapter | Firmas |
|---|---|
| `VistaSQLAdapter` | `hay_pendientes_para_bot()` · `obtener_siguiente_migracion()` |
| `EstadoSQLAdapter` | `obtener_id_por_nombre()` · `obtener_nombre_por_id()` · `actualizar_estado_migracion(contexto)` |
| `MigracionesSQLAdapter` | `registrar_detalle(contexto)` |
| `PlanesSQLAdapter` | `es_plan_valido(id_tipo_lista, nombre_plan, tipo)` |

> ℹ️ `estado`, `migracion`, `migracion_detalle` y `planes` usan **ORM/repositories**. `VistaRepository` se mantiene como **lectura especial legacy** (SQL `text()` con `TOP`/`NOLOCK`) porque la vista es dinámica/configurable y no garantiza una primary key real. El SQL de vista queda **aislado solo ahí**; la vista solo se consulta.

---

## ⚙ Configuración (`.env`)

> 🔒 El `.env` **no se versiona** y **no debe contener credenciales en la documentación**. Los valores de abajo son **placeholders**.

```env
# Identidad / lote
BOT_NAME=Bot_Lista_2_5
BOT_VISTA=vistaMigracionesTigo
PRIORIDAD_BAJAS=Lista_1, Lista_2

# Tablas destino
BOT_TABLA_MIGRACION=migracion
BOT_TABLA_MIGRACION_DETALLE=migracion_detalle
BOT_TABLA_PLANES=planes
BOT_TABLA_ESTADOS=estado

# Base de datos (REQUERIDA)
DATABASE_URL="mssql+pyodbc://USER:PASSWORD@SERVER/DB?driver=ODBC+Driver+17+for+SQL+Server"

# Escritorio remoto
CONEXION_ESCRITORIO=rdp            # rdp | web
DESKTOP_PROCCESS=mstsc.exe         # proceso a cerrar en logout (modo rdp)
DESKTOP_ANCHOR_IMAGE=ancla.png     # imagen ancla de "escritorio listo" (opcional)

# RDP / terminal
TERMINAL_RUTA=...
TERMINAL_USER=...
TERMINAL_PASSWORD=...
BCCS_USER=...
BCCS_PASSWORD=...

# Web (Guacamole)
GUACAMOLE_URL=https://...
GUACAMOLE_USER=...
GUACAMOLE_PASSWORD=...

# SMS / OCR / correo
SMS_URL=...
SMS_USER=...
SMS_PASSWORD=...
TESSERACT_PATH=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
MAIL_HOST=...
MAIL_PORT=587
```

| Grupo | Variables | Rol |
|---|---|---|
| **BD** | `DATABASE_URL` | **Requerida.** SQL Server hoy; portable a otros motores |
| **Lote** | `BOT_NAME`, `BOT_VISTA`, `PRIORIDAD_BAJAS`, `BOT_TABLA_*` | Identidad del bot, vista de pendientes y tablas |
| **Escritorio** | `CONEXION_ESCRITORIO`, `DESKTOP_PROCCESS`, `DESKTOP_ANCHOR_IMAGE` | Modo rdp/web, proceso a cerrar, ancla de listo |
| **RDP/BCCS** | `TERMINAL_*`, `BCCS_*` | Credenciales del terminal y BCCS |
| **Web** | `GUACAMOLE_URL/USER/PASSWORD` | Portal Guacamole |
| **OCR/SMS/Correo** | `TESSERACT_PATH`, `SMS_*`, `MAIL_*` | OCR, derivación SMS y alertas |
| **Locator** | `LOCATOR_TIMEOUT`, `LOCATOR_CONFIDENCE`, `LOCATOR_*` | Ajustes de búsqueda de imágenes |

---

## ▶ Ejecución

```bash
# 1) Entorno
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
python -m playwright install chromium

# 2) Configurar el .env en la raíz (ver sección anterior)

# 3) Ejecutar el servicio
python main.py
```

> Requisitos del SO: **Tesseract-OCR** instalado (ruta en `TESSERACT_PATH`) y, para modo `rdp`, **ODBC Driver 17** + cliente `mstsc`. Se detiene de forma segura con `Ctrl+C`.

---

## 🧪 Pruebas de base de datos

Validación aislada de la capa BD — **no abre RDP, no ejecuta `LoginAction` ni `MigracionActions`**.

```bash
# Read-only (no escribe nada)
python scripts/test_database_orm.py

# Validar un plan
python scripts/test_database_orm.py --plan "NOMBRE_PLAN" --tipo "Final" --id-tipo-lista 1

# Buscar id de estado
python scripts/test_database_orm.py --estado "NOMBRE_ESTADO"

# Escribir detalle (única forma de escribir; requiere --id-migracion)
python scripts/test_database_orm.py --write --id-migracion 123
```

| Regla | |
|---|---|
| Sin `--write` | No inserta ni actualiza |
| `--write` sin `--id-migracion` | Aborta |
| RDP / Login / Migracion | No se ejecutan |

---

## 🧩 Decisiones de diseño recientes

| Tema | Decisión |
|---|---|
| **Teardown simétrico** | `desconectar()` es el gemelo de `conectar()`: RDP mata `DESKTOP_PROCCESS`; WEB cierra el navegador. Ya no vive como paso del `logout.json` |
| **Logout web** | Mismo patrón que RDP: *salir BCCS* visual (`logout.json`) + *cerrar* navegador. El logout del portal no es necesario (paridad con matar mstsc) |
| **Sesión web no persistente** | `remember_session=False`: cada login arma un contexto nuevo, evitando que un token viejo saltee la pantalla de login del portal |
| **Portapapeles Guacamole** | Escritura directa al portapapeles remoto vía cliente JS; el booleano de éxito solo cuenta vías que llegan al remoto |
| **Capa BD** | Migrada a ORM/repositories; adapters como fachada (firmas intactas); `VistaRepository` = lectura legacy aislada |

---

## 📚 Documentación

| Documento | Contenido |
|---|---|
| [`docs/BOT_DOCUMENTACION.md`](docs/BOT_DOCUMENTACION.md) | Documentación técnica completa por módulos |
| [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md) | Registro de arquitectura y decisiones de diseño (el "por qué") |

---

<div align="center"><sub>Las credenciales viven solo en <code>.env</code> (no versionado). Esta documentación no contiene secretos.</sub></div>

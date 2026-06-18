<div align="center">

# 🤖 Bot Tigo — Migraciones / Bajas

**RPA que ejecuta migraciones/bajas asignadas por lote sobre un escritorio remoto (RDP o Guacamole web) y persiste resultados en base de datos.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![Playwright](https://img.shields.io/badge/Playwright-1.55-2EAD33?logo=playwright&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL%20Server-ODBC%2017-CC2927?logo=microsoftsqlserver&logoColor=white)
![RPA](https://img.shields.io/badge/RPA-PyAutoGUI%20%2B%20OCR-FF6F00)
![Capa BD](https://img.shields.io/badge/capa%20BD-ORM%2Frepositories-2E7D32)

</div>

---

## 📑 Contenido

[Propósito](#-propósito) · [Arquitectura](#-arquitectura) · [Flujo de login](#-flujo-de-login-rd--web) · [Stack](#-stack-técnico) · [Estructura](#-estructura-del-proyecto) · [Capa BD](#-capa-de-base-de-datos) · [Configuración](#-configuración-env) · [Pruebas BD](#-pruebas-de-base-de-datos) · [Documentación](#-documentación)

---

## 🎯 Propósito

El bot **consume registros ya asignados** a su `BOT_NAME`/lote (la asignación la hace un orquestador externo), ejecuta el proceso **visual/RPA** sobre el terminal/BCCS y guarda el resultado en BD.

| ✅ Qué hace | 🚫 Qué NO hace |
|---|---|
| Consume registros asignados a su lote | Crear o repartir lotes |
| Automatiza escritorio / web / RPA | Decidir qué bot procesa qué lista |
| Valida planes | Modificar la vista |
| Actualiza estado de migración | Administrar credenciales desde código |
| Registra detalle de la ejecución | Recalcular datos externos |

---

## 🏗 Arquitectura

```mermaid
flowchart LR
    TM[TaskManagerMigracion] --> PC[PreparadorDeContextos]
    PC --> MA[MigracionActions]
    MA --> AC[Actions específicas]
    AC --> AD[Adapters BD - fachada]
    AD --> RP[Repositories]
    RP --> MO[Models ORM]
    MO --> DB[(SQL Server)]
```

> **Regla rectora:** `desktop = data-driven` (flows JSON + imágenes) · `web = code-driven` (Playwright directo). No mezclar responsabilidades.

**Ciclo funcional:** consultar pendientes → obtener siguiente migración → preparar contexto → ejecutar RPA → validar plan → actualizar estado → registrar detalle → reportar errores.

---

## 🔐 Flujo de login (RDP / Web)

```mermaid
flowchart TD
    A[LoginAction.ejecutar] --> B{CONEXION_ESCRITORIO}
    B -->|rdp| C[ConexionEscritorio → abre mstsc]
    B -->|web| D[ConexionEscritorio → abre navegador Guacamole]
    D --> E[LoginEscritorioWebAction → login del portal]
    C --> F[esperar_ancla → escritorio listo]
    E --> F
    F --> G[ejecutar_bloque flow → login.json visual: terminal + BCCS]
```

`ConexionEscritorio` es **infraestructura** (abre/reutiliza/cierra, expone `page`/`session`/`run()`). El login del terminal/BCCS siempre lo hace `login.json` por imágenes, en ambos modos.

---

## 🧰 Stack técnico

| Área | Tecnología |
|---|---|
| Lenguaje | Python 3.10+ |
| RPA desktop | PyAutoGUI + OpenCV (template matching) + Tesseract (OCR) |
| Automatización web | Playwright (Chromium) |
| Base de datos | SQLAlchemy 2.0 (ORM + repositories) · SQL Server vía `pyodbc` (ODBC 17) |
| Escritorio remoto | mstsc (RDP) · Guacamole (web) |

---

## 📂 Estructura del proyecto

<details>
<summary><b>Ver árbol de carpetas</b></summary>

```
config/                  EnvConfig (.env), selectores web tipados, rutas de imágenes
core/
  action_base/           BaseAction (común) · ActionBase (desktop) · WebActionBase (web)
  actions/               acciones de negocio (login, validaciones, migración, derivación…)
  action_executor/       DesktopExecutor (ejecuta flows JSON por imágenes)
infrastructure/
  browser/               BrowserManager · BrowserSession · browser_profiles
  remote_desktop/        ConexionEscritorio (fachada rdp|web)
  database/
    database.py          engine / SessionLocal / Base (DATABASE_URL)
    models/              EstadoModel · MigracionModel · MigracionDetalleModel · PlanModel
    repositories/        Estado · Migracion · MigracionDetalle · Plan · Vista
    adapters/            VistaSQLAdapter · EstadoSQLAdapter · MigracionesSQLAdapter · PlanesSQLAdapter
  services/              mail_service
shared/tools/            ImageLocator · ClickTools · ExtractionTools · …
flows/                   *.json (pasos visuales del lado desktop)
scripts/                 test_database_orm.py (validación de la capa BD)
docs/                    BOT_DOCUMENTACION.md · TRAZABILIDAD.md
storage/                 runtime: logs, cookies, evidencias (NO documentación)
task/                    TaskManagerMigracion (orquestador del servicio)
```

</details>

---

## 🗄 Capa de base de datos

Migrada a **arquitectura ORM + repositories**, con los adapters conservados como **fachada de compatibilidad** (firmas públicas intactas → los consumidores no cambiaron).

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

> 🔒 El `.env` **no se versiona** y **no debe contener credenciales en la documentación**.

```env
BOT_NAME=Bot_Lista_2_5
BOT_VISTA=vistaMigracionesTigo
PRIORIDAD_BAJAS=Lista_1, Lista_2

BOT_TABLA_MIGRACION=migracion
BOT_TABLA_MIGRACION_DETALLE=migracion_detalle
BOT_TABLA_PLANES=planes
BOT_TABLA_ESTADOS=estado

# Configuración moderna y requerida de BD
DATABASE_URL="mssql+pyodbc://USER:PASSWORD@SERVER/DB?driver=ODBC+Driver+17+for+SQL+Server"

# Conexión al escritorio remoto
CONEXION_ESCRITORIO=rdp        # rdp | web
```

| Variable | Rol |
|---|---|
| `DATABASE_URL` | **Requerida.** Conexión a BD (SQL Server hoy; portable a otros motores) |
| `BOT_NAME` | Lote que consume este bot |
| `BOT_VISTA` | Vista de pendientes |
| `PRIORIDAD_BAJAS` | Orden de prioridad (Lista_1, Lista_2, …) |
| `BOT_TABLA_*` | Tablas destino |
| `CONEXION_ESCRITORIO` | `rdp` (mstsc) o `web` (Guacamole) |

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

## 📚 Documentación

| Documento | Contenido |
|---|---|
| [`docs/BOT_DOCUMENTACION.md`](docs/BOT_DOCUMENTACION.md) | Documentación técnica completa (15 secciones) |
| [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md) | Registro de arquitectura y decisiones de diseño (el "por qué") |

---

## ✅ Estado actual

- Capa BD **migrada a ORM/repositories**; `VistaRepository` = lectura especial legacy.
- Bot **funcionalmente compatible** con el flujo anterior (login, escritorio remoto, flows y orquestación **sin cambios**).
- Adapters conservan sus **firmas públicas**.
- Riesgos técnicos **revisados manualmente** y aceptados.
- Pendiente: pruebas integrales con registros reales disponibles para `BOT_NAME`.

<div align="center"><sub>Las credenciales viven solo en <code>.env</code> (no versionado). Esta documentación no contiene secretos.</sub></div>

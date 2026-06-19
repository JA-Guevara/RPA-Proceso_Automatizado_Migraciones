# Documentación técnica — Bot Tigo Migraciones

Documentación funcional y de arquitectura del bot. Para el registro de decisiones de diseño ("por qué"), ver `docs/TRAZABILIDAD.md`.

---

## 1. Propósito del bot

El bot automatiza **migraciones/bajas** sobre un entorno remoto (terminal/BCCS). Procesa registros **ya asignados** a su `BOT_NAME`/lote por un orquestador/base externo.

- **No** crea lotes, **no** asigna registros, **no** decide qué bot procesa qué lista.
- Solo **consume** lo que ya está preparado para su `BOT_NAME`, ejecuta el proceso visual y persiste resultados en BD.

## 2. Flujo general

1. Consulta si hay pendientes en la vista para su `BOT_NAME`.
2. Obtiene la siguiente migración (según `PRIORIDAD_BAJAS`).
3. Prepara el contexto a partir del registro.
4. Ejecuta el flujo visual/RPA (terminal/BCCS).
5. Valida el plan contra la tabla `planes`.
6. Actualiza el estado de la migración en la tabla `migracion`.
7. Registra/actualiza el detalle en `migracion_detalle`.
8. Reporta errores (correo / logs) si corresponde.

## 3. Responsabilidades del bot

**Qué hace:** consume registros asignados; automatiza escritorio/web/RPA; valida planes; actualiza estado; registra detalle.

**Qué NO hace:** no asigna lotes; no reparte carga; no modifica la vista; no administra credenciales desde código (vienen del `.env`); no recalcula datos externos.

## 4. Arquitectura general

```
TaskManagerMigracion
  → PreparadorDeContextos
  → MigracionActions
      → Actions específicas (login, buscar línea, validaciones, migración, derivación, etc.)
          → Adapters BD (fachada)
              → Repositories
                  → Models ORM
                      → Base de datos
```

Regla: **desktop = data-driven** (flows JSON + imágenes), **web = code-driven** (Playwright). La capa BD es ORM/repositories con adapters como fachada.

## 5. Capa de base de datos

- **`infrastructure/database/database.py`**: arma `engine` y `SessionLocal` (SQLAlchemy) a partir de `EnvConfig.DATABASE_URL`. Define `Base = declarative_base()` (base común de los modelos). `engine` usa `pool_pre_ping=True`.
- **`EnvConfig.DATABASE_URL`**: forma moderna y **requerida** de configurar la BD. `DB_SERVER/NAME/USER/PASSWORD` quedan como legacy.
- **`Base`**: clase base declarativa de la que heredan todos los modelos.
- **`engine` / `SessionLocal`**: conexión y fábrica de sesiones. Las sesiones se abren con `with SessionLocal() as db:` (lecturas sin commit; escrituras con commit explícito; rollback en excepción).
- **models / repositories / adapters**: ver secciones 6–8.

## 6. Models ORM

Ubicación: `infrastructure/database/models/`. El nombre de tabla de cada modelo se toma de una variable de entorno (no hardcodeado):

| Modelo | Tabla (`.env`) | Campos representados |
|---|---|---|
| `EstadoModel` | `BOT_TABLA_ESTADOS` | `id`, `nombre` |
| `MigracionModel` | `BOT_TABLA_MIGRACION` | `id`, `id_estado` |
| `MigracionDetalleModel` | `BOT_TABLA_MIGRACION_DETALLE` | `id_migracion` (clave lógica) + columnas de resultado del proceso |
| `PlanModel` | `BOT_TABLA_PLANES` | `id_tipo_lista`, `tipo`, `nombre_plan` |
| `VistaMigracionModel` | `BOT_VISTA` | vista de pendientes (read-only): `id_migracion` (PK declarada), `lote`, `nombre_lista`, `nombre_tipo_baja`, `id_estado`, `nro_linea`, `monto_valor_residual`, … |

`MigracionDetalleModel` mapea solo las columnas que el bot escribe; las fechas son `DateTime` y el resto queda como tipo de paso seguro para preservar el comportamiento previo.

## 7. Repositories

Ubicación: `infrastructure/database/repositories/`. Concentran la lógica real de acceso a datos.

- **`EstadoRepository`**: busca id de estado por nombre y nombre por id (ORM, `select()`).
- **`MigracionRepository`**: actualiza `migracion.id_estado` por `id_migracion` (ORM, `db.get` + set).
- **`MigracionDetalleRepository`**: upsert del detalle por `id_migracion`. Mantiene el `MAPEO` contexto→columna; inserta si no existe; en update solo toca columnas con valor (no pisa con `None`); sin `merge`.
- **`PlanRepository`**: valida plan por `id_tipo_lista`/`tipo`/`nombre_plan`. Normaliza en Python (convierte `id_tipo_lista` a int; matching **tolerante** a espacios dobles/diferencias menores del texto). Sin `TRY_CONVERT`/`TOP`.
- **`VistaRepository`**: lectura de la vista **con ORM** (`select(VistaMigracionModel)`), ordenando por prioridad con `case()` y tomando `.limit(1)`. Solo lectura (`hay_pendientes_para_bot`, `obtener_siguiente_migracion`); nunca insert/update/delete. **Sin `text()`/`TOP`/`NOLOCK`.**

## 8. Adapters

Ubicación: `infrastructure/database/adapters/`. Se conservan como **fachada de compatibilidad**: el bot ya consume estas clases, así que sus **firmas públicas se mantienen** para no romper consumidores. Internamente abren `SessionLocal` y delegan en los repositories (ya no contienen SQL crudo de negocio).

| Adapter | Firmas públicas | Delega en |
|---|---|---|
| `VistaSQLAdapter` | `hay_pendientes_para_bot()`, `obtener_siguiente_migracion()` | `VistaRepository` |
| `EstadoSQLAdapter` | `obtener_id_por_nombre()`, `obtener_nombre_por_id()`, `actualizar_estado_migracion(contexto)` | `EstadoRepository`, `MigracionRepository` |
| `MigracionesSQLAdapter` | `registrar_detalle(contexto)` | `MigracionDetalleRepository` |
| `PlanesSQLAdapter` | `es_plan_valido(id_tipo_lista, nombre_plan, tipo)` | `PlanRepository` |

## 9. Configuración `.env`

Variables necesarias (sin valores reales; **no versionar `.env` ni incluir contraseñas en la documentación**):

```
BOT_NAME=Bot_Lista_2_5
BOT_VISTA=vistaMigracionesTigo
PRIORIDAD_BAJAS=Lista_1, Lista_2

BOT_TABLA_MIGRACION=migracion
BOT_TABLA_MIGRACION_DETALLE=migracion_detalle
BOT_TABLA_PLANES=planes
BOT_TABLA_ESTADOS=estado

DATABASE_URL="mssql+pyodbc://USER:PASSWORD@SERVER/DB?driver=ODBC+Driver+17+for+SQL+Server"
```

- `DATABASE_URL` es la forma recomendada/requerida. Para SQL Server se usa el driver ODBC.
- Para un futuro motor (ej. PostgreSQL) bastaría cambiar `DATABASE_URL` (`postgresql+psycopg://...`), salvo la vista y dependencias propias de SQL Server.
- `.env` no debe subirse al repositorio.

## 10. Pruebas de BD

`scripts/test_database_orm.py` valida la capa BD de forma aislada (no abre RDP, no ejecuta `LoginAction` ni `MigracionActions`).

```
python scripts/test_database_orm.py
python scripts/test_database_orm.py --plan "NOMBRE_PLAN" --tipo "Final" --id-tipo-lista 1
python scripts/test_database_orm.py --estado "NOMBRE_ESTADO"
python scripts/test_database_orm.py --write --id-migracion 123
```

- **Read-only por defecto**: sin `--write` no inserta ni actualiza nada.
- `--write` **requiere** `--id-migracion` (si no, aborta).
- Valida: conexión, vista (pendientes + siguiente), `PreparadorDeContextos`, `es_plan_valido`, `obtener_id_por_nombre`, y `registrar_detalle` (solo con `--write`).

## 11. Login, escritorio remoto y logout

- **`ConexionEscritorio`**: infraestructura. Fachada según `CONEXION_ESCRITORIO` (`rdp` | `web`) con el par simétrico **`conectar()` / `desconectar()`**, ambos *mode-aware*. Expone `page` / `session` / `run()`. No hace login de negocio.
  - `conectar()` → **RDP** abre mstsc; **WEB** abre el navegador del portal Guacamole (`BrowserSession(vida="sesion")`, pantalla completa, permisos de portapapeles, `remember_session=False`).
  - `desconectar()` → **RDP** mata el proceso `DESKTOP_PROCCESS` (mstsc); **WEB** cierra el navegador (cae el túnel y guacd desarma la conexión).
- **`LoginAction`**: orquesta el login → `conectar()` → (si web) ejecuta `LoginEscritorioWebAction` → espera el escritorio (`esperar_ancla`) → ejecuta el flujo visual `login.json`.
- **`LoginEscritorioWebAction`**: solo el login al portal Guacamole (selectores web). No toca terminal/BCCS ni reemplaza `login.json`.
- **`login.json`**: flujo visual por imágenes del terminal + BCCS. Es el mismo en ambos modos.
- **`LogoutAction`**: ejecuta `logout.json` (salir de BCCS y del menú, por imágenes) y luego `ConexionEscritorio.desconectar()`. El cierre del cliente (matar mstsc en RDP / cerrar navegador en web) vive en infraestructura, no en el JSON.

### 11.1 Portapapeles en modo web (Guacamole)

En modo web, BCCS se alimenta por **portapapeles** (más rápido y fiable que tipear o que el OCR). Un `Ctrl+V` sintético no dispara el puente de portapapeles del navegador hacia el remoto, así que se escribe **directo al portapapeles remoto** por el túnel, vía el cliente JS de Guacamole.

- **`basic_tools.escribir_texto_clipboard`**: copia local (`pyperclip`) + refuerzo Guacamole + `Ctrl+A`/`Ctrl+V` reales (`pywinauto`).
- **`guacamole_clipboard_sync`**: puente síncrono; obtiene la `page` activa de `ConexionEscritorio` (solo actúa en modo web).
- **`guacamole_clipboard_bridge`**: localiza el cliente Guacamole (`.client-main`), verifica que esté conectado y escribe al portapapeles remoto (`createClipboardStream`). *Fallbacks:* textarea del menú Guacamole y espejo local. El booleano de éxito es **honesto**: solo cuentan las vías que llegan al remoto.

## 12. Flujos visuales

Los flows JSON (`flows/*.json`) siguen siendo la fuente de los pasos visuales del lado desktop (clics/escrituras por imagen). No se documentan datos sensibles ni capturas aquí. Al trabajar solo la capa BD, los flows no se tocan.

## 13. Riesgos revisados y decisión actual

- **`id_migracion` como clave lógica** de `migracion_detalle`: aceptado — una migración representa una ejecución y genera un único detalle; el comportamiento es insert/update por `id_migracion`, igual que la lógica anterior.
- **Planes**: la tabla `planes` fue corregida manualmente para evitar diferencias por espacios; la validación es **tolerante** para evitar falsos negativos por espacios dobles o diferencias menores del texto capturado.
- **Vista**: migrada a **ORM** (`VistaMigracionModel` + `VistaRepository`). Como la vista no tiene PK real, se declara `id_migracion` como primary key **solo a nivel mapeo** (no toca la BD); como solo se hace `.limit(1)`/`.first()`, no hay riesgo de identidad. Solo se consulta.
- **`DATABASE_URL`** como estándar de configuración.
- **Adapters** conservados como fachada de compatibilidad.

## 14. Buenas prácticas del proyecto

- No subir `.env`.
- No subir `variables_base.json` ni `contexto_prueba.json` si contienen datos sensibles.
- No documentar contraseñas.
- No tocar flows ni login si se está trabajando solo la capa BD.
- Validar con `scripts/test_database_orm.py` antes de ejecutar procesos visuales.

## 15. Estado actual

- Capa BD **100% ORM/repositories**, incluida la **vista de pendientes** (`VistaMigracionModel`). No queda SQL crudo en el código.
- **Escritorio remoto unificado**: `ConexionEscritorio` con `conectar()` / `desconectar()` *mode-aware*; el teardown de RDP (matar proceso) y de web (cerrar navegador) vive en infraestructura. `logout.json` quedó como logout puramente visual.
- **Modo web** con puente de portapapeles Guacamole para alimentar BCCS de forma fiable, y sesión no persistente (`remember_session=False`).
- Adapters conservan sus **firmas públicas**; el flujo de negocio (`MigracionActions`, validaciones, persistencia) no cambió.
- Riesgos técnicos **revisados manualmente** y aceptados.
- Pendiente: pruebas integrales con registros reales para `BOT_NAME`.

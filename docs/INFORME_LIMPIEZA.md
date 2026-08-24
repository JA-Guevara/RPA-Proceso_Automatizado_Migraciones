# Informe de limpieza y hallazgos — Bot Tigo

Análisis estático de todo el proyecto cruzando `config/images.py`, los 18 flows
JSON, las 21 acciones, los PNG reales en disco y el log de producción.

**La limpieza de archivos es lo menos importante de este informe.** Aparecieron
cuatro defectos de código, y uno de ellos explica por qué la rama *"Cambio de
Post Pago a Pre Pago R"* podría estar fallando de forma sistemática.

---

## 1. 🔴 CRÍTICO — `ProgramarCambioAction` nunca ejecuta su flujo

**Hecho verificado.** La acción invoca bloques que no existen en su JSON:

| `programar_cambio_action.py` invoca | `flows/programar_cambio.json` define | Resultado |
|---|---|---|
| `validation` | `validation` (5 pasos) | ✅ corre |
| **`flow_post_a_pre`** | **no existe** | 🔴 **0 pasos, en silencio** |
| **`desbloqueo`** | **no existe** (está como `flow_desbloqueo`) | 🔴 **0 pasos, en silencio** |
| `reboot_validation` | `reboot_validation` (1 paso) | ✅ corre |
| — | `flow` (**10 pasos**) | ⚠️ **nadie lo invoca** |

**Por qué es silencioso.** `DesktopExecutor.ejecutar_bloque()` (línea 44) hace:

```python
pasos = self.flow_data.get(bloque, [])
```

Una clave inexistente devuelve `[]`, loguea *"Ejecutando bloque: X (0 pasos)"* y
el `for` no itera. No lanza nada.

**Consecuencia.** El camino feliz de la acción es:

```
ejecutar_bloque('validation')       →  5 pasos   corre
ejecutar_bloque('flow_post_a_pre')  →  0 pasos   NO HACE NADA
return True                         →  reporta éxito
```

El bloque `flow` — el que escribe plan comercial `79`, plan de consumo `2400`,
selecciona *inmediato* y procesa — **nunca se ejecuta**. Después
`_validar_plan_final()` lee el plan sin cambiar y cierra como *Baja Observada*.

**Fix (elegí uno, no los dos):**

```python
# opción A — corregir la acción (2 líneas)
self.executor.ejecutar_bloque("flow")            # era "flow_post_a_pre"
self.executor.ejecutar_bloque("flow_desbloqueo") # era "desbloqueo"
```

```json
// opción B — renombrar los bloques en el JSON
"flow"           → "flow_post_a_pre"
"flow_desbloqueo" → "desbloqueo"
```

> ⚠️ **Antes de aplicar el fix, corregí también el punto 2.** Dos de las tres
> referencias de imagen rotas viven justo dentro de ese bloque `flow`. Por eso
> nadie notó los nombres mal escritos: el bloque nunca corrió. Si arreglás el
> nombre del bloque sin arreglar los PNG, va a empezar a fallar con
> `InterfazException`.

**Blindaje recomendado** en `ejecutar_bloque()`, para que esto no vuelva a pasar
en silencio:

```python
pasos = self.flow_data.get(bloque)
if pasos is None:
    raise RPAExceptions.FlujoException(
        f"El bloque '{bloque}' no existe en el flow. "
        f"Disponibles: {sorted(k for k in self.flow_data if k != 'meta')}"
    )
```

---

## 2. 🔴 Tres referencias de imagen rotas en `config/images.py`

**Hecho verificado** cruzando `images.py` contra los 160 PNG reales.
`ImageLocator._validar_plantilla` lanza `InterfazException` si el archivo no
existe en disco.

| `images.py` declara | PNG real en disco | Dónde se usa |
|---|---|---|
| `programar_cambio/plan_consumo_field.png` | `plan_conusmo_field2.png` | bloque `flow` (que hoy no corre) |
| `programar_cambio/tipos_plan_lista.png` | `tipos_plan_list.png` | bloque `flow` (que hoy no corre) |
| `varificar_crear_servicios/actualizar2_button.png` | `actualizar2.png` | `flow_FFLTE` — **este sí corre hoy** |

**Fix — corregir `images.py`, no borrar los PNG:**

```python
    PROGRAMAR_CAMBIO = {
        ...
        "plan_consumo_field": ruta("programar_cambio", "plan_conusmo_field2.png"),
        "tipos_plan_lista":   ruta("programar_cambio", "tipos_plan_list.png"),
    }

    VERIFICAR_CREAR_SERVICIO = {
        ...
        "actualizar2_button": ruta("varificar_crear_servicios", "actualizar2.png"),
    }
```

(O renombrar los PNG en disco a lo que `images.py` espera. Da igual, pero
elegí un lado.)

El tercero es el más urgente: `actualizar2_button` está en `flow_FFLTE`, que
`CrearServicioFflteAction` sí invoca. Ese paso no tiene `transitorio` ni
`raise_error: false`, así que **falla siempre** que la ejecución llegue ahí.

---

## 3. 🟠 `_migracion_post_preR` ignora el resultado de sus validaciones

**Hecho verificado** en `core/actions/migracion_action.py`:

```python
    def _migracion_post_preR(self) -> bool:
        ValidationIdctlActualAction(...).ejecutar()      # ← retorno descartado
        VerificarServicioLdi_900Action(...).ejecutar()   # ← retorno descartado
        self.contexto["migracion_ejecutada"] = True
        CrearServicioFflteAction(...).ejecutar()         # ← retorno descartado
        ProgramarCambioAction(...).ejecutar()            # ← retorno descartado
        return True
```

Si `ValidationIdctlActualAction` devuelve `False` porque el IDCTL está en `COR`
(caso que la propia acción marca como *Baja Observada*), **el flujo sigue y
migra igual**.

Compará con la rama de 3 pasos, que sí tiene el guard:

```python
    def _migracion_post_pre3(self) -> bool:
        SaldoCoreBalanceAction(...).ejecutar()
        self.contexto["migracion_ejecutada"] = True
        PasoPostAPreAction(...).ejecutar()
        if self.contexto.get("linea_error_migracion", False):   # ← guard
            self._cerrar_con_reclamo()
            return False
        ...
```

La rama R no tiene el equivalente. Sumado al punto 1, esa rama tiene tres
defectos independientes.

---

## 4. 🟡 `LogoutAction` invoca un bloque inexistente

`logout_action.py` llama `ejecutar_bloque("reboot_validation")` en su rama de
excepción, pero `flows/logout.json` define `reboot_logout` (y está vacío). El
fallback de recuperación de logout no hace nada.

Impacto bajo (solo en el camino de error), pero es un `except` que aparenta
recuperar y no recupera.

---

## 5. 🟡 `requirements.txt` — UTF-16 y dependencia duplicada

**Hecho verificado:** el archivo está en **UTF-16 con BOM** (`0xFF 0xFE`).
`pip install -r requirements.txt` no lo parsea correctamente en ese encoding.
Ya estaba anotado como *known issue* en `TRAZABILIDAD.md` §7.

Además declara **dos paquetes distintos** para lo mismo:

```
dotenv==0.9.9          ← paquete de terceros, no mantenido
python-dotenv==1.2.1   ← el que realmente usás (config/config.py importa dotenv de acá)
```

**Fix:** regenerar en UTF-8 y sacar `dotenv`:

```powershell
# desde el venv activo
pip uninstall dotenv -y
pip freeze | Out-File -Encoding utf8 requirements.txt
```

---

## 6. Archivos a limpiar

Corré `limpiar.ps1` (mueve a `_papelera\`, no borra).

### Tier 1 — seguro

| Ruta | Motivo |
|---|---|
| `_mejoras_portapapeles\` | Redundante: todo está aplicado en su lugar |
| `assets\images_debug\` | 7 PNG; reemplazado por `storage\ocr_debug` con poda y flag `OCR_EVIDENCIA` |
| `__pycache__\` (recursivo, excluyendo `venv`) | Bytecode |

### Tier 2 — huérfanos verificados (11 PNG)

No están declarados en `images.py`, así que ningún flow puede alcanzarlos:

| Ruta | Motivo |
|---|---|
| `assets\images\paso_post_a_pre\liberacion_cuenta\` (4 PNG) | Copia de `assets\images\liberacion_cuenta\`; `images.py` apunta siempre a la raíz |
| `assets\images\varificar_crear_servicios\liberacion_cuenta\` (4 PNG) | Ídem |
| `assets\images\varificar_crear_servicios\image_error.png` | Duplicado de `liberacion_cuenta\image_error.png` |

### Tier 3 — revisar antes (`-IncluirRevisar`)

| Ruta | Motivo |
|---|---|
| `validations\validation_estado_controlado\IDCTL_actual_field.png` | Sin declarar; el vigente es `validation_idctl_actual\idctl_actual_field.png` |
| `validations\validation_idctl_actual\eliminar_plan_button2.png` | Sin declarar. **No** es una variante: el locator solo reconoce el patrón `nombre@algo.png`, no `nombre2.png` |

### NO borrar

`plan_conusmo_field2.png`, `tipos_plan_list.png` y `actualizar2.png` aparecen
como huérfanos **porque `images.py` los nombra mal**. Son los PNG correctos: hay
que arreglar la referencia (punto 2), no borrar el archivo.

### Se deja como está

`storage\debug_failures\` (3 PNG) — es la evidencia de misses de `ImageLocator`,
ya tiene poda con `LOCATOR_EVIDENCIA_MAX` y sirve para re-recortar plantillas.
`storage\logs\server.log` (254 KB) — rotativo, gestionado.

---

## 7. Código muerto menor

| Qué | Dónde |
|---|---|
| `self.flow_loader`, `self.app_tools`, `self.imagenes` | `task/manager.py`: se instancian en `__init__` y no se usan nunca |
| 5 excepciones declaradas y sin uso | `ClickException`, `SesionInvalidaException`, `UsuarioBloqueadoException`, `ContrasenaIncorrectaException`, `ServicioNoDisponibleException` |
| 4 bloques de flow vacíos y sin invocar | `logout.json::reboot_logout`, `validation_consumo.json::flow`, `validation_plan.json::reboot_extraer_plan_actual` y `::reboot_extraer_plan_asignado` |
| 1 bloque con pasos que nadie invoca | `captura_datos.json::reboot_captura_datos` (la acción no lo llama en su `except`) |
| 2 claves de `images.py` que ningún flow usa | `buscar_linea.inicial_busqueda`, `saldo_core_balance.estado_field` |
| `EstadoSQLAdapter.obtener_nombre_por_id()` | Ya marcado como legacy en el propio código |

> Las excepciones `DatosException`, `TiempoEsperaExcedidoException`,
> `EntradaTextoException` y `ConexionFallidaException` **sí se usan ahora**: las
> incorporaron los parches del portapapeles.

---

## 8. 🔒 Credencial en texto plano (pendiente desde el primer análisis)

`Pruebas o test - Bot tigo.txt`, en la raíz del proyecto y sincronizado en
OneDrive corporativo, contiene la cadena de conexión completa a SQL Server:
servidor, base, usuario `bot_bajas` y su contraseña.

Ese archivo **no** está cubierto por `.gitignore`. Recomendación:

1. Rotar la contraseña de `bot_bajas` en SQL Server.
2. Reemplazar el contenido por la versión con placeholders (te dejo
   `Pruebas o test - Bot tigo.SANITIZADO.txt`).
3. Agregar `Pruebas o test*.txt` al `.gitignore`.
4. Si el archivo ya está commiteado, la contraseña sigue en el historial de git
   aunque la borres del working tree.

---

## 9. Qué sigue — orden propuesto

| # | Acción | Por qué en ese orden |
|---|---|---|
| 1 | Rotar la credencial de `bot_bajas` y sanear el `.txt` | Es lo único con exposición real hoy |
| 2 | Corregir las 3 referencias de `images.py` (punto 2) | Prerequisito del paso 3 |
| 3 | Corregir los bloques de `ProgramarCambioAction` (punto 1) | Devuelve a la vida la rama R |
| 4 | Agregar el guard de `_migracion_post_preR` (punto 3) | Evita migrar cuando la validación dijo que no |
| 5 | Blindar `ejecutar_bloque()` contra bloques inexistentes | Impide que el punto 1 se repita |
| 6 | `limpiar.ps1 -Ejecutar` | Cosmético, sin riesgo |
| 7 | Regenerar `requirements.txt` en UTF-8 sin `dotenv` | Cosmético |
| 8 | Probar el tap de portapapeles: `python scripts/test_runner.py LoginEscritorioWebAction` | Ya desplegado, falta validarlo |
| 9 | Un lote con telemetría y después `GUACAMOLE_INPUT_MODE=tunnel` | La fase 2 del plan de portapapeles |

**Los pasos 2, 3 y 4 son de negocio, no de limpieza.** Si la rama *"Cambio de
Post Pago a Pre Pago R"* te viene dando *Baja Observada* de forma sistemática,
ahí está la causa, y no tiene nada que ver con el portapapeles.

---

## Alcance de este análisis

**Verificado estáticamente:** cruces de `images.py` ↔ PNG en disco ↔ flows ↔
acciones, encodings, `.gitignore`, código muerto. Todo reproducible.

**No verificado en ejecución:** el log disponible cubre 11 minutos
(2026-06-18 13:44 a 13:55) y solo ejercitó la rama *"Migración de Post Pago a
Pre Pago"*. `ProgramarCambioAction`, `CrearServicioFflteAction`,
`ValidationIdctlActualAction` y `VerificarServicioLdi_900Action` no aparecen ni
una vez, así que no hay evidencia de runtime que confirme ni refute los puntos 1
a 3. La conclusión se apoya en lectura de código, que para el punto 1 es
concluyente (`dict.get(clave, [])` sobre una clave ausente).

**No analizado:** `infrastructure/browser/browser_manager.py`,
`browser_session.py` y `browser_profiles.py` siguen sin poder leerse (hardlink
de OneDrive). Puede haber perfiles declarados y sin uso ahí.

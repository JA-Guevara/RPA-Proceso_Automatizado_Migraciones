"""
Keysyms X11 para Guacamole.Client.sendKeyEvent(pressed, keysym).

Guacamole viaja teclas como keysyms de X11, no como scancodes de Windows.
Para ASCII imprimible (0x20-0x7E) el keysym coincide con el codepoint, y el
servidor RDP se encarga de traducirlo a scancode + shift. Para caracteres
fuera de ASCII se usa el rango Unicode de X11: 0x01000000 + codepoint.
"""

# --- Modificadores ---
CONTROL_L = 0xFFE3
CONTROL_R = 0xFFE4
SHIFT_L = 0xFFE1
SHIFT_R = 0xFFE2
ALT_L = 0xFFE9
ALT_R = 0xFFEA

MODIFICADORES_TODOS = (CONTROL_L, CONTROL_R, SHIFT_L, SHIFT_R, ALT_L, ALT_R)

_MODIFICADORES = {
    "ctrl": CONTROL_L,
    "control": CONTROL_L,
    "shift": SHIFT_L,
    "alt": ALT_L,
}

# --- Teclas especiales (mismos nombres que AppTools._convertir_tecla_real) ---
_ESPECIALES = {
    "enter": 0xFF0D,
    "return": 0xFF0D,
    "tab": 0xFF09,
    "esc": 0xFF1B,
    "escape": 0xFF1B,
    "backspace": 0xFF08,
    "delete": 0xFFFF,
    "del": 0xFFFF,
    "insert": 0xFF63,
    "ins": 0xFF63,
    "home": 0xFF50,
    "end": 0xFF57,
    "up": 0xFF52,
    "down": 0xFF54,
    "left": 0xFF51,
    "right": 0xFF53,
    "pgdn": 0xFF56,
    "pagedown": 0xFF56,
    "pgup": 0xFF55,
    "pageup": 0xFF55,
    "space": 0x0020,
    "f1": 0xFFBE,
    "f2": 0xFFBF,
    "f3": 0xFFC0,
    "f4": 0xFFC1,
    "f5": 0xFFC2,
    "f6": 0xFFC3,
    "f7": 0xFFC4,
    "f8": 0xFFC5,
    "f9": 0xFFC6,
    "f10": 0xFFC7,
    "f11": 0xFFC8,
    "f12": 0xFFC9,
}


def keysym_de_caracter(caracter: str) -> int:
    """Keysym de un único carácter."""
    codigo = ord(caracter)

    if codigo in (0x0A, 0x0D):
        return 0xFF0D
    if codigo == 0x09:
        return 0xFF09
    if 0x20 <= codigo <= 0x7E:
        return codigo

    return 0x01000000 + codigo


def keysym_de_tecla(tecla: str) -> int:
    """
    Keysym de un nombre de tecla. Acepta la misma nomenclatura que
    AppTools._convertir_tecla_real ('enter', 'tab', 'pgdn', 'f2', 'a'...).
    """
    nombre = str(tecla).strip().lower()

    if nombre in _MODIFICADORES:
        return _MODIFICADORES[nombre]

    if nombre in _ESPECIALES:
        return _ESPECIALES[nombre]

    if len(nombre) == 1:
        return keysym_de_caracter(nombre)

    raise ValueError(f"Tecla no reconocida para keysym: {tecla!r}")


def keysyms_de_texto(texto: str) -> list[int]:
    """Secuencia de keysyms para tipear un texto carácter por carácter."""
    return [keysym_de_caracter(c) for c in str(texto)]


def combinacion(*teclas: str) -> list[int]:
    """
    Convierte ('ctrl', 'c') -> [CONTROL_L, 0x63].

    El orden importa: los modificadores van primero y el consumidor los
    presiona en orden y los libera en reverso.
    """
    modificadores: list[int] = []
    finales: list[int] = []

    for tecla in teclas:
        nombre = str(tecla).strip().lower()
        if nombre in _MODIFICADORES:
            modificadores.append(_MODIFICADORES[nombre])
        else:
            finales.append(keysym_de_tecla(nombre))

    if not finales:
        raise ValueError(f"Combinación sin tecla final: {teclas!r}")

    return modificadores + finales


# Atajos usados por el servicio de portapapeles
COPIAR = combinacion("ctrl", "c")
PEGAR = combinacion("ctrl", "v")
SELECCIONAR_TODO = combinacion("ctrl", "a")

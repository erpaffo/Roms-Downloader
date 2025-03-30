KEY_MAPPING = {
    "è": "leftbracket",
    "+": "rightbracket",
    "ò": "semicolon",
    "à": "quote",
    "ù": "backslash",
    "1": "num1",
    "2": "num2",
    "3": "num3",
    "4": "num4",
    "5": "num5",
    "6": "num6",
    "7": "num7",
    "8": "num8",
    "9": "num9",
    "0": "num0",
    ",": "comma",
    ".": "period",
    "-": "slash",
    "'": "minus",
    "ì": "equals",
    "<": "oem102",
    "ins": "insert",
    "canc": "del",
    "arrow": "home",
}

def convert_binding(key: str) -> str:
    """Restituisce il valore mappato se presente, altrimenti restituisce key."""
    return KEY_MAPPING.get(key, key)
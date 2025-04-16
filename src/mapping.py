import logging
import re

TITLE_TERM_MAP = {
    "versione nera": "black version",
    "versione bianca": "white version",
    "nero": "black",
    "bianco": "white",
    "versione oro": "gold version",
    "versione argento": "silver version",
    "oro": "gold",
    "argento": "silver",
    "versione cristallo": "crystal version",
    "cristallo": "crystal",
    "versione rossa": "red version",
    "versione blu": "blue version",
    "rosso": "red",
    "blu": "blue",
    "versione gialla": "yellow version",
    "giallo": "yellow",
    "rubino": "ruby",
    "zaffiro": "sapphire",
    "smeraldo": "emerald",
    "diamante": "diamond",
    "perla": "pearl",
    "platino": "platinum",
    "cuore": "heart",
    "anima": "soul",
    "ombra": "shadow",
    "tempesta": "storm",
    "oscurità": "darkness",
    "luce": "light",
    "fuoco": "fire",
    "foglia": "leaf",
    "sole": "sun",
    "luna": "moon",
    "schwarz": "black",
    "weiss": "white",
    "goldene": "gold",
    "silberne": "silver",
    "noir": "black",
    "blanc": "white",
    "or": "gold",
    "argent": "silver",
}

COMMON_LOCAL_WORDS_TO_REMOVE = ["Versione", "Edizione", "Edition", "Ausgabe"]

def apply_title_term_map(title: str) -> str:
    modified_title = title.lower()
    if not title:
        return ""

    sorted_keys = sorted(TITLE_TERM_MAP.keys(), key=len, reverse=True)

    for term in sorted_keys:
        pattern = r'\b' + re.escape(term) + r'\b'
        modified_title = re.sub(pattern, TITLE_TERM_MAP[term], modified_title, flags=re.IGNORECASE)

    return modified_title.title()

def simplify_title(title: str) -> str:
    simplified = title
    for word in COMMON_LOCAL_WORDS_TO_REMOVE:
         pattern = r'\b' + re.escape(word) + r'\b\s*'
         simplified = re.sub(pattern, '', simplified, flags=re.IGNORECASE)

    simplified = " ".join(simplified.split()).strip()
    return simplified
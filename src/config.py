import logging
import os

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BASE_URL = "https://myrient.erista.me/files/"
CONSOLES = {
    "3ds": "No-Intro/Nintendo%20-%20Nintendo%203DS%20(Decrypted)/",
    "gb": "No-Intro/Nintendo%20-%20Game%20Boy/",
    "gba": "No-Intro/Nintendo%20-%20Game%20Boy%20Advance/",
    "nds": "No-Intro/Nintendo%20-%20Nintendo%20DS%20(Decrypted)/"
}

# Cartella in cui salvare i download – modificabile dall'utente
DOWNLOADS_FOLDER = os.path.join(os.getcwd(), "downloads")

# Percorsi degli emulatori (modifica in base al tuo sistema)
# src/config.py
EMULATOR_3DS_NAME = "citra"
EMULATOR_NDS_NAME = "drastic"
EMULATOR_GBA_NAME = "mgba"   # Placeholder per giochi GBA
EMULATOR_GB_NAME = "mgba"    # Placeholder per giochi GB – eventualmente puoi sostituirlo con "sameboy" o un altro emulatore

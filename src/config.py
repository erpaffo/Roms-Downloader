import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BASE_URL = 'https://myrient.erista.me/files/'
CONSOLES = {
    "3ds": "No-Intro/Nintendo%20-%20Nintendo%203DS%20(Decrypted)/",
    "gb": "No-Intro/Nintendo%20-%20Game%20Boy/",
    "gba": "No-Intro/Nintendo%20-%20Game%20Boy%20Advance/",
    "nds": "No-Intro/Nintendo%20-%20Nintendo%20DS%20%28Decrypted%29/"
}

DOWNLOAD_DIR = "Roms"
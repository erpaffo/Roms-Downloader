import logging
import os
from PySide6.QtCore import QSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BASE_URL = "https://myrient.erista.me/files/"
CONSOLES = {
    "Atari 2600": "No-Intro/Atari%20-%202600/",
    "Atari 5200": "No-Intro/Atari%20-%205200/",
    "Atari 7800": "No-Intro/Atari%20-%207800/",
    "Microsoft Xbox": "Redump/Microsoft%20-%20Xbox/",
    "Microsoft Xbox 360": "Redump/Microsoft%20-%20Xbox%20360/",
    "Nintendo GameBoy": "No-Intro/Nintendo%20-%20Game%20Boy/",
    "Nintendo GameBoy Advance": "No-Intro/Nintendo%20-%20Game%20Boy%20Advance/",
    "Nintendo GameBoy Color": "No-Intro/Nintendo%20-%20Game%20Boy%20Color/",
    "Nintendo 3DS": "No-Intro/Nintendo%20-%20Nintendo%203DS%20(Decrypted)/",
    "Nintendo DS": "No-Intro/Nintendo%20-%20Nintendo%20DS%20(Decrypted)/",
    "Nintendo 64": "No-Intro/Nintendo%20-%20Nintendo%2064%20%28BigEndian%29/",
    "Nintendo GameCube": "Redump/Nintendo%20-%20GameCube%20-%20NKit%20RVZ%20%5Bzstd-19-128k%5D/",
    "Nintendo Wii": "Redump/Nintendo%20-%20Wii%20-%20NKit%20RVZ%20%5Bzstd-19-128k%5D/",
    "Nintendo Wii U": "Redump/Nintendo%20-%20Wii%20U%20-%20Disc%20Keys/",
    "Sony PlayStation": "Redump/Sony%20-%20PlayStation/",
    "Sony PlayStation 2": "Redump/Sony%20-%20PlayStation%202/",
    "Sony PlayStation 3": "Redump/Sony%20-%20PlayStation%203/",
    "Sony PlayStation Portable": "Redump/Sony%20-%20PlayStation%20Portable/"
}

RETROARCH_NAME = r"C:\RetroArch-Win64\retroarch.exe"

CACHE_FOLDER = os.path.join(os.getcwd(), "cache")
if not os.path.exists(CACHE_FOLDER):
    os.makedirs(CACHE_FOLDER)

SETTINGS_ORG = "MyCompany"
SETTINGS_APP = "RomsDownloader"
settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

# Se l'utente non ha già impostato la cartella, usa un default
DEFAULT_DOWNLOADS_FOLDER = os.path.join(os.getcwd(), "downloads")
USER_DOWNLOADS_FOLDER = settings.value("download_folder", DEFAULT_DOWNLOADS_FOLDER)

# Assicurati che la cartella esista
if not os.path.exists(USER_DOWNLOADS_FOLDER):
    os.makedirs(USER_DOWNLOADS_FOLDER)

def set_user_download_folder(new_path):
    global USER_DOWNLOADS_FOLDER
    USER_DOWNLOADS_FOLDER = new_path
    if not os.path.exists(USER_DOWNLOADS_FOLDER):
        os.makedirs(USER_DOWNLOADS_FOLDER)
    settings.setValue("download_folder", USER_DOWNLOADS_FOLDER)
import logging
import os
from PySide6.QtCore import QSettings

# Configurazione di base del logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# URL base per lo scraping
BASE_URL = "https://myrient.erista.me/files/"

# Dizionario delle console con i relativi percorsi per lo scraping
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

# Percorso dell'eseguibile di RetroArch (modifica se necessario)
RETROARCH_NAME = r"C:\RetroArch-Win64\retroarch.exe"

# Cartella per la cache
CACHE_FOLDER = os.path.join(os.getcwd(), "cache")
if not os.path.exists(CACHE_FOLDER):
    os.makedirs(CACHE_FOLDER)

# Configurazione persistente con QSettings
SETTINGS_ORG = "MyCompany"
SETTINGS_APP = "RomsDownloader"
settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

# Percorso di default per i download e la libreria
DEFAULT_DOWNLOADS_FOLDER = os.path.join(os.getcwd(), "downloads")
USER_DOWNLOADS_FOLDER = settings.value("download_folder", DEFAULT_DOWNLOADS_FOLDER)
if not os.path.exists(USER_DOWNLOADS_FOLDER):
    os.makedirs(USER_DOWNLOADS_FOLDER)

def set_user_download_folder(new_path):
    """Imposta il percorso della cartella dei download e lo salva in QSettings."""
    print(f"Impostazione della cartella dei download su: {new_path}")
    USER_DOWNLOADS_FOLDER = new_path
    if not os.path.exists(USER_DOWNLOADS_FOLDER):
        os.makedirs(USER_DOWNLOADS_FOLDER)
    settings.setValue("download_folder", USER_DOWNLOADS_FOLDER)
    print(f"Cartella dei download impostata su: {USER_DOWNLOADS_FOLDER}")

# Impostazione del numero massimo di download concorrenti (default 2)
MAX_CONCURRENT_DOWNLOADS = int(settings.value("max_dl", 2))
def set_max_concurrent_downloads(value):
    """Imposta il numero massimo di download concorrenti e lo salva in QSettings."""
    global MAX_CONCURRENT_DOWNLOADS
    MAX_CONCURRENT_DOWNLOADS = value
    settings.setValue("max_dl", MAX_CONCURRENT_DOWNLOADS)

def add_console(name, link):
    """
    Aggiunge una nuova console al dizionario CONSOLES.
    'name' è il titolo visualizzato e 'link' è il percorso relativo usato per lo scraping.
    """
    CONSOLES[name] = link
    # Se vuoi, puoi persistere questa modifica in QSettings o in un file di configurazione.

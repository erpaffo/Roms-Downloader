import logging
import os
import sys
from PySide6.QtCore import QSettings

# Configurazione di base del logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def get_app_base_path():
    """
    Determina la directory base dell'applicazione.
    Se l'app è bundlizzata (es. con PyInstaller), restituisce la directory dell'eseguibile.
    Altrimenti, restituisce la directory in cui si trova questo file.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# Definizione della directory base e della struttura dati
BASE_DIR = get_app_base_path()
DATA_DIR = os.path.join(BASE_DIR, "app_data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Configurazione persistente tramite QSettings
SETTINGS_ORG = "MyCompany"
SETTINGS_APP = "RomsDownloader"
settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

# Cartella per i download (e la libreria)
DEFAULT_DOWNLOADS_FOLDER = os.path.join(DATA_DIR, "downloads")
USER_DOWNLOADS_FOLDER = settings.value("download_folder", DEFAULT_DOWNLOADS_FOLDER)
if not os.path.exists(USER_DOWNLOADS_FOLDER):
    os.makedirs(USER_DOWNLOADS_FOLDER)

# Cartella per la cache
CACHE_FOLDER = os.path.join(DATA_DIR, "cache")
if not os.path.exists(CACHE_FOLDER):
    os.makedirs(CACHE_FOLDER)

# Cartella principale per l'emulazione: contiene RetroArch, core e file di configurazione
EMULATOR_FOLDER = os.path.join(DATA_DIR, "emulator")
if not os.path.exists(EMULATOR_FOLDER):
    os.makedirs(EMULATOR_FOLDER)

# Cartella per RetroArch estratto
RETROARCH_EXTRACT_FOLDER = os.path.join(EMULATOR_FOLDER, "RetroArch")
if not os.path.exists(RETROARCH_EXTRACT_FOLDER):
    os.makedirs(RETROARCH_EXTRACT_FOLDER)

# Cartella per i core
CORES_FOLDER = os.path.join(EMULATOR_FOLDER, "cores")
if not os.path.exists(CORES_FOLDER):
    os.makedirs(CORES_FOLDER)

# Cartella per i file di configurazione degli emulatori
EMULATOR_CONFIG_FOLDER = os.path.join(EMULATOR_FOLDER, "config")
if not os.path.exists(EMULATOR_CONFIG_FOLDER):
    os.makedirs(EMULATOR_CONFIG_FOLDER)

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

# Imposta CORE_EXT e il base URL per i nightly build in base al sistema operativo
if sys.platform.startswith("win"):
    CORE_EXT = ".dll"
    NIGHTLY_URL = "https://buildbot.libretro.com/nightly/windows/x86_64/latest/"
elif sys.platform.startswith("linux"):
    CORE_EXT = ".so"
    NIGHTLY_URL = "https://buildbot.libretro.com/nightly/linux/x86_64/latest/"
elif sys.platform.startswith("darwin"):
    CORE_EXT = ".dylib"
    NIGHTLY_URL = "https://buildbot.libretro.com/nightly/apple/osx/x86_64/latest/"
else:
    CORE_EXT = ".so"
    NIGHTLY_URL = ""

# Funzione helper per le risorse (utile con PyInstaller)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = BASE_DIR
    return os.path.join(base_path, relative_path)

# Mappa dei core di default: per ogni console, il nome base del core (senza estensione)
DEFAULT_CORES = {
    "Atari 2600": "stella2023_libretro",
    "Atari 5200": "a5200_libretro",
    "Atari 7800": "prosystem_libretro",
    "Nintendo GameBoy": "gambatte_libretro",
    "Nintendo GameBoy Advance": "mgba_libretro",
    "Nintendo GameBoy Color": "gambatte_libretro",
    "Nintendo 3DS": "citra_libretro",
    "Nintendo DS": "melonds_libretro",
    "Nintendo 64": "mupen64plus_next_libretro",
    "Nintendo GameCube": "dolphin_libretro",
    "Nintendo Wii": "dolphin_libretro",
    "Sony PlayStation": "pcsx_rearmed_libretro",
    "Sony PlayStation 2": "pcsx2_libretro",
    "Sony PlayStation 3": "rpcs3_libretro",
    "Sony PlayStation Portable": "ppsspp_libretro"
}

def set_user_download_folder(new_path):
    """Imposta il percorso della cartella dei download e lo salva in QSettings."""
    global USER_DOWNLOAD_FOLDER
    USER_DOWNLOAD_FOLDER = new_path
    if not os.path.exists(USER_DOWNLOAD_FOLDER):
        os.makedirs(USER_DOWNLOAD_FOLDER)
    settings.setValue("download_folder", USER_DOWNLOAD_FOLDER)
    print(f"Cartella dei download impostata su: {USER_DOWNLOAD_FOLDER}")

# Numero massimo di download concorrenti (default 2)
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

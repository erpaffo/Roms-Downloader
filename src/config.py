import logging
import os
import sys
import shutil
from PySide6.QtCore import QSettings

try:
    import platformdirs
except ImportError:
    print("Errore: La libreria 'platformdirs' non è installata.")
    print("Esegui: pip install platformdirs")
    platformdirs = None

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_app_base_path():
    """Determines the base directory for resource loading."""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        else:
            return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller.
    Assumes relative_path is relative to the project root (e.g., "src/data/file.txt").
    """
    try:
        base_path = get_app_base_path()
    except Exception:
        base_path = os.path.abspath(".")

    final_path = os.path.join(base_path, relative_path)
    return final_path


APP_NAME = "RomsDownloader"
AUTHOR_NAME = "YourAppNameOrCompany"

if platformdirs:
    USER_DATA_DIR = platformdirs.user_data_dir(APP_NAME, AUTHOR_NAME)
    USER_CONFIG_DIR = platformdirs.user_config_dir(APP_NAME, AUTHOR_NAME)
    USER_CACHE_DIR = platformdirs.user_cache_dir(APP_NAME, AUTHOR_NAME)
else:
    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)
    USER_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", APP_NAME)
    USER_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", APP_NAME)

DATA_DIR = USER_DATA_DIR
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

SETTINGS_ORG = AUTHOR_NAME
SETTINGS_APP = APP_NAME
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
settings = QSettings(SETTINGS_ORG, SETTINGS_APP)

STYLES_REL_PATH = os.path.join("src", "gui", "styles")
DEFAULT_THEME_FILENAME = "default_light_theme.qss"  # O il nome del tuo tema predefinito


DEFAULT_DOWNLOADS_FOLDER = os.path.join(DATA_DIR, "downloads")
USER_DOWNLOADS_FOLDER = settings.value("download_folder", DEFAULT_DOWNLOADS_FOLDER)
if not os.path.exists(USER_DOWNLOADS_FOLDER):
    os.makedirs(USER_DOWNLOADS_FOLDER, exist_ok=True)

CACHE_FOLDER = USER_CACHE_DIR
if not os.path.exists(CACHE_FOLDER):
    os.makedirs(CACHE_FOLDER, exist_ok=True)

EMULATOR_CONFIG_FOLDER = os.path.join(USER_CONFIG_DIR, "emulator_config")
if not os.path.exists(EMULATOR_CONFIG_FOLDER):
    os.makedirs(EMULATOR_CONFIG_FOLDER, exist_ok=True)

SYSTEM_FOLDER = os.path.join(DATA_DIR, "system")
if not os.path.exists(SYSTEM_FOLDER):
    try:
        os.makedirs(SYSTEM_FOLDER, exist_ok=True)
        logging.info(f"Cartella System/BIOS creata: {SYSTEM_FOLDER}")
    except OSError as e:
        logging.error(f"Impossibile creare cartella System/BIOS '{SYSTEM_FOLDER}': {e}")

SAVES_BASE_FOLDER = os.path.join(DATA_DIR, "saves")
if not os.path.exists(SAVES_BASE_FOLDER):
    try:
        os.makedirs(SAVES_BASE_FOLDER, exist_ok=True)
        logging.info(f"Cartella base salvataggi creata: {SAVES_BASE_FOLDER}")
    except OSError as e:
        logging.error(
            f"Impossibile creare cartella base salvataggi '{SAVES_BASE_FOLDER}': {e}"
        )


_EMULATOR_REL_PATH_SRC = os.path.join("src", "app_data", "emulator")

RETROARCH_EXTRACT_FOLDER = resource_path(
    os.path.join(_EMULATOR_REL_PATH_SRC, "RetroArch")
)
CORES_FOLDER = resource_path(os.path.join(_EMULATOR_REL_PATH_SRC, "cores"))


def get_save_directory(console_name: str) -> str:
    """
    Generates the absolute path for a console's save directory.
    Creates the directory if it doesn't exist. Uses a safe directory name.
    """
    safe_dir_name = console_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    console_save_dir = os.path.join(SAVES_BASE_FOLDER, safe_dir_name)
    if not os.path.exists(console_save_dir):
        try:
            os.makedirs(console_save_dir, exist_ok=True)
            logging.info(
                f"Cartella salvataggi creata per '{console_name}': {console_save_dir}"
            )
        except OSError as e:
            logging.error(
                f"Impossibile creare cartella salvataggi per '{console_name}' in '{console_save_dir}': {e}"
            )
            return SAVES_BASE_FOLDER
    return console_save_dir


def copy_default_data_on_first_run():
    """
    Copies default configuration files from the source/bundled data to the user's
    configuration directory on the very first run.
    """
    marker_file = os.path.join(USER_CONFIG_DIR, ".first_run_complete")

    if os.path.exists(marker_file):
        return

    logging.info("First run detected. Attempting to copy default configurations...")

    source_config_dir_rel = os.path.join("src", "app_data", "emulator", "config")
    source_config_dir_abs = resource_path(source_config_dir_rel)
    target_config_dir = EMULATOR_CONFIG_FOLDER

    if os.path.isdir(source_config_dir_abs):
        try:
            os.makedirs(target_config_dir, exist_ok=True)
            if sys.version_info >= (3, 8):
                shutil.copytree(
                    source_config_dir_abs, target_config_dir, dirs_exist_ok=True
                )
            else:
                for item in os.listdir(source_config_dir_abs):
                    s = os.path.join(source_config_dir_abs, item)
                    d = os.path.join(target_config_dir, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
            logging.info(f"Default emulator configs copied to: {target_config_dir}")
        except FileExistsError:
            logging.warning(
                f"Target config directory '{target_config_dir}' already exists (unexpected on first run). Skipping copy."
            )
        except Exception as e:
            logging.error(
                f"Failed to copy default emulator configs from '{source_config_dir_abs}' to '{target_config_dir}': {e}"
            )
    else:
        logging.warning(
            f"Bundled default config directory not found at '{source_config_dir_abs}'. Cannot copy defaults."
        )

    try:
        os.makedirs(USER_CONFIG_DIR, exist_ok=True)
        with open(marker_file, "w") as f:
            f.write("Setup complete")
        logging.info(f"First run marker created: {marker_file}")
    except Exception as e:
        logging.error(f"Failed to create first run marker file '{marker_file}': {e}")


copy_default_data_on_first_run()

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
    "Sony PlayStation Portable": "Redump/Sony%20-%20PlayStation%20Portable/",
}

if sys.platform.startswith("win"):
    CORE_EXT = ".dll"
elif sys.platform.startswith("linux"):
    CORE_EXT = ".so"
elif sys.platform.startswith("darwin"):
    CORE_EXT = ".dylib"
else:
    CORE_EXT = ".so"

DEFAULT_CORES = {
    "Atari 2600": "stella2023_libretro",
    "Atari 5200": "a5200_libretro",
    "Atari 7800": "prosystem_libretro",
    "Nintendo GameBoy": "gambatte_libretro",
    "Nintendo GameBoy Advance": "mgba_libretro",
    "Nintendo GameBoy Color": "gambatte_libretro",
    "Nintendo 3DS": "citra_libretro",
    "Nintendo DS": "melondsds_libretro",
    "Nintendo 64": "mupen64plus_next_libretro",
    "Nintendo GameCube": "dolphin_libretro",
    "Nintendo Wii": "dolphin_libretro",
    "Sony PlayStation": "pcsx_rearmed_libretro",
    "Sony PlayStation 2": "pcsx2_libretro",
    "Sony PlayStation 3": "rpcs3_libretro",
    "Sony PlayStation Portable": "ppsspp_libretro",
}

CORE_SETTINGS_DEFAULTS = {
    "video_vsync": "false",
    "video_driver": "gl",
    "video_fullscreen": "false",
    "audio_driver": "",
    "input_driver": "",
}


def set_user_download_folder(new_path):
    """Sets the user download folder path and saves it to settings."""
    global USER_DOWNLOADS_FOLDER
    USER_DOWNLOADS_FOLDER = new_path
    if not os.path.exists(USER_DOWNLOADS_FOLDER):
        os.makedirs(USER_DOWNLOADS_FOLDER, exist_ok=True)
    settings.setValue("download_folder", USER_DOWNLOADS_FOLDER)
    logging.info(f"User download folder set to: {USER_DOWNLOADS_FOLDER}")


MAX_CONCURRENT_DOWNLOADS = int(settings.value("max_dl", 4))


def set_max_concurrent_downloads(value):
    """Sets the maximum concurrent downloads and saves it to settings."""
    global MAX_CONCURRENT_DOWNLOADS
    try:
        val_int = int(value)
        if 1 <= val_int <= 10:
            MAX_CONCURRENT_DOWNLOADS = val_int
            settings.setValue("max_dl", MAX_CONCURRENT_DOWNLOADS)
            logging.info(f"Max concurrent downloads set to: {MAX_CONCURRENT_DOWNLOADS}")
        else:
            logging.warning(
                f"Invalid value for max concurrent downloads: {value}. Must be between 1 and 10."
            )
    except ValueError:
        logging.error(
            f"Invalid non-integer value for max concurrent downloads: {value}"
        )


def add_console(name, link):
    """
    Adds or updates a console entry in the CONSOLES dictionary.
    (Note: This change is runtime only, not persistent unless saved elsewhere)
    """
    if name and link:
        CONSOLES[name] = link
        logging.info(f"Console '{name}' added/updated at runtime.")
    else:
        logging.warning("Attempted to add console with empty name or link.")


METADATA_FOLDER = os.path.join(USER_DATA_DIR, "metadata")
COVERS_FOLDER = os.path.join(METADATA_FOLDER, "covers")

# Crea le cartelle se non esistono
if not os.path.exists(METADATA_FOLDER):
    try:
        os.makedirs(METADATA_FOLDER, exist_ok=True)
        logging.info(f"Cartella Metadati creata: {METADATA_FOLDER}")
    except OSError as e:
        logging.error(f"Impossibile creare cartella Metadati '{METADATA_FOLDER}': {e}")

if not os.path.exists(COVERS_FOLDER):
    try:
        os.makedirs(COVERS_FOLDER, exist_ok=True)
        logging.info(f"Cartella Copertine creata: {COVERS_FOLDER}")
    except OSError as e:
        logging.error(f"Impossibile creare cartella Copertine '{COVERS_FOLDER}': {e}")

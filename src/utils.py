import logging
import re
import zipfile
import os
import sys
import subprocess
import platform
import requests
from pyunpack import Archive
import shutil
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from src.config import RETROARCH_EXTRACT_FOLDER, SYSTEM_FOLDER, get_save_directory
from src.console_keybindings import CONSOLE_KEYBINDINGS
from src.conversion import convert_binding
from src.default_keybindings import DEFAULT_KEYBINDINGS
from src.config import CORE_SETTINGS_DEFAULTS

ALLOWED_NATIONS = {"Japan", "USA", "Europe", "Spain", "Italy", "Germany", "France", "China"}

def extract_nations(game_name):
    """
    Estrae le nazioni dal nome del gioco cercando un pattern tra parentesi.
    Ad esempio: "Final Fantasy (Europe, USA)" restituirà ["Europe", "USA"].
    """
    pattern = r'\((.*?)\)'
    match = re.search(pattern, game_name)
    if match:
        nations_str = match.group(1)
        nations = [s.strip() for s in nations_str.split(',')]
        return [nation for nation in nations if nation in ALLOWED_NATIONS]
    return []

def extract_zip(zip_path, extract_to):
    """
    Estrae il contenuto del file ZIP specificato in zip_path nella directory extract_to.
    Se l'estrazione ha successo, elimina il file ZIP.
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        os.remove(zip_path)
        return True
    except Exception as e:
        print(f"Errore nell'estrazione: {e}")
        return False

def find_emulator_path(emulator_name):
    """
    Cerca il percorso eseguibile dell'emulatore dato il suo nome.
    Utilizza shutil.which per individuare l'eseguibile nel PATH di sistema.
    Se non viene trovato, viene sollevata un'eccezione.
    """
    path = shutil.which(emulator_name)
    if path:
        return path
    else:
        raise FileNotFoundError(f"Emulatore '{emulator_name}' non trovato nel PATH di sistema. "
                                "Assicurati di averlo installato e che sia accessibile.")

def format_rate(rate):
    """
    Converte una velocità (in byte/sec) in una stringa formattata.
    Se la velocità è inferiore a 1 MB/s, usa KB/s, altrimenti MB/s.
    """
    if rate < 1024*1024:
        return f"{rate/1024:.1f} KB/s"
    else:
        return f"{rate/(1024*1024):.1f} MB/s"

def format_space(bytes_value):
    """
    Converte uno spazio (in byte) in una stringa formattata.
    Se lo spazio è inferiore a 1 MB, usa KB, altrimenti MB.
    """
    if bytes_value < 1024*1024:
        return f"{bytes_value/1024:.1f} KB"
    else:
        return f"{bytes_value/(1024*1024):.1f} MB"

def find_retroarch():
    """
    Finds the RetroArch executable.

    Checks system PATH, then the application's configured data directory,
    and finally common system-wide locations.
    Returns the absolute path to the executable or None if not found.
    """
    path_in_syspath = shutil.which("retroarch")
    if path_in_syspath and os.path.exists(path_in_syspath):
        logging.info(f"RetroArch found in PATH: {path_in_syspath}")
        return path_in_syspath
    logging.info(RETROARCH_EXTRACT_FOLDER)
    if RETROARCH_EXTRACT_FOLDER: # Assicurati che la variabile sia stata importata
        exe_name = "retroarch.exe" if sys.platform.startswith("win") else "retroarch"
        path_in_appdata = os.path.join(RETROARCH_EXTRACT_FOLDER, exe_name)
        logging.info(f"Checking for RetroArch in configured app data path: {path_in_appdata}")
        if os.path.exists(path_in_appdata):
            logging.info(f"RetroArch found in configured app data path: {path_in_appdata}")
            return os.path.abspath(path_in_appdata) # Restituisci percorso assoluto
    else:
         logging.warning("RETROARCH_EXTRACT_FOLDER non definito o non importato, salto controllo")


    possible = []
    if sys.platform.startswith("win"):
        possible = [r"C:\RetroArch-Win64\retroarch.exe", r"C:\Program Files\RetroArch\retroarch.exe"]
    elif sys.platform.startswith("linux"):
        possible = ["/usr/bin/retroarch", "/usr/local/bin/retroarch"]
    elif sys.platform.startswith("darwin"):
        possible = ["/Applications/RetroArch.app/Contents/MacOS/retroarch"]

    logging.debug(f"RetroArch not found in PATH or app data. Checking common paths: {possible}")
    for p in possible:
        if os.path.exists(p):
            logging.info(f"RetroArch found in common location: {p}")
            return p

    logging.error("RetroArch executable not found in PATH, app data, or common locations.")
    return None

def is_retroarch_installed():
    return find_retroarch() is not None

def update_emulator_config(config_path, new_bindings):
    """
    Aggiorna il file di configurazione nel percorso config_path.
    Per ogni binding, se esiste una conversione nel dizionario KEY_MAPPING, salva il valore convertito.
    """
    lines = []
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            lines = f.readlines()

    for command, user_value in new_bindings.items():
        mapped_value = convert_binding(user_value)
        found = False
        for idx, line in enumerate(lines):
            if "=" in line:
                key, _ = line.split("=", 1)
                if key.strip() == command:
                    lines[idx] = f'{command} = "{mapped_value}"\n'
                    found = True
                    break
        if not found:
            lines.append(f'{command} = "{mapped_value}"\n')

    with open(config_path, "w") as f:
        f.writelines(lines)

def convert_key(key):
    di = {"+":"add",
          "-": "subtract"}
    
def create_default_core_config(core_config_path: str, console_name: str, core_base_name: str):
    """
    Creates a default core-specific config file if it doesn't exist.
    Merges global defaults, core setting defaults, console P1 defaults,
    and calculated save/system paths. Converts keybindings.
    Returns True on success, False on failure.
    """
    if os.path.exists(core_config_path):
        logging.debug(f"File config core già esistente, non creato: {core_config_path}")
        return True

    logging.info(f"Creazione file config default per '{console_name}'/'{core_base_name}' in: {core_config_path}")

    try:
        combined_settings = DEFAULT_KEYBINDINGS.copy()
        combined_settings.update(CORE_SETTINGS_DEFAULTS)
        p1_defaults = CONSOLE_KEYBINDINGS.get(console_name, {})
        combined_settings.update(p1_defaults)

        save_dir = get_save_directory(console_name)
        combined_settings['savefile_directory'] = os.path.abspath(save_dir)
        combined_settings['savestate_directory'] = os.path.abspath(save_dir)
        combined_settings['system_directory'] = os.path.abspath(SYSTEM_FOLDER)

        final_settings = {}
        known_hotkey_commands = set(DEFAULT_KEYBINDINGS.keys()).union(set(p1_defaults.keys()))

        for command, value in combined_settings.items():
            is_known_input = command.startswith("input_") and command in known_hotkey_commands
            is_bool = str(value).lower() in ["true", "false"]
            is_path = command.endswith("_directory")

            if is_known_input and not is_bool and not is_path and value != "nul":
                final_settings[command] = convert_binding(value)
            else:
                final_settings[command] = value

        update_emulator_config(core_config_path, final_settings)
        logging.info(f"File config default creato con successo: {core_config_path}")
        return True

    except Exception as e:
        logging.exception(f"Errore imprevisto durante la creazione del file config default '{core_config_path}': {e}")
        return False
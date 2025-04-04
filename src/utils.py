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
from src.config import BASE_DIR, USER_DOWNLOADS_FOLDER, RETROARCH_EXTRACT_FOLDER
from src.conversion import convert_binding

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
    """Cerca l'eseguibile di RetroArch sul sistema, includendo il percorso relativo dell'app."""
    # 1. Cerca nel PATH di sistema (modo preferito)
    path = shutil.which("retroarch")
    if path and os.path.exists(path): # Aggiunto check exists per sicurezza con which
        print(f"RetroArch trovato nel PATH: {path}")
        return path

    # 2. Costruisci il percorso relativo basato sulla configurazione
    # Determina il nome dell'eseguibile in base all'OS
    exe_name = "retroarch.exe" if sys.platform.startswith("win") else "retroarch"
    # Il percorso è RETROARCH_EXTRACT_FOLDER + nome eseguibile
    relative_path_from_config = os.path.join(RETROARCH_EXTRACT_FOLDER, exe_name)

    # Controlla se esiste nel percorso relativo definito in config.py
    if os.path.exists(relative_path_from_config):
        print(f"RetroArch trovato nel percorso relativo dell'app: {relative_path_from_config}")
        return relative_path_from_config

    # 3. Fallback: Cerca in percorsi comuni specifici del sistema operativo (come ultima risorsa)
    possible = []
    if sys.platform.startswith("win"):
        # Rimuovi il percorso relativo già controllato sopra
        possible = [r"C:\RetroArch-Win64\retroarch.exe", r"C:\Program Files\RetroArch\retroarch.exe"]
    elif sys.platform.startswith("linux"):
        # Rimuovi percorsi hardcoded che potrebbero non essere corretti
        possible = ["/usr/bin/retroarch", "/usr/local/bin/retroarch",
                    # Aggiungi un percorso relativo alla directory base dell'app come fallback estremo
                    os.path.join(BASE_DIR, "..", "app_data", "emulator", "RetroArch", "retroarch")] # Percorso relativo a src
    elif sys.platform.startswith("darwin"):
        possible = ["/Applications/RetroArch.app/Contents/MacOS/retroarch"]

    print(f"RetroArch non trovato nel PATH o nel percorso relativo ({relative_path_from_config}). Controllo percorsi comuni: {possible}")
    for p in possible:
        if os.path.exists(p):
            print(f"RetroArch trovato nel percorso comune: {p}")
            return p

    # 4. Se non trovato da nessuna parte
    print("RetroArch non trovato.")
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
        # Convertiamo il valore prima di salvarlo
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
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
from src.config import USER_DOWNLOADS_FOLDER, RETROARCH_EXTRACT_FOLDER, RETROARCH_URLS

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
    """Cerca l'eseguibile di RetroArch sul sistema."""
    path = shutil.which("retroarch")
    if path:
        return path

    if sys.platform.startswith("win"):
        possible = [r"C:\RetroArch-Win64\retroarch.exe", r"C:\Program Files\RetroArch\retroarch.exe", f"{RETROARCH_EXTRACT_FOLDER}/retroarch.exe"]
    elif sys.platform.startswith("linux"):
        possible = ["/home/erpaffo/Scrivania/Roms-Downloader/emulator/retroarch", "/usr/bin/retroarch", "/usr/local/bin/retroarch"]
    elif sys.platform.startswith("darwin"):
        possible = ["/Applications/RetroArch.app/Contents/MacOS/retroarch"]
    else:
        possible = []
    for p in possible:
        if os.path.exists(p):
            return p
    return None

def is_retroarch_installed():
    return find_retroarch() is not None

def download_and_install_retroarch(log_func=print):
    system_os = platform.system()
    url = RETROARCH_URLS.get(system_os)
    if not url:
        log_func(f"Sistema operativo {system_os} non supportato.")
        return False

    os.makedirs(USER_DOWNLOADS_FOLDER, exist_ok=True)
    local_file = os.path.join(USER_DOWNLOADS_FOLDER, os.path.basename(url))

    log_func(f"Scarico RetroArch da: {url}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_file, 'wb') as f:
            for chunk in r.iter_content(1024*1024):
                f.write(chunk)

    log_func("Download completato. Estrazione in corso...")
    Archive(local_file).extractall(RETROARCH_EXTRACT_FOLDER)
    os.remove(local_file)
    log_func("RetroArch installato correttamente.")

    retroarch_exe = find_retroarch()
    return retroarch_exe is not None

import os
import sys
import requests
import zipfile
from bs4 import BeautifulSoup

def download_and_extract_core(core_base):
    """
    Scarica ed estrae il core se non presente.
    core_base: il nome base del core (es. "stella2023_libretro")
    Restituisce il percorso completo del core estratto o None in caso di errore.
    """
    from src.config import NIGHTLY_URL, CORES_FOLDER, CORE_EXT
    expected_zip_name = core_base + ".zip"

    try:
        response = requests.get(NIGHTLY_URL)
        response.raise_for_status()
    except Exception as e:
        print(f"Errore nel contattare {NIGHTLY_URL}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    zip_url = None
    for link in soup.find_all("a"):
        href = link.get("href")
        if href and expected_zip_name in href and href.endswith(".zip"):
            zip_url = NIGHTLY_URL + href
            break

    if not zip_url:
        print(f"Core {core_base} non trovato nella pagina nightly.")
        return None

    try:
        r = requests.get(zip_url, stream=True)
        r.raise_for_status()
        zip_path = os.path.join(CORES_FOLDER, expected_zip_name)
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        print(f"Errore nel download del core {core_base}: {e}")
        return None

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(CORES_FOLDER)
        os.remove(zip_path)
    except Exception as e:
        print(f"Errore nell'estrazione del core {core_base}: {e}")
        return None

    core_filename = core_base + CORE_EXT
    core_path = os.path.join(CORES_FOLDER, core_filename)
    if os.path.exists(core_path):
        print(f"Core {core_base} scaricato ed estratto in: {core_path}")
        return core_path
    else:
        print(f"Core {core_base} non trovato dopo l'estrazione.")
        return None

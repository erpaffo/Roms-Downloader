import re
import zipfile
import os
import sys
import subprocess
import shutil
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

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
        possible = [r"C:\RetroArch-Win64\retroarch.exe", r"C:\Program Files\RetroArch\retroarch.exe"]
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
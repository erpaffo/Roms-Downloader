import os
import requests
from PySide6.QtCore import QObject, Signal
import logging
from src.config import DOWNLOAD_DIR  # Importa la cartella di download

class DownloadWorker(QObject):
    # Emette (game_name, downloaded_bytes, total_bytes)
    progress_update = Signal(str, int, int)
    # Emette (game_name, local_filename)
    finished = Signal(str, str)
    log = Signal(str)
    
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.cancelled = False
    
    def run(self):
        url = self.game['link']
        filename = os.path.basename(url)
        console_folder = self.game.get('console', 'default')
        # Crea la cartella per la console all'interno della cartella di download
        destination_dir = os.path.join(DOWNLOAD_DIR, console_folder)
        os.makedirs(destination_dir, exist_ok=True)
        local_filename = os.path.join(destination_dir, filename)
        self.log.emit(f"Inizio download: {filename} in {destination_dir}")
        try:
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                total = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1 MB
                with open(local_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if self.cancelled:
                            self.log.emit(f"Download annullato: {filename}")
                            self.finished.emit(self.game['name'], "")
                            return
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.progress_update.emit(self.game['name'], downloaded, total)
            self.log.emit(f"Download completato: {filename}")
            self.finished.emit(self.game['name'], local_filename)
        except Exception as e:
            self.log.emit(f"Errore nel download di {filename}: {e}")
            self.finished.emit(self.game['name'], "")
    
    def cancel(self):
        self.cancelled = True

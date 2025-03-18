import os
import time
import requests
from PySide6.QtCore import QObject, Signal
from src.config import DOWNLOADS_FOLDER
from src.utils import extract_zip

class DownloadWorker(QObject):
    # Ora il segnale emette: (game_name, downloaded_bytes, total_bytes, speed (B/s), remaining_time (sec))
    progress_update = Signal(str, int, int, float, float)
    finished = Signal(str, str)  # (game_name, local_filename)
    log = Signal(str)
    
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.cancelled = False
    
    def run(self):
        url = self.game['link']
        filename = os.path.basename(url)
        console_folder = self.game.get('console', 'default')
        destination_dir = os.path.join(DOWNLOADS_FOLDER, console_folder)
        os.makedirs(destination_dir, exist_ok=True)
        local_file = os.path.join(destination_dir, filename)
        self.log.emit(f"Inizio download: {filename} in {destination_dir}")
        try:
            start_time = time.time()
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                total = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1 MB
                with open(local_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if self.cancelled:
                            self.log.emit(f"Download annullato: {filename}")
                            self.finished.emit(self.game['name'], "")
                            return
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            elapsed_time = time.time() - start_time
                            # Calcola la velocità (B/s)
                            speed = downloaded / elapsed_time if elapsed_time > 0 else 0
                            # Calcola il tempo rimanente (sec)
                            remaining_time = ((total - downloaded) / speed) if speed > 0 else -1
                            self.progress_update.emit(self.game['name'], downloaded, total, speed, remaining_time)
            self.log.emit(f"Download completato: {filename}")
            base, ext = os.path.splitext(local_file)
            if ext.lower() == ".zip":
                self.log.emit(f"Estrazione di {filename}")
                if extract_zip(local_file, destination_dir):
                    extracted_files = [os.path.join(destination_dir, f) for f in os.listdir(destination_dir) if not f.lower().endswith(".zip")]
                    local_file = extracted_files[0] if extracted_files else ""
            self.finished.emit(self.game['name'], local_file)
        except Exception as e:
            self.log.emit(f"Errore nel download di {filename}: {e}")
            self.finished.emit(self.game['name'], "")
    
    def cancel(self):
        self.cancelled = True

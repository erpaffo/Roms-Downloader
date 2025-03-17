from PySide6.QtCore import QObject, Signal, QThread

class DownloadManager(QObject):
    log = Signal(str)
    overall_progress = Signal(int)  # percentuale globale
    finished = Signal()
    file_progress = Signal(str, int)  # (game_name, percent)
    queue_updated = Signal()  # Nuovo segnale per aggiornare la coda

    def __init__(self, queue, update_queue_callback):
        super().__init__()
        self.queue = queue.copy()  # Lista dei giochi da scaricare
        self.update_queue_callback = update_queue_callback  # Potresti non usarla direttamente
        self.cancelled = False
        self.completed_downloads = []
        self.total_bytes = sum(game['size_bytes'] for game in self.queue)
        self.downloaded_bytes = {game['name']: 0 for game in self.queue}
        self.active_worker = None  # Un solo download alla volta
        self.thread = None

    def process_queue(self):
        self.log.emit("Download Manager avviato.")
        self.start_next_download()

    def start_next_download(self):
        if self.cancelled:
            self.log.emit("Download annullati.")
            self.finished.emit()
            return
        if self.queue:
            game = self.queue.pop(0)
            self.queue_updated.emit()
            self.log.emit(f"Avvio download per: {game['name']}")
            self.thread = QThread()
            from src.workers.download_worker import DownloadWorker
            self.worker = DownloadWorker(game)
            self.worker.moveToThread(self.thread)
            self.worker.progress_update.connect(self.on_worker_progress)
            self.worker.log.connect(self.log.emit)
            self.worker.finished.connect(self.on_worker_finished)
            self.thread.started.connect(self.worker.run)
            self.thread.start()
            self.active_worker = (self.worker, self.thread)
        else:
            self.log.emit("Tutti i download completati.")
            self.finished.emit()

    def on_worker_progress(self, game_name, downloaded, total):
        self.downloaded_bytes[game_name] = downloaded
        percent_file = int((downloaded / total) * 100) if total > 0 else 0
        self.file_progress.emit(game_name, percent_file)
        
        overall_downloaded = float(sum(self.downloaded_bytes.values()))
        total_bytes = float(self.total_bytes) if self.total_bytes > 0 else 1
        ratio = overall_downloaded / total_bytes
        overall_percent = int(ratio * 100)
        overall_percent = min(overall_percent, 100)
        self.overall_progress.emit(overall_percent)


    def on_worker_finished(self, game_name, local_filename):
        self.thread.quit()
        self.thread.wait()
        if local_filename:
            self.completed_downloads.append(local_filename)
            self.file_progress.emit(game_name, 100)
        self.active_worker = None
        self.start_next_download()

    def cancel_all(self):
        self.cancelled = True
        self.log.emit("Annullamento di tutti i download...")
        if self.active_worker:
            worker, _ = self.active_worker
            worker.cancel()
        self.queue.clear()
        self.queue_updated.emit()  
        self.finished.emit()

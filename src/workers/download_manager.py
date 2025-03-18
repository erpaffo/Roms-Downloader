from PySide6.QtCore import QObject, Signal, QThread

class DownloadManager(QObject):
    log = Signal(str)
    overall_progress = Signal(int)  # percentuale globale
    finished = Signal()
    file_progress = Signal(str, int)  # (game_name, percent_file)
    detailed_progress = Signal(str, float, float, float)  # (game_name, speed, remaining_time, space_remaining)
    file_finished = Signal(str)  # Segnale emesso quando un file finisce il download

    def __init__(self, queue, update_queue_callback, max_concurrent=2):
        super().__init__()
        self.queue = queue.copy()  # Lista dei giochi da scaricare
        self.update_queue_callback = update_queue_callback
        self.max_concurrent = max_concurrent
        self.cancelled = False
        self.completed_downloads = []
        self.total_bytes = sum(game['size_bytes'] for game in self.queue)
        self.downloaded_bytes = {game['name']: 0 for game in self.queue}
        self.active_workers = []  # Lista delle tuple (worker, thread)

    def process_queue(self):
        self.log.emit("Download Manager avviato.")
        self.start_new_downloads()

    def start_new_downloads(self):
        # Avvia nuovi download fino a raggiungere il limite e finché ci sono file in coda
        while not self.cancelled and self.queue and len(self.active_workers) < self.max_concurrent:
            game = self.queue.pop(0)
            self.update_queue_callback()  # Aggiorna la visualizzazione della coda se necessario
            self.log.emit(f"Avvio download per: {game['name']}")
            thread = QThread()
            from src.workers.download_worker import DownloadWorker
            worker = DownloadWorker(game)
            worker.moveToThread(thread)
            # Usa una lambda per passare anche worker e thread al metodo on_worker_finished
            worker.finished.connect(lambda gn, lf, w=worker, t=thread: self.on_worker_finished(gn, lf, w, t))
            worker.progress_update.connect(self.on_worker_progress)
            worker.log.connect(self.log.emit)
            thread.started.connect(worker.run)
            thread.start()
            self.active_workers.append((worker, thread))
        if not self.queue and not self.active_workers:
            self.log.emit("Tutti i download completati.")
            self.finished.emit()

    def on_worker_progress(self, game_name, downloaded, total, speed, remaining_time):
        self.downloaded_bytes[game_name] = downloaded
        percent_file = int(downloaded / total * 100) if total > 0 else 0
        self.file_progress.emit(game_name, percent_file)
        overall_downloaded = sum(self.downloaded_bytes.values())
        overall_percent = int((overall_downloaded / self.total_bytes) * 100) if self.total_bytes > 0 else 0
        overall_percent = min(overall_percent, 100)
        self.overall_progress.emit(overall_percent)
        space_remaining = total - downloaded
        self.detailed_progress.emit(game_name, speed, remaining_time, space_remaining)

    def on_worker_finished(self, game_name, local_filename, worker, thread):
        thread.quit()
        thread.wait()
        if local_filename:
            self.completed_downloads.append(local_filename)
            self.file_progress.emit(game_name, 100)
        self.file_finished.emit(game_name)
        # Rimuovi il worker dalla lista degli attivi
        self.active_workers = [aw for aw in self.active_workers if aw[0] != worker]
        self.start_new_downloads()

    def cancel_all(self):
        self.cancelled = True
        self.log.emit("Annullamento di tutti i download...")
        for worker, _ in self.active_workers:
            worker.cancel()
        self.queue.clear()
        self.update_queue_callback()
        self.finished.emit()

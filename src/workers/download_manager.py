import logging
from PySide6.QtCore import QObject, Signal, QThread
from src.workers.download_worker import (
    DownloadWorker,
)  # Assuming this import exists at the top or is handled elsewhere


class DownloadManager(QObject):
    log = Signal(str)
    overall_progress = Signal(int)
    finished = Signal()
    file_progress = Signal(str, int, int, float, float)
    file_finished = Signal(str)

    def __init__(self, queue, update_queue_callback, max_concurrent=2):
        super().__init__()
        self.queue = queue.copy()
        self.update_queue_callback = update_queue_callback
        self.max_concurrent = max_concurrent
        self.cancelled = False
        self.completed_downloads = []

        self.total_bytes = sum(game.get("size_bytes", 0) for game in self.queue)
        self.downloaded_bytes = {
            game.get("name", f"unknown_game_{i}"): 0
            for i, game in enumerate(self.queue)
        }
        self.active_workers = []

        logging.info(
            f"DownloadManager creato con {len(self.queue)} giochi in coda. Max concurrent: {self.max_concurrent}. Total size: {self.total_bytes} bytes."
        )
        if not self.queue:
            logging.warning("DownloadManager creato con una coda VUOTA.")

    def process_queue(self):
        msg = "Download Manager: process_queue chiamato."
        self.log.emit(msg)
        logging.info(msg)

        if not self.queue:
            warning_msg = (
                "Download Manager: La coda interna è vuota all'inizio di process_queue."
            )
            self.log.emit(warning_msg)
            logging.warning(warning_msg)
            self.finished.emit()
            return
        self.start_new_downloads()

    def start_new_downloads(self):
        logging.debug(
            f"Download Manager: start_new_downloads chiamato. Coda={len(self.queue)}, Attivi={len(self.active_workers)}, Max={self.max_concurrent}"
        )
        while (
            not self.cancelled
            and self.queue
            and len(self.active_workers) < self.max_concurrent
        ):
            game = self.queue.pop(0)
            game_name = game.get("name", "Nome Sconosciuto")
            game_link = game.get("link", "Link Sconosciuto")
            log_msg = (
                f"Download Manager: Avvio worker per '{game_name}' (Link: {game_link})"
            )
            self.log.emit(log_msg)
            logging.info(log_msg)

            if self.update_queue_callback:
                try:
                    self.update_queue_callback()
                except Exception as e:
                    logging.error(f"Errore nel chiamare update_queue_callback: {e}")

            thread = QThread()
            from src.workers.download_worker import DownloadWorker

            worker = DownloadWorker(game)
            worker.moveToThread(thread)

            worker.finished.connect(
                lambda gn, lf, w=worker, t=thread: self.on_worker_finished(gn, lf, w, t)
            )
            worker.progress_update.connect(self.on_worker_progress)
            worker.log.connect(self.log.emit)
            thread.started.connect(worker.run)

            thread.start()
            self.active_workers.append((worker, thread))
            logging.debug(
                f"Download Manager: Worker per '{game_name}' avviato e aggiunto agli attivi. Attivi ora: {len(self.active_workers)}"
            )

        if not self.cancelled and not self.queue and not self.active_workers:
            finish_msg = "Download Manager: Coda svuotata e nessun worker attivo. Tutti i download completati."
            self.log.emit(finish_msg)
            logging.info(finish_msg)
            self.finished.emit()
        elif not self.queue:
            logging.info(
                f"Download Manager: Coda interna svuotata, ma ci sono ancora {len(self.active_workers)} worker attivi."
            )

    def on_worker_progress(self, game_name, downloaded, total, speed, remaining_time):
        if game_name in self.downloaded_bytes:
            self.downloaded_bytes[game_name] = downloaded
        else:
            logging.warning(
                f"Chiave '{game_name}' non trovata in downloaded_bytes durante progress update."
            )

        self.file_progress.emit(game_name, downloaded, total, speed, remaining_time)

        overall_downloaded = sum(self.downloaded_bytes.values())
        if self.total_bytes > 0:
            overall_percent = int((overall_downloaded / self.total_bytes) * 100)
            overall_percent = min(overall_percent, 100)
        else:
            overall_percent = 100 if not self.active_workers and not self.queue else 0
        self.overall_progress.emit(overall_percent)

    def on_worker_finished(self, game_name, local_filename, worker, thread):
        finish_log_msg = f"Download Manager: Worker per '{game_name}' ha finito. File locale: '{local_filename if local_filename else 'Nessuno/Errore'}'"
        logging.info(finish_log_msg)

        thread.quit()
        if not thread.wait(1000):
            logging.warning(
                f"Thread per worker '{game_name}' non ha terminato entro 1 secondo."
            )

        if local_filename:
            self.completed_downloads.append(local_filename)
            total_bytes_game = next(
                (
                    g.get("size_bytes", 0)
                    for g in self.queue + [w.game for w, t in self.active_workers]
                    if g.get("name") == game_name
                ),
                0,
            )
            if total_bytes_game > 0:
                self.file_progress.emit(
                    game_name, total_bytes_game, total_bytes_game, 0.0, 0.0
                )
            else:
                self.file_progress.emit(game_name, 100, 100, 0.0, 0.0)

        self.file_finished.emit(game_name)

        self.active_workers = [(w, t) for w, t in self.active_workers if w != worker]
        logging.debug(
            f"Download Manager: Worker per '{game_name}' rimosso dagli attivi. Attivi ora: {len(self.active_workers)}"
        )

        self.start_new_downloads()

    def cancel_all(self):
        cancel_msg = "Download Manager: cancel_all chiamato. Annullamento download..."
        self.log.emit(cancel_msg)
        logging.info(cancel_msg)

        self.cancelled = True

        active_count = len(self.active_workers)
        logging.info(f"Annullamento richiesto per {active_count} download attivi...")

        workers_to_cancel = list(self.active_workers)
        for worker, thread in workers_to_cancel:
            if hasattr(worker, "cancel"):
                logging.debug(
                    f"Chiamata cancel() per worker '{getattr(worker, 'game_name', 'N/A')}'"
                )
                worker.cancel()

        queue_cleared_count = len(self.queue)
        self.queue.clear()
        logging.info(f"Coda interna svuotata ({queue_cleared_count} giochi rimossi).")

        if self.update_queue_callback:
            try:
                self.update_queue_callback()
            except Exception as e:
                logging.error(
                    f"Errore nel chiamare update_queue_callback durante cancel_all: {e}"
                )

        if not self.active_workers:
            logging.info(
                "Download Manager: Nessun worker attivo dopo richiesta di annullamento, emissione segnale finished."
            )
            self.finished.emit()
        else:
            logging.info(
                f"Download Manager: Annullamento richiesto, in attesa che i {len(self.active_workers)} worker attivi terminino."
            )

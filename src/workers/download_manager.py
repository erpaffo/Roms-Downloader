import logging  # Assicurati che logging sia importato
from PySide6.QtCore import QObject, Signal, QThread
# (Altri import, se presenti nel file originale)
# from src.workers.download_worker import DownloadWorker # L'import è già fatto nel metodo

class DownloadManager(QObject):
    log = Signal(str)
    overall_progress = Signal(int)  # percentuale globale
    finished = Signal()
    # Segnale aggiornato per passare più info alla UI principale
    file_progress = Signal(str, int, int, float, float)  # (game_name, downloaded, total, speed B/s, remaining_time s)
    # Segnale rimosso perché 'file_progress' ora contiene tutte le info
    # detailed_progress = Signal(str, float, float, float)
    file_finished = Signal(str)  # Segnale emesso quando un file finisce il download (con il nome del gioco)


    def __init__(self, queue, update_queue_callback, max_concurrent=2):
        super().__init__()
        # Fa una copia della coda per non modificare l'originale esterna
        self.queue = queue.copy()
        self.update_queue_callback = update_queue_callback
        self.max_concurrent = max_concurrent
        self.cancelled = False
        self.completed_downloads = [] # Lista per tenere traccia dei file locali completati

        # Calcola total_bytes sulla COPIA interna, gestendo casi senza 'size_bytes'
        self.total_bytes = sum(game.get('size_bytes', 0) for game in self.queue)
        # Crea downloaded_bytes gestendo giochi senza nome o duplicati (usa indice)
        self.downloaded_bytes = {
            game.get('name', f'unknown_game_{i}'): 0
            for i, game in enumerate(self.queue)
        }
        self.active_workers = []  # Lista delle tuple (worker, thread)

        # Log iniziale
        logging.info(f"DownloadManager creato con {len(self.queue)} giochi in coda. Max concurrent: {self.max_concurrent}. Total size: {self.total_bytes} bytes.")
        if not self.queue:
             logging.warning("DownloadManager creato con una coda VUOTA.")


    def process_queue(self):
        # Emetti il log tramite il segnale per la UI E tramite logging
        msg = "Download Manager: process_queue chiamato."
        self.log.emit(msg)
        logging.info(msg)

        if not self.queue:
             warning_msg = "Download Manager: La coda interna è vuota all'inizio di process_queue."
             self.log.emit(warning_msg)
             logging.warning(warning_msg)
             self.finished.emit() # Emetti finished se non c'è nulla da fare
             return
        self.start_new_downloads()

    def start_new_downloads(self):
        logging.debug(f"Download Manager: start_new_downloads chiamato. Coda={len(self.queue)}, Attivi={len(self.active_workers)}, Max={self.max_concurrent}")
        # Avvia nuovi download fino a raggiungere il limite e finché ci sono file in coda
        while not self.cancelled and self.queue and len(self.active_workers) < self.max_concurrent:
            game = self.queue.pop(0) # Prendi dalla COPIA interna
            game_name = game.get('name', 'Nome Sconosciuto')
            game_link = game.get('link', 'Link Sconosciuto')
            log_msg = f"Download Manager: Avvio worker per '{game_name}' (Link: {game_link})"
            self.log.emit(log_msg) # Emetti per UI
            logging.info(log_msg) # Log interno

            # Chiama il callback per aggiornare la UI della coda d'attesa se necessario
            if self.update_queue_callback:
                 try:
                     self.update_queue_callback()
                 except Exception as e:
                     logging.error(f"Errore nel chiamare update_queue_callback: {e}")


            thread = QThread()
            # Importa qui o all'inizio del file
            from src.workers.download_worker import DownloadWorker
            worker = DownloadWorker(game) # Passa il dizionario 'game' completo
            worker.moveToThread(thread)

            # Connessioni
            worker.finished.connect(lambda gn, lf, w=worker, t=thread: self.on_worker_finished(gn, lf, w, t))
            worker.progress_update.connect(self.on_worker_progress)
            # Collega il segnale log del worker al segnale log del manager
            # Questo permette ai log del worker di apparire nella UI principale
            worker.log.connect(self.log.emit)
            thread.started.connect(worker.run)

            thread.start()
            self.active_workers.append((worker, thread))
            logging.debug(f"Download Manager: Worker per '{game_name}' avviato e aggiunto agli attivi. Attivi ora: {len(self.active_workers)}")

        # Controlla se abbiamo finito DOPO aver tentato di avviare nuovi download
        # Emetti finished SOLO se non siamo stati cancellati
        if not self.cancelled and not self.queue and not self.active_workers:
            finish_msg = "Download Manager: Coda svuotata e nessun worker attivo. Tutti i download completati."
            self.log.emit(finish_msg)
            logging.info(finish_msg)
            self.finished.emit()
        elif not self.queue:
             # Log se la coda è vuota ma ci sono ancora worker attivi
             logging.info(f"Download Manager: Coda interna svuotata, ma ci sono ancora {len(self.active_workers)} worker attivi.")


    def on_worker_progress(self, game_name, downloaded, total, speed, remaining_time):
        # Aggiorna i byte scaricati per questo gioco (gestisci chiave mancante)
        if game_name in self.downloaded_bytes:
            self.downloaded_bytes[game_name] = downloaded
        else:
            # Se il nome non c'è (raro), logga un warning ma non bloccare
            logging.warning(f"Chiave '{game_name}' non trovata in downloaded_bytes durante progress update.")

        # Emetti il segnale file_progress con tutti i dati ricevuti dal worker
        self.file_progress.emit(game_name, downloaded, total, speed, remaining_time)

        # Calcola progresso globale basato sui byte totali della coda iniziale
        overall_downloaded = sum(self.downloaded_bytes.values())
        # Usa self.total_bytes calcolato in __init__
        if self.total_bytes > 0:
             overall_percent = int((overall_downloaded / self.total_bytes) * 100)
             overall_percent = min(overall_percent, 100) # Non superare 100%
        else:
             overall_percent = 100 if not self.active_workers and not self.queue else 0 # 100% se finito, 0% altrimenti
        self.overall_progress.emit(overall_percent)

        # Il segnale detailed_progress è stato rimosso, le info sono in file_progress


    def on_worker_finished(self, game_name, local_filename, worker, thread):
        finish_log_msg = f"Download Manager: Worker per '{game_name}' ha finito. File locale: '{local_filename if local_filename else 'Nessuno/Errore'}'"
        # Non emettere questo log tramite self.log perché lo emette già il worker
        logging.info(finish_log_msg)

        # Ferma e attendi il thread associato al worker
        thread.quit()
        if not thread.wait(1000): # Attendi max 1 secondo
             logging.warning(f"Thread per worker '{game_name}' non ha terminato entro 1 secondo.")

        # Aggiungi alla lista dei completati SE il file locale esiste
        if local_filename:
            self.completed_downloads.append(local_filename)
            # Emetti un ultimo segnale di progresso al 100% per questo file
            # Trova il totale per questo gioco (se possibile)
            total_bytes_game = next((g.get('size_bytes', 0) for g in self.queue + [w.game for w, t in self.active_workers] if g.get('name') == game_name), 0)
            if total_bytes_game > 0:
                 self.file_progress.emit(game_name, total_bytes_game, total_bytes_game, 0.0, 0.0)
            else: # Se non si conosce il totale, manda 100, 100
                 self.file_progress.emit(game_name, 100, 100, 0.0, 0.0)


        # Emetti il segnale file_finished con il nome del gioco
        # Questo segnale serve alla UI per sapere che *questo specifico* gioco ha finito
        self.file_finished.emit(game_name)

        # Rimuove il worker dalla lista degli attivi CERCANDO l'oggetto worker
        self.active_workers = [(w, t) for w, t in self.active_workers if w != worker]
        logging.debug(f"Download Manager: Worker per '{game_name}' rimosso dagli attivi. Attivi ora: {len(self.active_workers)}")

        # Controlla se avviare altri download o se abbiamo finito
        # Questa chiamata è cruciale per continuare la coda o emettere finished
        self.start_new_downloads()

    def cancel_all(self):
        # Emetti log per UI e per file
        cancel_msg = "Download Manager: cancel_all chiamato. Annullamento download..."
        self.log.emit(cancel_msg)
        logging.info(cancel_msg)

        self.cancelled = True # Imposta il flag

        active_count = len(self.active_workers)
        logging.info(f"Annullamento richiesto per {active_count} download attivi...")

        # Itera su una copia della lista perché potremmo modificarla indirettamente
        workers_to_cancel = list(self.active_workers)
        for worker, thread in workers_to_cancel:
             # Chiama il metodo cancel() del worker, se esiste
             if hasattr(worker, 'cancel'):
                 logging.debug(f"Chiamata cancel() per worker '{getattr(worker, 'game_name', 'N/A')}'")
                 worker.cancel()
             # Non provare a fermare il thread qui, lascia che il worker finisca (o venga interrotto)
             # e che on_worker_finished pulisca il thread.

        # Svuota la coda interna dei giochi rimanenti
        queue_cleared_count = len(self.queue)
        self.queue.clear()
        logging.info(f"Coda interna svuotata ({queue_cleared_count} giochi rimossi).")

        # Chiama il callback per aggiornare la UI della coda di attesa
        if self.update_queue_callback:
             try:
                 self.update_queue_callback()
             except Exception as e:
                 logging.error(f"Errore nel chiamare update_queue_callback durante cancel_all: {e}")

        # Emetti finished per segnalare alla MainWindow che il processo è terminato (anche se annullato)
        # MA SOLO SE non ci sono più worker attivi (potrebbero volerci un attimo a terminare dopo cancel)
        # La logica corretta è che on_worker_finished chiamerà start_new_downloads
        # che a sua volta emetterà finished quando active_workers sarà vuoto.
        # Quindi NON emettere finished qui direttamente.

        # Se non ci sono worker attivi già da ora (improbabile ma possibile), emetti finished.
        if not self.active_workers:
             logging.info("Download Manager: Nessun worker attivo dopo richiesta di annullamento, emissione segnale finished.")
             self.finished.emit()
        else:
             logging.info(f"Download Manager: Annullamento richiesto, in attesa che i {len(self.active_workers)} worker attivi terminino.")
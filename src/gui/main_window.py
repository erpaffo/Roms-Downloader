import os
import subprocess
import sys
import weakref
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QPlainTextEdit, QListWidget, QListWidgetItem, QProgressBar,
    QStackedWidget, QMessageBox, QSpinBox, QInputDialog
)
from PySide6.QtCore import Qt, QThread
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget
from src.gui.roms_page import RomsPage
from src.config import CONSOLES, DOWNLOADS_FOLDER, RETROARCH_NAME
from src.workers.scrape_worker import ScrapeWorker
from src.workers.download_manager import DownloadManager
from src.gui.download_queue_item import DownloadQueueItemWidget
from src.utils import extract_nations, format_rate, format_space
from src.gui.weight_item import WeightItem

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Roms Downloader")
        self.setGeometry(100, 100, 1200, 800)
        
        self.games_list = []      # Giochi ottenuti dallo scraping
        self.download_queue = []  # Giochi in attesa di download
        self.active_downloads_widgets = {}  # Mapping: nome gioco -> widget in download attivo
        self.roms_active_download_widgets = {}  # Per tracciare i widget attivi in ROMS (già collegati dalla pagina ROMS)
        self.roms_progress_stats = {}  # game_name -> (downloaded, total, speed)
        self.roms_peak_speeds = {}     # game_name -> peak (in byte/sec)
        self.last_speed ={}

        # Creazione dello stacked widget e delle pagine
        self.stacked_widget = QStackedWidget()
        self.download_manager_page = QWidget()  # pagina originale (se vuoi mantenerla)
        self.library_page = QWidget()             # pagina libreria esistente
        self.roms_page = RomsPage()               # nuova pagina ROMS per i download
        
        self.init_download_manager_page()
        self.init_library_page()
        
        # Aggiungi le pagine allo stacked widget
        self.stacked_widget.addWidget(self.download_manager_page)  # indice 0
        self.stacked_widget.addWidget(self.library_page)             # indice 1
        self.stacked_widget.addWidget(self.roms_page)                # indice 2
        
        # Creazione dell'header con i pulsanti di navigazione
        main_layout = QVBoxLayout()
        nav_layout = QHBoxLayout()
        self.btn_download_manager = QPushButton("Roms")
        self.btn_library = QPushButton("Library")
        self.btn_roms = QPushButton("Download Manager")
        
        self.btn_download_manager.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.btn_library.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.btn_roms.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        
        nav_layout.addWidget(self.btn_download_manager)
        nav_layout.addWidget(self.btn_library)
        nav_layout.addWidget(self.btn_roms)
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)
        
        # Carica inizialmente i giochi per la console "3ds"
        self.load_games("Atari 2600")
    
    def init_download_manager_page(self):
        layout = QVBoxLayout()
        
        # Controlli superiori: selezione console, ricerca e numero max di download concorrenti
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Seleziona Console:"))
        self.console_combo = QComboBox()
        self.console_combo.addItems(list(CONSOLES.keys()))
        self.console_combo.currentTextChanged.connect(self.console_changed)
        top_layout.addWidget(self.console_combo)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Cerca gioco...")
        self.search_bar.textChanged.connect(self.update_table)
        top_layout.addWidget(self.search_bar)
        
        self.btn_filter_nation = QPushButton("Filtra Nazione")
        self.btn_filter_nation.clicked.connect(self.filter_by_nation)
        top_layout.addWidget(self.btn_filter_nation)

        top_layout.addWidget(QLabel("Max download concorrenti:"))
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setMinimum(1)
        self.concurrent_spin.setMaximum(10)
        self.concurrent_spin.setValue(2)
        top_layout.addWidget(self.concurrent_spin)
        layout.addLayout(top_layout)
        
        # Tabella dei giochi disponibili (risultati dello scraping)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Nome Gioco", "Peso"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        layout.addWidget(self.table)
        
        # Lista di attesa: mostra i giochi in download che non sono ancora stati avviati
        waiting_layout = QVBoxLayout()
        waiting_layout.addWidget(QLabel("Coda Download (Attesa):"))
        self.waiting_queue_list = QListWidget()
        self.waiting_queue_list.itemDoubleClicked.connect(self.remove_waiting_item)
        waiting_layout.addWidget(self.waiting_queue_list)
        layout.addLayout(waiting_layout)
        
        # Sezione "Download Attivi": widget individuali per file in download
        active_layout = QVBoxLayout()
        active_layout.addWidget(QLabel("Download Attivi:"))
        self.active_downloads_container = QWidget()
        self.active_downloads_layout = QVBoxLayout()
        self.active_downloads_container.setLayout(self.active_downloads_layout)
        active_layout.addWidget(self.active_downloads_container)
        layout.addLayout(active_layout)
        
        # Progressione Globale
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progresso Globale:"))
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setValue(0)
        progress_layout.addWidget(self.overall_progress_bar)
        layout.addLayout(progress_layout)
        
        # Pulsanti Download e Log
        actions_layout = QHBoxLayout()
        self.btn_start_downloads = QPushButton("Avvia Download")
        self.btn_start_downloads.clicked.connect(self.start_downloads)
        actions_layout.addWidget(self.btn_start_downloads)
        self.btn_cancel_downloads = QPushButton("Annulla Download")
        self.btn_cancel_downloads.clicked.connect(self.cancel_downloads)
        actions_layout.addWidget(self.btn_cancel_downloads)
        layout.addLayout(actions_layout)
        
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(150)
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log_area)
        
        self.download_manager_page.setLayout(layout)
    
    def init_library_page(self):
        from PySide6.QtWidgets import QTreeWidget
        layout = QVBoxLayout()
        
        # Barra superiore con titolo e pulsante Refresh
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Library - Giochi Scaricati"))
        self.refresh_library_btn = QPushButton("Refresh")
        self.refresh_library_btn.clicked.connect(self.load_library)
        top_layout.addWidget(self.refresh_library_btn)
        layout.addLayout(top_layout)
        
        # Utilizziamo un QTreeWidget per raggruppare i giochi per console
        self.library_tree_widget = QTreeWidget()
        self.library_tree_widget.setHeaderLabels(["Nome Gioco", "Dimensione"])
        self.library_tree_widget.itemDoubleClicked.connect(self.launch_game_from_library)
        layout.addWidget(self.library_tree_widget)
        
        self.library_page.setLayout(layout)
    
    def log(self, message):
        logging.info(message)
        self.log_area.appendPlainText(message)
    
    def console_changed(self, console_name):
        self.log(f"Console cambiata: {console_name}")
        self.load_games(console_name)
    
    def load_games(self, console_name):
        self.log(f"Caricamento giochi per '{console_name}'...")
        self.table.setRowCount(0)
        self.scrape_thread = QThread()
        self.scrape_worker = ScrapeWorker(console_name)
        self.scrape_worker.moveToThread(self.scrape_thread)
        self.scrape_thread.started.connect(self.scrape_worker.run)
        self.scrape_worker.progress.connect(self.log)
        self.scrape_worker.finished.connect(self.on_games_loaded)
        self.scrape_worker.finished.connect(self.scrape_thread.quit)
        self.scrape_worker.finished.connect(self.scrape_worker.deleteLater)
        self.scrape_thread.finished.connect(self.scrape_thread.deleteLater)
        self.scrape_thread.start()
    
    def on_games_loaded(self, games):
        for game in games:
            game["nations"] = extract_nations(game["name"])
        self.games_list = games
        self.update_table()
        self.load_library()
    
    def update_table(self):
        search_text = self.search_bar.text().lower().strip()
        search_terms = search_text.split()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for game in self.games_list:
            name_lower = game['name'].lower()
            # Verifica che ogni termine di ricerca sia contenuto nel nome
            if any(term not in name_lower for term in search_terms):
                continue
            # Se è attivo un filtro per nazione, controlla che la nazione selezionata sia presente
            if hasattr(self, "selected_nation") and self.selected_nation:
                nations_lower = [n.lower() for n in game.get("nations", [])]
                if self.selected_nation not in nations_lower:
                    continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            item_name = QTableWidgetItem(game['name'])
            from src.gui.weight_item import WeightItem  # Assicurati che l'import sia qui o in cima al file
            item_size = WeightItem(game['size_str'])
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_size)
        self.table.setSortingEnabled(True)

    def filter_by_nation(self):
        # Le nazioni consentite sono definite in ALLOWED_NATIONS (importabile da src/utils)
        from src.utils import ALLOWED_NATIONS
        nations = sorted(list(ALLOWED_NATIONS))
        nation, ok = QInputDialog.getItem(self, "Filtra per Nazione", "Seleziona nazione:", nations, 0, False)
        if ok and nation:
            self.selected_nation = nation.lower()  # Salva la nazione selezionata in minuscolo
        else:
            self.selected_nation = ""
        self.update_table()

    def on_table_double_click(self, row, column):
        game_name = self.table.item(row, 0).text()
        
        game_already_downloaded = False
        for file_path in self.library_files:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            if base_name.lower() == game_name.lower():
                game_already_downloaded = True
                break
        if game_already_downloaded:
            QMessageBox.information(self, "Già scaricato", "Questo gioco è già presente nella tua libreria!")
            return

        # Assegna la variabile 'game' cercando nel games_list
        game = next((g for g in self.games_list if g['name'] == game_name), None)
        # Ora controlla se 'game' è stato trovato e non è già in coda
        if game and game not in self.download_queue:
            self.download_queue.append(game)
            self.update_waiting_queue_list()
            self.roms_page.add_to_queue(game['name'])
            self.log(f"Aggiunto in coda: {game['name']}")

    def update_waiting_queue_list(self):
        # Aggiorna la QListWidget che mostra i giochi in attesa di download
        self.waiting_queue_list.clear()
        for game in self.download_queue:
            item = QListWidgetItem(game['name'])
            item.setData(Qt.UserRole, game['name'])
            self.waiting_queue_list.addItem(item)
    
    def remove_waiting_item(self, item):
        # Rimuove manualmente un gioco dalla coda d'attesa
        game_name = item.data(Qt.UserRole)
        row = self.waiting_queue_list.row(item)
        self.waiting_queue_list.takeItem(row)
        self.download_queue = [g for g in self.download_queue if g['name'] != game_name]
        self.log(f"Rimosso dalla coda d'attesa: {game_name}")
    
    def update_file_progress(self, game_name, percent):
        """
        Aggiorna il widget del download attivo per il gioco 'game_name' con la percentuale di completamento.
        Questa funzione viene invocata dal segnale file_progress che emette (game_name, percent).
        """
        widget = self.active_downloads_widgets.get(game_name)
        if widget:
            widget.update_progress(percent)
        else:
            widget = DownloadQueueItemWidget({"name": game_name})
            widget.update_progress(percent)
            self.active_downloads_layout.addWidget(widget)
            self.active_downloads_widgets[game_name] = widget

    
    def update_detailed_progress(self, game_name, speed, remaining_time, space_remaining):
        widget = self.active_downloads_widgets.get(game_name)
        if widget and hasattr(widget, "set_detailed_info"):
            widget.set_detailed_info(format_rate(speed), f"{remaining_time:.1f} s", format_space(space_remaining))
    
    def remove_finished_file(self, finished_game_name):
        # Rimuove il gioco finito dalla coda d'attesa
        self.download_queue = [g for g in self.download_queue if g['name'] != finished_game_name]
        self.update_waiting_queue_list()
    
    def remove_active_download_widget(self, game_name):
        widget = self.active_downloads_widgets.get(game_name)
        if widget:
            widget.setParent(None)
            widget.deleteLater()
            del self.active_downloads_widgets[game_name]
    
    def start_downloads(self):
        if not self.download_queue:
            self.log("Nessun download in coda.")
            return

        self.log("Avvio coda download...")
        self.download_manager_thread = QThread()
        max_concurrent = self.concurrent_spin.value()
        self.download_manager_worker = DownloadManager(
            self.download_queue,
            lambda: self.update_waiting_queue_list(),
            max_concurrent
        )

        # Connessioni fondamentali (verifica bene questa connessione):
        self.download_manager_worker.file_progress.connect(self.update_roms_active_download)
        self.download_manager_worker.file_finished.connect(self.on_download_finished_roms)

        self.download_manager_worker.moveToThread(self.download_manager_thread)
        self.download_manager_worker.log.connect(self.log)
        self.download_manager_thread.started.connect(self.download_manager_worker.process_queue)
        self.download_manager_worker.finished.connect(self.download_manager_thread.quit)
        self.download_manager_worker.finished.connect(self.download_manager_worker.deleteLater)
        self.download_manager_thread.finished.connect(self.download_manager_thread.deleteLater)
        self.download_manager_thread.start()

    def cancel_downloads(self):
        if self.download_manager_worker:
            self.download_manager_worker.cancel_all()
            self.log("Download annullati.")
    
    def load_library(self):
        """
        Scansiona ricorsivamente la cartella DOWNLOADS_FOLDER per trovare i giochi,
        li raggruppa per console e li visualizza nel QTreeWidget.
        """
        self.library_tree_widget.clear()
        self.library_files = []
        files_by_console = {}
        for root, dirs, files in os.walk(DOWNLOADS_FOLDER):
            for file in files:
                if file.lower().endswith((".3ds", ".nds", ".gba", ".gb")):
                    full_path = os.path.join(root, file)
                    self.library_files.append(full_path)
                    # Determina la console: si assume la struttura DOWNLOADS_FOLDER/<console>/<file>
                    norm_path = os.path.normpath(full_path)
                    parts = norm_path.split(os.sep)
                    console = "Unknown"
                    try:
                        download_folder = os.path.basename(DOWNLOADS_FOLDER)
                        index = parts.index(download_folder)
                        if len(parts) > index + 1:
                            console = parts[index + 1]
                    except ValueError:
                        console = "Unknown"
                    if console not in files_by_console:
                        files_by_console[console] = []
                    # Ottieni la dimensione del file e formattala (usando format_space)
                    size = os.path.getsize(full_path)
                    files_by_console[console].append((file, size, full_path))
        
        from PySide6.QtWidgets import QTreeWidgetItem
        for console, games in files_by_console.items():
            top_item = QTreeWidgetItem([console])
            for game_name, size, full_path in games:
                size_str = format_space(size)
                child_item = QTreeWidgetItem([game_name, size_str])
                child_item.setData(0, Qt.UserRole, full_path)
                top_item.addChild(child_item)
            self.library_tree_widget.addTopLevelItem(top_item)

    
    def launch_game_from_library(self, item, column):
        """
        Se l'item selezionato è un file (foglia del QTreeWidget), lancia RetroArch con la ROM.
        """
        # Se l'item ha dei figli, si tratta di un gruppo, quindi non fare nulla.
        if item.childCount() > 0:
            return
        file_path = item.data(0, Qt.UserRole)
        try:
            subprocess.Popen([RETROARCH_NAME, file_path])
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile avviare RetroArch: {e}")

    def update_roms_current_download(self, game_name, downloaded, total, speed, remaining_time):
        # Calcola la percentuale di avanzamento
        percent = int(downloaded / total * 100)
        
        # Formatta la velocità corrente (usando la funzione format_rate)
        speed_str = format_rate(speed)
        
        # Gestione del picco di velocità
        if not hasattr(self, 'peak_speeds'):
            self.peak_speeds = {}
        if game_name not in self.peak_speeds or speed > self.peak_speeds[game_name]:
            self.peak_speeds[game_name] = speed
        peak_speed_str = format_rate(self.peak_speeds[game_name])
        
        # Aggiorna la sezione ROMS con il download corrente
        self.roms_page.update_current_download(game_name, percent, speed_str, peak_speed_str)

    def on_download_finished_roms(self, game_name, local_file):
        # Rimuove il gioco dalla coda ROMS
        self.roms_page.remove_from_queue(game_name)
        
        # Aggiunge il download completato alla lista dei completati
        self.roms_page.add_completed_download(game_name)
        
        # (Opzionale) Reset dei dati del download corrente se non ci sono altri download attivi
        self.roms_page.update_current_download("Nessun download in corso", 0, "0 KB/s", "0 KB/s")

    def update_roms_progress(self, game_name, percent):
        """
        Aggiorna il download corrente nella pagina ROMS usando la percentuale,
        che proviene dal segnale file_progress (due parametri: game_name e percent).
        """
        self.current_game = game_name
        self.current_percent = percent
        # Se non abbiamo ancora dati di velocità, impostiamo valori di default
        current_speed = getattr(self, 'current_speed', 0)
        peak_speed = getattr(self, 'peak_speed', 0)
        self.roms_page.update_current_download(game_name, percent, format_rate(current_speed), format_rate(peak_speed))

    def update_roms_active_download(self, game_name, downloaded, total, speed, remaining_time):
        percent = int(downloaded / total * 100) if total else 0

        # Crea widget se non esiste già
        if game_name not in self.roms_active_download_widgets:
            widget = self.roms_page.add_active_download(game_name)
            self.roms_active_download_widgets[game_name] = widget

        # Aggiorna barra di progresso
        self.roms_page.update_active_download(game_name, percent)

        # Velocità in MB/s (convertita da byte/s)
        speed_mb = speed / (1024 * 1024)

        # Aggiorna il picco di velocità
        peak_speed = self.roms_peak_speeds.get(game_name, 0)
        if speed_mb > peak_speed:
            self.roms_peak_speeds[game_name] = speed_mb
            peak_speed = speed_mb

        # Aggiorna statistiche nel widget
        self.roms_page.update_active_stats(game_name, speed_mb, peak_speed)

        # Aggiorna statistiche globali
        self.roms_progress_stats[game_name] = (downloaded, total, speed_mb)

        # Ricalcola statistiche globali
        total_active = sum(t for _, t, _ in self.roms_progress_stats.values())
        downloaded_active = sum(d for d, _, _ in self.roms_progress_stats.values())
        global_speed = sum(s for _, _, s in self.roms_progress_stats.values())
        global_peak = max(self.roms_peak_speeds.values(), default=0)

        self.roms_page.update_global_progress(
            downloaded_active,
            total_active,
            global_speed,
            global_peak
        )

    def on_download_finished_roms(self, game_name, *args):
        if game_name in self.roms_active_download_widgets:
            self.roms_page.remove_active_download(game_name)
            self.roms_active_download_widgets.pop(game_name)

        if game_name in self.roms_progress_stats:
            del self.roms_progress_stats[game_name]

        if game_name in self.roms_peak_speeds:
            del self.roms_peak_speeds[game_name]

        if game_name in self.last_speed:
            del self.last_speed[game_name]

        self.roms_page.remove_from_queue(game_name)
        self.roms_page.add_completed_download(game_name)

        # Ricalcola statistiche globali dopo aver rimosso il download completato
        total_active = sum(t for _, t, _ in self.roms_progress_stats.values())
        downloaded_active = sum(d for d, _, _ in self.roms_progress_stats.values())
        global_speed = sum(s for _, _, s in self.roms_progress_stats.values())
        global_peak = max(self.roms_peak_speeds.values(), default=0)

        self.roms_page.update_global_progress(
            downloaded_active,
            total_active,
            global_speed,
            global_peak
        )

    def update_roms_detailed(self, game_name, speed, remaining_time, space_remaining):
        """
        Aggiorna i dati dettagliati (velocità e picco) del download corrente
        usando il segnale detailed_progress (quattro parametri: game_name, speed, remaining_time, space_remaining).
        """
        self.current_game = game_name
        self.current_speed = speed
        if not hasattr(self, 'peak_speed') or speed > self.peak_speed:
            self.peak_speed = speed
        # Aggiorna la GUI usando la percentuale salvata (se esistente) e i nuovi dati di velocità
        percent = getattr(self, 'current_percent', 0)
        self.roms_page.update_current_download(game_name, percent, format_rate(speed), format_rate(self.peak_speed))

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


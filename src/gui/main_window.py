import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QHeaderView,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QTreeWidgetItem,
    QPlainTextEdit, QTreeWidget, QListWidget, QListWidgetItem, QProgressBar,
    QStackedWidget, QMessageBox, QSpinBox, QInputDialog, QSystemTrayIcon, QMenuBar, QMenu
)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QFileDialog
from src.gui.emulator_settings_dialog import EmulatorSettingsDialog
from src.gui.roms_page import RomsPage
from src.config import CONSOLES, CORE_EXT, DEFAULT_CORES, EMULATOR_CONFIG_FOLDER, USER_DOWNLOADS_FOLDER, set_user_download_folder, set_max_concurrent_downloads, settings, DEFAULT_DOWNLOADS_FOLDER,  MAX_CONCURRENT_DOWNLOADS
from src.workers.scrape_worker import ScrapeWorker
from src.workers.download_manager import DownloadManager
from src.gui.download_queue_item import DownloadQueueItemWidget
from src.utils import extract_nations, format_rate, format_space, ALLOWED_NATIONS, update_emulator_config
from src.gui.settings_dialog import SettingsDialog
from src.gui.library_page import LibraryPage
from src.gui.weight_item import WeightItem
from src.gui.hotkeys_dialog import HotkeysDialog
from src.default_keybindings import DEFAULT_KEYBINDINGS
from src.key_bindings import KeyBindings

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
        self.library_page = LibraryPage()            # pagina libreria esistente
        self.roms_page = RomsPage()               # nuova pagina ROMS per i download
        
        self.init_download_manager_page()
        
        # Aggiungi le pagine allo stacked widget
        self.stacked_widget.addWidget(self.download_manager_page)  # indice 0
        self.stacked_widget.addWidget(self.library_page)             # indice 1
        self.stacked_widget.addWidget(self.roms_page)                # indice 2
        
        self.key_bindings = KeyBindings(DEFAULT_KEYBINDINGS)

        # Creazione barra menu con  impostazioni
        menu_bar = QMenuBar(self)
        settings_menu = QMenu("Settings", self)
        menu_bar.addMenu(settings_menu)

        # Azione per le impostazioni
        settings_action = QAction("Opzioni", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(settings_action)

        hotkeys_action = QAction("Configura Hotkeys", self)
        hotkeys_action.triggered.connect(self.open_hotkeys_dialog)
        settings_menu.addAction(hotkeys_action)

        emulator_menu = QMenu("Emulator", self)
        menu_bar.addMenu(emulator_menu)
        # Per ogni core in DEFAULT_CORES, aggiungi un'azione per aprire il dialogo di impostazioni
        for core_name, core_file in DEFAULT_CORES.items():
            action = QAction(core_name, self)
            action.triggered.connect(lambda checked, core=core_name, file=core_file: self.open_emulator_settings(core + CORE_EXT, file))
            emulator_menu.addAction(action)

        main_layout = QVBoxLayout()
        main_layout.setMenuBar(menu_bar)

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
        
        self.btn_start_downloads.setEnabled(True)
        self.btn_cancel_downloads.setEnabled(False)

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
        
        layout.addLayout(top_layout)
        
        # Tabella dei giochi disponibili (risultati dello scraping)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Nome Gioco", "Peso"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Adatta automaticamente "Nome Gioco"
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
    
    def select_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella download", USER_DOWNLOADS_FOLDER)
        if folder:
            set_user_download_folder(folder)
            self.log(f"Cartella download impostata su: {folder}")
            self.library_page.load_library()

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
        self.library_page.load_library()
    
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
            item_size = WeightItem(game['size_str'])
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_size)
        self.table.setSortingEnabled(True)

    def filter_by_nation(self):
        # Le nazioni consentite sono definite in ALLOWED_NATIONS (importabile da src/utils)
        nations = sorted(list(ALLOWED_NATIONS))
        nation, ok = QInputDialog.getItem(self, "Filtra per Nazione", "Seleziona nazione:", nations, 0, False)
        if ok and nation:
            self.selected_nation = nation.lower()  # Salva la nazione selezionata in minuscolo
        else:
            self.selected_nation = ""
        self.update_table()

    def on_table_double_click(self, row, column):
        if not self.btn_start_downloads.isEnabled():  # Download in corso, evita modifiche
            QMessageBox.warning(self, "Attenzione", "Attendere il termine dei download prima di aggiungere altri giochi.")
            return
        game_name = self.table.item(row, 0).text()
        
        game_already_downloaded = False
        for file_path in self.library_page.library_files:
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
        
        self.btn_start_downloads.setEnabled(False)   
        self.btn_cancel_downloads.setEnabled(True)

        # Svuota la lista visiva della coda
        self.waiting_queue_list.clear()
        
        self.log("Avvio coda download...")
        self.download_manager_thread = QThread()
        # Leggi il valore aggiornato dalle impostazioni
        max_concurrent = MAX_CONCURRENT_DOWNLOADS

        # Crea il DownloadManager con la coda attuale e il numero massimo di download concorrenti
        self.download_manager_worker = DownloadManager(
            self.download_queue,
            lambda: self.update_waiting_queue_list(),
            max_concurrent
        )

        self.download_manager_worker.file_progress.connect(self.update_roms_active_download)
        self.download_manager_worker.file_finished.connect(self.on_download_finished_roms)

        self.download_manager_worker.moveToThread(self.download_manager_thread)
        self.download_manager_worker.log.connect(self.log)
        self.download_manager_thread.started.connect(self.download_manager_worker.process_queue)        
        self.download_manager_worker.finished.connect(self.on_all_downloads_finished)
        self.download_manager_worker.finished.connect(self.download_manager_thread.quit)
        self.download_manager_worker.finished.connect(self.download_manager_worker.deleteLater)
        self.download_manager_thread.finished.connect(self.download_manager_thread.deleteLater)
        self.download_manager_thread.start()

        # Svuota anche la lista interna della coda
        self.download_queue.clear()

    def cancel_downloads(self):
        if self.download_manager_worker:
            self.download_manager_worker.cancel_all()
            self.log("Download annullati.")
            self.btn_start_downloads.setEnabled(True)    # Riabilita pulsante Avvia Download
            self.btn_cancel_downloads.setEnabled(False)  # Disabilita pulsante Annulla Download


    def on_all_downloads_finished(self):
        self.log("Tutti i download completati.")
        self.btn_start_downloads.setEnabled(True)    # Riabilita pulsante Avvia Download
        self.btn_cancel_downloads.setEnabled(False)  # Disabilita pulsante Annulla Download

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

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Se l'utente ha premuto OK, aggiorna le impostazioni
            values = dialog.get_values()
            set_user_download_folder(values["download_folder"])
            set_max_concurrent_downloads(values["max_dl"])
            self.log(f"Impostazioni aggiornate: {values}")
            # Aggiorna la libreria con il nuovo percorso (se necessario)
            self.library_page.load_library()


    def open_emulator_settings(self, core_name, core_file):
        """
        Apre il dialogo per modificare le impostazioni del core specifico.
        Il file di configurazione è individuato in EMULATOR_CONFIG_FOLDER.
        Se core_file non termina con ".cfg", l'estensione viene aggiunta.
        """
        if not core_file.endswith(".cfg"):
            config_filename = core_file + CORE_EXT + ".cfg"
        else:
            config_filename = core_file
        config_path = os.path.join(EMULATOR_CONFIG_FOLDER, config_filename)
        dialog = EmulatorSettingsDialog(core_name, config_path, self)
        if dialog.exec():
            self.log(f"Impostazioni per {core_name} aggiornate. Config file: {dialog.get_config_path()}")

    def open_hotkeys_dialog(self):
        dialog = HotkeysDialog(self.key_bindings, self)
        if dialog.exec():
            # Dopo il salvataggio, aggiorna il file di configurazione relativo al core corrente.
            # Supponiamo di avere il nome della console corrente, ad esempio "Nintendo DS".
            console = "Nintendo DS"
            # Otteniamo il nome base del core dal dizionario DEFAULT_CORES (definito in config.py)
            from src.config import DEFAULT_CORES, EMULATOR_CONFIG_FOLDER, CORE_EXT
            core_base = DEFAULT_CORES.get(console)
            if core_base:
                config_filename = core_base + ".cfg" 
                config_path = os.path.join(EMULATOR_CONFIG_FOLDER, config_filename)
                # Aggiorniamo il file di configurazione con i nuovi binding
                update_emulator_config(config_path, self.key_bindings.bindings)
                self.log("Hotkeys aggiornate e file di configurazione aggiornato: " + config_filename)
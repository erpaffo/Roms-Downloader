import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, QHeaderView,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QTreeWidgetItem,
    QPlainTextEdit, QTreeWidget, QListWidget, QListWidgetItem, QProgressBar, QSizePolicy, QSplitter,
    QStackedWidget, QMessageBox, QSpinBox, QInputDialog, QSystemTrayIcon, QMenuBar, QMenu, QApplication
)
from PySide6.QtCore import Qt, QThread, QSize
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QFileDialog
from src.gui.emulator_settings_dialog import EmulatorSettingsDialog
from src.gui.roms_page import RomsPage
from src.config import (
    CONSOLES, CORE_EXT, DEFAULT_CORES, EMULATOR_CONFIG_FOLDER, BASE_DIR,
    USER_DOWNLOADS_FOLDER, set_user_download_folder, set_max_concurrent_downloads,
    settings, DEFAULT_DOWNLOADS_FOLDER, MAX_CONCURRENT_DOWNLOADS
)
from src.workers.scrape_worker import ScrapeWorker
from src.workers.download_manager import DownloadManager
from src.gui.download_queue_item import DownloadQueueItemWidget
from src.utils import extract_nations, ALLOWED_NATIONS, update_emulator_config, convert_binding 
from src.gui.settings_dialog import SettingsDialog
from src.gui.library_page import LibraryPage
from src.gui.weight_item import WeightItem
from src.gui.hotkeys_dialog import HotkeysDialog
from src.default_keybindings import DEFAULT_KEYBINDINGS
from src.key_bindings import KeyBindings
from src.gui.controls_page import ControlsPage

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Roms Downloader")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(800, 600)

        try:
            qss_path = os.path.join(BASE_DIR, "gui/styles/style.qss")
            if not os.path.exists(qss_path):
                 qss_path = os.path.join(BASE_DIR, "style.qss") 
            if not os.path.exists(qss_path):
                 qss_path = os.path.join(BASE_DIR, "../gui/style.qss")

            if os.path.exists(qss_path):
                with open(qss_path, "r") as f:
                    style_sheet = f.read()
                    app = QApplication.instance()
                    if app:
                        app.setStyleSheet(style_sheet)
                    else:
                        print("WARNING: QApplication instance not found when applying stylesheet.")
            else:
                print(f"WARNING: Stylesheet file not found at expected paths like '{os.path.join(BASE_DIR, 'gui', 'styles', 'style.qss')}' or similar.")
        except Exception as e:
            print(f"Error loading stylesheet: {e}")

        # Inizializza attributi
        self.games_list = []
        self.download_queue = []
        self.active_downloads_widgets = {}
        self.roms_active_download_widgets = {}
        self.roms_progress_stats = {}
        self.roms_peak_speeds = {}
        self.last_speed = {}
        self.key_bindings = KeyBindings(DEFAULT_KEYBINDINGS)
        self.download_manager_worker = None # Inizializza worker a None
        self.download_manager_thread = None # Inizializza thread a None

        # Layout Principale Orizzontale (Sidebar + Contenuto)
        main_layout = QHBoxLayout(self) # Applica direttamente alla finestra
        main_layout.setContentsMargins(0, 0, 0, 0) # Rimuovi margini esterni
        main_layout.setSpacing(0) # Rimuovi spaziatura tra sidebar e contenuto

        # --- Navigazione Sidebar ---
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList") # Per stile QSS
        self.nav_list.setFixedWidth(180)
        self.nav_list.addItem("Cerca ROMs")
        self.nav_list.addItem("Libreria")
        self.nav_list.addItem("Gestione Download")
        self.nav_list.addItem("Controlli Console")
        # TODO AGGIUNGERE ICONE (self.nav_list.item(0).setIcon(QIcon("path/to/search_icon.png")))
        self.nav_list.currentRowChanged.connect(self.change_page)
        main_layout.addWidget(self.nav_list)

        # Contenitore per MenuBar e StackedWidget
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # --- Menu Bar ---
        menu_bar = self._create_menu_bar() # Crea la menubar con un metodo helper
        content_layout.setMenuBar(menu_bar)

        # --- Stacked Widget e Pagine ---
        self.stacked_widget = QStackedWidget()
        self.download_manager_page = QWidget() # Pagina Cerca ROMs
        self.library_page = LibraryPage()         # Pagina Libreria
        self.roms_page = RomsPage()               # Pagina Gestione Download
        self.controls_page = ControlsPage(config_folder=EMULATOR_CONFIG_FOLDER) # Pagina Controlli

        self.init_download_manager_page() # Inizializza layout pagina download

        self.stacked_widget.addWidget(self.download_manager_page)  # Indice 0
        self.stacked_widget.addWidget(self.library_page)             # Indice 1
        self.stacked_widget.addWidget(self.roms_page)                # Indice 2
        self.stacked_widget.addWidget(self.controls_page)            # Indice 3

        content_layout.addWidget(self.stacked_widget)

        main_layout.addWidget(content_container) # Aggiungi container a destra

        # Imposta pagina iniziale
        self.nav_list.setCurrentRow(0)

        # Carica giochi iniziali (assicurandosi che console_combo esista)
        initial_console = list(CONSOLES.keys())[0] if CONSOLES else "Atari 2600" # Fallback
        if hasattr(self, 'console_combo'):
            initial_console = self.console_combo.currentText()
        self.load_games(initial_console)

    def _create_menu_bar(self):
        """Crea e restituisce la barra dei menu."""
        menu_bar = QMenuBar()
        # Menu Impostazioni
        settings_menu = QMenu("Impostazioni", self)
        menu_bar.addMenu(settings_menu)
        settings_action = QAction("Opzioni Generali", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(settings_action)
        hotkeys_action = QAction("Configura Tasti Rapidi", self)
        hotkeys_action.triggered.connect(self.open_hotkeys_dialog)
        settings_menu.addAction(hotkeys_action)

        # Menu Emulatore
        emulator_menu = QMenu("Impostazioni Emulatore", self)
        menu_bar.addMenu(emulator_menu)
        for core_name, core_file_base in DEFAULT_CORES.items():
            # Assicurati che core_file_base sia solo il nome base (es. 'stella2023_libretro')
            action = QAction(core_name, self)
            # Passa il nome visualizzato (core_name) e il nome base del file (core_file_base)
            action.triggered.connect(
                lambda checked, name=core_name, file_base=core_file_base: self.open_emulator_settings(name, file_base)
            )
            emulator_menu.addAction(action)
        return menu_bar

    def change_page(self, index):
        """Cambia la pagina visualizzata nello QStackedWidget."""
        self.stacked_widget.setCurrentIndex(index)
        if index == 1: # Se si va alla pagina Libreria
             self.library_page.refresh_library() # Aggiorna la libreria

    def init_download_manager_page(self):
        """Inizializza il layout della pagina 'Cerca ROMs'."""
        page_layout = QVBoxLayout(self.download_manager_page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(10)

        # 1. Controlli Superiori
        page_layout.addLayout(self._create_top_controls())

        # 2. Splitter Principale (Tabella sopra, Download/Log sotto)
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)

        # 2a. Tabella Giochi
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0,0,0,0)
        self.table = self._create_games_table()
        table_layout.addWidget(self.table)
        main_splitter.addWidget(table_container)

        # 2b. Sezioni Inferiori (Download + Log)
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0,0,0,0)
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.setChildrenCollapsible(False)

        # Contenitore Sezioni Download
        download_sections_widget = QWidget()
        download_sections_layout = self._create_download_sections()
        download_sections_widget.setLayout(download_sections_layout)
        bottom_splitter.addWidget(download_sections_widget)

        # Contenitore Log
        log_widget = QWidget()
        log_layout = self._create_log_area()
        log_widget.setLayout(log_layout)
        bottom_splitter.addWidget(log_widget)

        # Imposta dimensioni iniziali splitter (adattive)
        # Usa setStretchFactor per una divisione proporzionale
        bottom_splitter.setStretchFactor(0, 6) # 60% a download
        bottom_splitter.setStretchFactor(1, 4) # 40% a log
        # bottom_splitter.setSizes([600, 400]) # Alternativa con dimensioni fisse iniziali

        bottom_layout.addWidget(bottom_splitter)
        main_splitter.addWidget(bottom_container)

        # Imposta dimensioni iniziali splitter principale
        main_splitter.setStretchFactor(0, 5) # 50% a tabella
        main_splitter.setStretchFactor(1, 5) # 50% a sotto
        # main_splitter.setSizes([400, 400]) # Alternativa con dimensioni fisse iniziali

        page_layout.addWidget(main_splitter)

        # Stato iniziale bottoni (assicurati che esistano prima di accedervi)
        if hasattr(self, 'btn_start_downloads'):
            self.btn_start_downloads.setEnabled(True)
        if hasattr(self, 'btn_cancel_downloads'):
            self.btn_cancel_downloads.setEnabled(False)

    def _create_top_controls(self):
        """Crea il layout per i controlli superiori (console, cerca, filtra)."""
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Seleziona Console:"))
        self.console_combo = QComboBox()
        self.console_combo.addItems(list(CONSOLES.keys()))
        self.console_combo.currentTextChanged.connect(self.console_changed)
        self.console_combo.setMinimumWidth(150)
        self.console_combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.console_combo)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Cerca gioco...")
        self.search_bar.textChanged.connect(self.update_table)
        self.search_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.search_bar)

        self.btn_filter_nation = QPushButton("Filtra Nazione")
        self.btn_filter_nation.clicked.connect(self.filter_by_nation)
        layout.addWidget(self.btn_filter_nation)
        layout.addStretch()
        return layout

    def _create_games_table(self):
        """Crea e restituisce la tabella dei giochi."""
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Nome Gioco", "Peso"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.cellDoubleClicked.connect(self.on_table_double_click)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True) # Abilita ordinamento colonne
        return table

    def _create_download_sections(self):
        """Crea il layout per le sezioni relative ai download."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0) # Margini laterali per spaziatura dallo splitter
        layout.setSpacing(5)

        # Coda Attesa
        layout.addWidget(QLabel("Coda Download (Attesa):"))
        self.waiting_queue_list = QListWidget()
        self.waiting_queue_list.setMaximumHeight(120) # Altezza massima per evitare che cresca troppo
        self.waiting_queue_list.itemDoubleClicked.connect(self.remove_waiting_item)
        layout.addWidget(self.waiting_queue_list)

        # Download Attivi
        layout.addWidget(QLabel("Download Attivi:"))
        self.active_downloads_container = QWidget()
        self.active_downloads_layout = QVBoxLayout()
        self.active_downloads_layout.setContentsMargins(0,0,0,0)
        self.active_downloads_container.setLayout(self.active_downloads_layout)
        # Aggiungi stretch per comprimere i widget attivi verso l'alto se ce ne sono pochi
        self.active_downloads_layout.addStretch()
        layout.addWidget(self.active_downloads_container, 1) # Dagli stretch factor per occupare spazio

        # Progresso Globale
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progresso Globale:"))
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setValue(0)
        progress_layout.addWidget(self.overall_progress_bar)
        layout.addLayout(progress_layout)

        # Pulsanti Azioni
        actions_layout = QHBoxLayout()
        self.btn_start_downloads = QPushButton("Avvia Download Coda")
        self.btn_start_downloads.clicked.connect(self.start_downloads)
        actions_layout.addWidget(self.btn_start_downloads)
        self.btn_cancel_downloads = QPushButton("Annulla Tutti")
        self.btn_cancel_downloads.clicked.connect(self.cancel_downloads)
        actions_layout.addWidget(self.btn_cancel_downloads)
        layout.addLayout(actions_layout)
        # layout.addStretch() # Rimosso lo stretch finale per non comprimere i bottoni
        return layout

    def _create_log_area(self):
        """Crea il layout per l'area di log."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0) # Margini laterali
        layout.addWidget(QLabel("Log:"))
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        return layout

    # --- Metodi Funzionali (per lo più invariati, ma verifica i riferimenti ai widget) ---

    def select_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella download", USER_DOWNLOADS_FOLDER)
        if folder:
            set_user_download_folder(folder)
            self.log(f"Cartella download impostata su: {folder}")
            if hasattr(self, 'library_page'): # Verifica se library_page esiste
                self.library_page.load_library()

    def log(self, message):
        logging.info(message)
        if hasattr(self, 'log_area'): # Verifica se log_area esiste
            self.log_area.appendPlainText(message)

    def console_changed(self, console_name):
        self.log(f"Console cambiata: {console_name}")
        self.load_games(console_name)

    def load_games(self, console_name):
        self.log(f"Caricamento giochi per '{console_name}'...")
        if not hasattr(self, 'table'): # Se la tabella non è ancora pronta, esci
             print("WARN: Table widget not ready for loading games.")
             return
        self.table.setRowCount(0) # Svuota tabella
        self.table.setSortingEnabled(False) # Disabilita sort durante caricamento

        self.scrape_thread = QThread()
        self.scrape_worker = ScrapeWorker(console_name)
        self.scrape_worker.moveToThread(self.scrape_thread)

        # Connessioni segnali/slot
        self.scrape_thread.started.connect(self.scrape_worker.run)
        self.scrape_worker.progress.connect(self.log)
        self.scrape_worker.finished.connect(self.on_games_loaded)
        # Pulizia al termine
        self.scrape_worker.finished.connect(self.scrape_thread.quit)
        self.scrape_worker.finished.connect(self.scrape_worker.deleteLater)
        self.scrape_thread.finished.connect(self.scrape_thread.deleteLater)

        self.scrape_thread.start()

    def on_games_loaded(self, games):
        self.log(f"Caricati {len(games)} giochi.")
        for game in games:
            # Assicurati che 'nations' esista, default a lista vuota
            game["nations"] = extract_nations(game.get("name", ""))
        self.games_list = games
        self.update_table() # Aggiorna la tabella con i nuovi giochi
        # Aggiorna libreria (se la pagina esiste)
        if hasattr(self, 'library_page'):
            self.library_page.load_library()

    def update_table(self):
        if not hasattr(self, 'table'):
             print("WARN: Table widget not ready for updating.")
             return
        search_text = self.search_bar.text().lower().strip() if hasattr(self, 'search_bar') else ""
        search_terms = search_text.split()

        self.table.setSortingEnabled(False) # Disabilita sort durante aggiornamento
        self.table.setRowCount(0) # Svuota tabella

        selected_nation = getattr(self, "selected_nation", "").lower() # Usa getattr per sicurezza

        for game in self.games_list:
            name_lower = game.get('name', '').lower()
            # Filtro ricerca
            if search_terms and any(term not in name_lower for term in search_terms):
                continue
            # Filtro nazione
            if selected_nation:
                nations_lower = [n.lower() for n in game.get("nations", [])]
                if selected_nation not in nations_lower:
                    continue

            # Aggiungi riga alla tabella
            row = self.table.rowCount()
            self.table.insertRow(row)
            item_name = QTableWidgetItem(game.get('name', 'N/A'))
            item_size = WeightItem(game.get('size_str', '0 B')) # Usa WeightItem
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_size)

        self.table.setSortingEnabled(True) # Riabilita sort
        self.log(f"Tabella aggiornata, {self.table.rowCount()} giochi visualizzati.")


    def filter_by_nation(self):
        nations = sorted(list(ALLOWED_NATIONS))
        nation, ok = QInputDialog.getItem(self, "Filtra per Nazione", "Seleziona nazione (vuoto per rimuovere filtro):", [""] + nations, 0, False)
        if ok:
            self.selected_nation = nation # Salva nazione selezionata (anche vuota)
            self.log(f"Filtro nazione impostato su: '{nation}'" if nation else "Filtro nazione rimosso.")
            self.update_table() # Aggiorna tabella con il nuovo filtro


    def on_table_double_click(self, row, column):
        # Verifica se un download è in corso (controllando lo stato dei bottoni)
        start_enabled = self.btn_start_downloads.isEnabled() if hasattr(self, 'btn_start_downloads') else True
        if not start_enabled:
            QMessageBox.warning(self, "Attenzione", "Attendere il termine dei download prima di aggiungere altri giochi.")
            return

        if not hasattr(self, 'table'): return # Sicurezza
        game_name_item = self.table.item(row, 0)
        if not game_name_item: return # Sicurezza
        game_name = game_name_item.text()

        # Controlla se già scaricato (nella libreria)
        if hasattr(self, 'library_page') and hasattr(self.library_page, 'library_files'):
            game_already_downloaded = False
            for file_path in self.library_page.library_files:
                try:
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    if base_name.lower() == game_name.lower():
                        game_already_downloaded = True
                        break
                except Exception: continue # Ignora errori nel path
            if game_already_downloaded:
                QMessageBox.information(self, "Già scaricato", f"'{game_name}' è già presente nella tua libreria.")
                return

        # Controlla se già in coda di attesa
        if any(g['name'] == game_name for g in self.download_queue):
             QMessageBox.information(self, "Già in coda", f"'{game_name}' è già nella coda di download.")
             return

        # Trova il gioco corrispondente nella lista completa
        game = next((g for g in self.games_list if g.get('name') == game_name), None)

        if game:
            self.download_queue.append(game)
            self.update_waiting_queue_list() # Aggiorna lista visiva attesa
            if hasattr(self, 'roms_page'): # Aggiorna anche la pagina ROMS se esiste
                self.roms_page.add_to_queue(game['name'])
            self.log(f"Aggiunto in coda: {game['name']}")
        else:
             self.log(f"ERRORE: Impossibile trovare i dati per '{game_name}'")


    def update_waiting_queue_list(self):
        if not hasattr(self, 'waiting_queue_list'): return
        self.waiting_queue_list.clear()
        for game in self.download_queue:
            item = QListWidgetItem(game.get('name', 'N/A'))
            # Salva il nome nel UserRole per recuperarlo facilmente
            item.setData(Qt.ItemDataRole.UserRole, game.get('name'))
            self.waiting_queue_list.addItem(item)

    def remove_waiting_item(self, item):
        if not hasattr(self, 'waiting_queue_list'): return
        game_name = item.data(Qt.ItemDataRole.UserRole) # Recupera nome da UserRole
        if game_name:
            row = self.waiting_queue_list.row(item)
            self.waiting_queue_list.takeItem(row)
            # Rimuovi dalla coda interna
            self.download_queue = [g for g in self.download_queue if g.get('name') != game_name]
             # Rimuovi anche dalla pagina ROMS se esiste
            if hasattr(self, 'roms_page'):
                 self.roms_page.remove_from_queue(game_name)
            self.log(f"Rimosso dalla coda d'attesa: {game_name}")


    def update_file_progress(self, game_name, downloaded, total, speed, remaining_time):
        """Aggiorna il widget del download attivo specifico."""
        if not hasattr(self, 'active_downloads_layout'): return

        widget = self.active_downloads_widgets.get(game_name)
        if not widget:
            # Trova il gioco per ottenere il nome (anche se dovrebbe essere game_name)
            game_data = {"name": game_name, "size_bytes": total} # Dati minimi
            widget = DownloadQueueItemWidget(game_data)
            # Inserisci il nuovo widget all'inizio del layout dei download attivi
            self.active_downloads_layout.insertWidget(0, widget)
            self.active_downloads_widgets[game_name] = widget

        # Calcola percentuale
        percent = int(downloaded / total * 100) if total > 0 else 0
        widget.update_progress(percent)

        # Aggiorna statistiche nel widget specifico (se il widget le supporta)
        if hasattr(widget, 'update_stats'):
            speed_mb = speed / (1024 * 1024) if speed else 0
            # Aggiorna picco per questo widget
            peak_speed = self.roms_peak_speeds.get(game_name, 0)
            if speed_mb > peak_speed:
                self.roms_peak_speeds[game_name] = speed_mb
                peak_speed = speed_mb
            widget.update_stats(speed_mb, peak_speed)

        # Aggiorna anche la pagina ROMS (che ha una logica simile ma separata)
        if hasattr(self, 'roms_page'):
             self.update_roms_active_download(game_name, downloaded, total, speed, remaining_time)

        # Aggiorna barra progresso globale
        self.update_overall_progress()


    def update_overall_progress(self):
        """Ricalcola e aggiorna la barra di progresso globale."""
        if not hasattr(self, 'overall_progress_bar'): return

        total_bytes_active = 0
        downloaded_bytes_active = 0

        # Usa i dati salvati in roms_progress_stats che vengono aggiornati da update_roms_active_download
        for game_name, (downloaded, total, speed_mb) in self.roms_progress_stats.items():
             total_bytes_active += total
             downloaded_bytes_active += downloaded

        overall_percent = int(downloaded_bytes_active / total_bytes_active * 100) if total_bytes_active > 0 else 0
        self.overall_progress_bar.setValue(overall_percent)


    def remove_finished_file(self, finished_game_name):
        """ Gestisce la rimozione di un file completato dai widget attivi."""
         # Rimuovi widget dalla pagina principale 'Cerca ROMs'
        widget = self.active_downloads_widgets.pop(finished_game_name, None)
        if widget:
            widget.setParent(None)
            widget.deleteLater()

        # Aggiorna la pagina ROMS (chiamerà la sua logica di rimozione)
        if hasattr(self, 'roms_page'):
             self.on_download_finished_roms(finished_game_name, None) # Passa None come local_file

        # Ricalcola progresso globale dopo la rimozione
        self.update_overall_progress()


    def start_downloads(self):
            if not self.download_queue:
                self.log("Nessun download in coda.")
                QMessageBox.information(self, "Coda Vuota", "Aggiungere giochi alla coda prima di avviare il download.")
                return
            
            if hasattr(self, 'btn_start_downloads'): self.btn_start_downloads.setEnabled(False) # Avvia viene disabilitato
            if hasattr(self, 'btn_cancel_downloads'): self.btn_cancel_downloads.setEnabled(True)  # Annulla viene abilitato

            current_queue_copy = self.download_queue[:]
            queue_size = len(current_queue_copy)

            # Disabilita/Abilita bottoni
            if hasattr(self, 'btn_start_downloads'): self.btn_start_downloads.setEnabled(False)
            if hasattr(self, 'btn_cancel_downloads'): self.btn_cancel_downloads.setEnabled(True)

            # Svuota la lista visiva della coda di attesa (questo può rimanere qui)
            if hasattr(self, 'waiting_queue_list'): self.waiting_queue_list.clear()

            # Log con la dimensione salvata
            self.log(f"Avvio coda download ({queue_size} giochi)...")

            self.cancel_downloads(silent=True)

            # Crea il nuovo thread e worker
            self.download_manager_thread = QThread(self) # Rendi la finestra parent
            max_concurrent = MAX_CONCURRENT_DOWNLOADS # Leggi dalle config

            # Passa la COPIA GIA' FATTA della coda
            self.download_manager_worker = DownloadManager(
                current_queue_copy, # Ora questa copia contiene i giochi!
                self.update_waiting_queue_list, # Callback
                max_concurrent
            )
            self.download_manager_worker.moveToThread(self.download_manager_thread)

            # Connetti i segnali del worker (come prima)
            self.download_manager_worker.file_progress.connect(self.update_file_progress)
            self.download_manager_worker.log.connect(self.log)
            self.download_manager_worker.file_finished.connect(self.remove_finished_file)
            self.download_manager_worker.finished.connect(self.on_all_downloads_finished)

            # Connetti segnali del thread (come prima)
            self.download_manager_thread.started.connect(self.download_manager_worker.process_queue)
            self.download_manager_worker.finished.connect(self.download_manager_thread.quit)
            self.download_manager_worker.finished.connect(self.download_manager_worker.deleteLater)
            self.download_manager_thread.finished.connect(self.download_manager_thread.deleteLater)
            self.download_manager_thread.finished.connect(self._clear_download_worker_refs)


            # --- INIZIO FIX ---
            # Svuota la coda interna della MainWindow ORA.
            # Questo va bene perché il DownloadManager ha già ricevuto la sua copia.
            self.download_queue.clear()
            # --- FINE FIX ---

            # Avvia il thread
            self.download_manager_thread.start()
    def cancel_downloads(self, silent=False):
        """Annulla tutti i download attivi e pulisce il worker."""
        worker_existed = False
        if self.download_manager_worker:
            worker_existed = True
            if not silent: self.log("Annullamento download in corso...")
            self.download_manager_worker.cancel_all() # Dice al worker di fermarsi

        # Se il thread è ancora in esecuzione, prova a chiuderlo gentilmente
        if self.download_manager_thread and self.download_manager_thread.isRunning():
             self.download_manager_thread.quit()
             self.download_manager_thread.wait(500) # Attendi un po'

        # Pulisci riferimenti in ogni caso
        self._clear_download_worker_refs()

        # Riabilita/Disabilita bottoni
        if hasattr(self, 'btn_start_downloads'): self.btn_start_downloads.setEnabled(True)
        if hasattr(self, 'btn_cancel_downloads'): self.btn_cancel_downloads.setEnabled(False)

        # Svuota la coda di attesa (se l'utente aveva aggiunto roba dopo l'avvio)
        self.download_queue.clear()
        self.update_waiting_queue_list()

        # Rimuovi tutti i widget attivi dalla UI (potrebbero esserci rimasti se cancel è forzato)
        if hasattr(self, 'active_downloads_layout'):
            for game_name in list(self.active_downloads_widgets.keys()):
                 widget = self.active_downloads_widgets.pop(game_name, None)
                 if widget:
                     widget.setParent(None)
                     widget.deleteLater()
        # Resetta anche la pagina ROMS
        if hasattr(self, 'roms_page'):
            for game_name in list(self.roms_active_download_widgets.keys()):
                self.roms_page.remove_active_download(game_name)
            self.roms_active_download_widgets.clear()
            self.roms_page.queue_list.clear() # Svuota anche la sua coda visiva
            self.roms_page.completed_list.clear() # Svuota completati per sicurezza
            self.roms_page.update_global_progress(0, 0, 0, 0) # Resetta progresso globale

        self.roms_progress_stats.clear()
        self.roms_peak_speeds.clear()

        if worker_existed and not silent:
            self.log("Download annullati.")
            self.overall_progress_bar.setValue(0) # Resetta barra globale


    def _clear_download_worker_refs(self):
        """Resetta i riferimenti al worker e al thread dei download."""
        self.download_manager_worker = None
        self.download_manager_thread = None
        # print("DEBUG: Download worker references cleared.")


    def on_all_downloads_finished(self):
        self.log("Tutti i download nella coda attuale sono stati processati.")
        if hasattr(self, 'btn_start_downloads'): self.btn_start_downloads.setEnabled(True)
        if hasattr(self, 'btn_cancel_downloads'): self.btn_cancel_downloads.setEnabled(False)
        self.log("Pronto per avviare una nuova coda di download.")
        self._clear_download_worker_refs()

    def update_roms_active_download(self, game_name, downloaded, total, speed, remaining_time):
        """Aggiorna lo stato di un download attivo nella pagina ROMS."""
        if not hasattr(self, 'roms_page'): return

        percent = int(downloaded / total * 100) if total else 0

        # Crea/Ottieni widget nella pagina ROMS
        widget = self.roms_active_download_widgets.get(game_name)
        if not widget:
            # Aggiungi alla sezione attivi nella pagina ROMS e tieni traccia
            widget = self.roms_page.add_active_download(game_name)
            if widget: # add_active_download potrebbe restituire None se fallisce
                 self.roms_active_download_widgets[game_name] = widget
            else:
                 self.log(f"ERRORE: Impossibile creare widget attivo per {game_name} nella pagina ROMS.")
                 return # Esci se non si può creare il widget

        # Aggiorna barra di progresso nel widget della pagina ROMS
        self.roms_page.update_active_download(game_name, percent)

        # Calcola velocità e picco in MB/s
        speed_mb = speed / (1024 * 1024) if speed else 0.0
        peak_speed_mb = self.roms_peak_speeds.get(game_name, 0.0)
        if speed_mb > peak_speed_mb:
            self.roms_peak_speeds[game_name] = speed_mb
            peak_speed_mb = speed_mb

        # Aggiorna statistiche nel widget della pagina ROMS
        self.roms_page.update_active_stats(game_name, speed_mb, peak_speed_mb)

        # Aggiorna dati per calcolo globale (usato da update_overall_progress sulla pagina principale)
        self.roms_progress_stats[game_name] = (downloaded, total, speed_mb)

        # Ricalcola e aggiorna statistiche globali nella pagina ROMS
        # (Non chiamare update_overall_progress qui, quella aggiorna la barra nella pagina principale)
        total_active_bytes = sum(t for d, t, s in self.roms_progress_stats.values())
        downloaded_active_bytes = sum(d for d, t, s in self.roms_progress_stats.values())
        global_speed_mb = sum(s for d, t, s in self.roms_progress_stats.values())
        global_peak_mb = max(self.roms_peak_speeds.values(), default=0.0)

        self.roms_page.update_global_progress(
            downloaded_active_bytes,
            total_active_bytes,
            global_speed_mb,
            global_peak_mb
        )

    # Questo metodo viene chiamato dal segnale file_finished del DownloadManager
    def on_download_finished_roms(self, game_name, local_file_path):
        """Gestisce la fine di un download nella pagina ROMS."""
        if not hasattr(self, 'roms_page'): return

        # Rimuovi da attivi nella pagina ROMS
        self.roms_page.remove_active_download(game_name)
        self.roms_active_download_widgets.pop(game_name, None) # Rimuovi da tracciamento

        # Pulisci statistiche per questo gioco
        self.roms_progress_stats.pop(game_name, None)
        self.roms_peak_speeds.pop(game_name, None)

        # Rimuovi dalla coda visiva (se per caso era rimasto lì)
        self.roms_page.remove_from_queue(game_name)
        # Aggiungi ai completati
        self.roms_page.add_completed_download(game_name + (f" -> {local_file_path}" if local_file_path else " (Errore/Annullato)"))

        # Ricalcola statistiche globali nella pagina ROMS dopo rimozione
        total_active_bytes = sum(t for d, t, s in self.roms_progress_stats.values())
        downloaded_active_bytes = sum(d for d, t, s in self.roms_progress_stats.values())
        global_speed_mb = sum(s for d, t, s in self.roms_progress_stats.values())
        global_peak_mb = max(self.roms_peak_speeds.values(), default=0.0)
        self.roms_page.update_global_progress(
            downloaded_active_bytes,
            total_active_bytes,
            global_speed_mb,
            global_peak_mb
        )

        # Aggiorna anche la libreria sulla pagina Libreria
        if hasattr(self, 'library_page'):
            self.library_page.refresh_library()


    # --- Metodi per Dialoghi Impostazioni ---

    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            values = dialog.get_values()
            # Applica e salva le impostazioni tramite le funzioni in config.py
            if "download_folder" in values:
                 set_user_download_folder(values["download_folder"])
            if "max_dl" in values:
                 set_max_concurrent_downloads(values["max_dl"])
            self.log(f"Impostazioni generali aggiornate: Cartella='{USER_DOWNLOADS_FOLDER}', Max DL={MAX_CONCURRENT_DOWNLOADS}")
            # Aggiorna la libreria se il percorso è cambiato
            if hasattr(self, 'library_page'):
                self.library_page.load_library()


    def open_emulator_settings(self, core_display_name, core_file_base):
        """
        Apre il dialogo per modificare le impostazioni del core specifico.
        core_display_name: Nome visualizzato (es. "Nintendo 64")
        core_file_base: Nome base del file core (es. "mupen64plus_next_libretro")
        """
        # Costruisci il nome del file di configurazione (es. mupen64plus_next_libretro.cfg)
        config_filename = core_file_base + ".cfg"
        config_path = os.path.join(EMULATOR_CONFIG_FOLDER, config_filename)

        # Passa il nome visualizzato e il percorso completo del file .cfg al dialogo
        dialog = EmulatorSettingsDialog(core_display_name, config_path, self)
        if dialog.exec():
            self.log(f"Impostazioni per '{core_display_name}' salvate in '{config_path}'")
        else:
             self.log(f"Modifiche alle impostazioni per '{core_display_name}' annullate.")


    def open_hotkeys_dialog(self):
        """Apre il dialogo per configurare i tasti rapidi globali e per il giocatore 1."""
        dialog = HotkeysDialog(self.key_bindings, self)
        if dialog.exec():
            self.log("Salvataggio Hotkeys...")
            # Ora dobbiamo salvare i binding nei file di configurazione corretti.
            # Dividiamo i binding in "globali" e "player1"
            global_bindings = {}
            player1_bindings = {}
            for command, value in self.key_bindings.bindings.items():
                 if command.startswith("input_player1_"):
                     player1_bindings[command] = value
                 else:
                     global_bindings[command] = value

            # Converti i valori usando convert_binding prima di salvare
            converted_global = {cmd: convert_binding(val) for cmd, val in global_bindings.items() if val}
            converted_player1 = {cmd: convert_binding(val) for cmd, val in player1_bindings.items() if val}

            # 1. Salva i binding globali nel file retroarch_global.cfg
            global_config_path = os.path.join(EMULATOR_CONFIG_FOLDER, "retroarch_global.cfg")
            try:
                update_emulator_config(global_config_path, converted_global)
                self.log(f"Binding globali salvati in: {global_config_path}")
            except Exception as e:
                 self.log(f"ERRORE nel salvataggio di {global_config_path}: {e}")
                 QMessageBox.critical(self, "Errore Salvataggio", f"Impossibile salvare i binding globali:\n{e}")

            # 2. Trova i file di configurazione dei core associati ai controlli player1
            #    e aggiorna *solo* le righe relative a input_player1_*
            #    Questo è complesso perché i binding P1 possono essere diversi per core.
            #    Approccio semplice: aggiorniamo TUTTI i file .cfg dei core con i binding P1 attuali.
            #    ATTENZIONE: Questo sovrascriverà eventuali binding P1 specifici del core!
            #    Un approccio migliore richiederebbe di sapere a quale console/core
            #    si riferiscono i binding P1 modificati nel dialogo.
            #    Per ora, applichiamo i P1 a tutti i core definiti.
            self.log("Applicazione binding Player 1 ai file di configurazione dei core...")
            updated_core_files = []
            for core_name, core_file_base in DEFAULT_CORES.items():
                core_config_filename = core_file_base + ".cfg"
                core_config_path = os.path.join(EMULATOR_CONFIG_FOLDER, core_config_filename)
                try:
                    update_emulator_config(core_config_path, converted_player1)
                    updated_core_files.append(core_config_filename)
                except Exception as e:
                     self.log(f"ERRORE nell'aggiornamento di {core_config_path}: {e}")

            if updated_core_files:
                 self.log(f"Binding Player 1 aggiornati per i core: {', '.join(updated_core_files)}")
            self.log("Salvataggio Hotkeys completato.")
        else:
            self.log("Modifica Hotkeys annullata.")

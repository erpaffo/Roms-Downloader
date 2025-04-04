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
from src.gui.roms_page import RomsPage
from src.config import (
    CONSOLES, CORE_EXT, DEFAULT_CORES, EMULATOR_CONFIG_FOLDER,
    USER_DOWNLOADS_FOLDER, resource_path, set_user_download_folder, set_max_concurrent_downloads,
    settings, DEFAULT_DOWNLOADS_FOLDER, MAX_CONCURRENT_DOWNLOADS
)
from src.workers.scrape_worker import ScrapeWorker
from src.workers.download_manager import DownloadManager
from src.gui.download_queue_item import DownloadQueueItemWidget
from src.utils import extract_nations, ALLOWED_NATIONS, update_emulator_config, convert_binding
from src.gui.settings_dialog import SettingsDialog
from src.gui.library_page import LibraryPage
from src.gui.weight_item import WeightItem
from src.default_keybindings import DEFAULT_KEYBINDINGS
from src.gui.controls_page import ControlsPage

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Roms Downloader")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(800, 600)

        try:
            qss_relative_path = os.path.join("src", "gui", "styles", "style.qss")
            qss_abs_path = resource_path(qss_relative_path)

            if os.path.exists(qss_abs_path):
                with open(qss_abs_path, "r", encoding='utf-8') as f:
                    style_sheet = f.read()
                    app = QApplication.instance()
                    if app:
                        app.setStyleSheet(style_sheet)
                        logging.info(f"Stile QSS caricato da: {qss_abs_path}")
                    else:
                        logging.warning("Istanza QApplication non trovata durante l'applicazione dello stile QSS.")
            else:
                qss_relative_path_alt = os.path.join("src", "style.qss")
                qss_abs_path_alt = resource_path(qss_relative_path_alt)
                if os.path.exists(qss_abs_path_alt):
                     with open(qss_abs_path_alt, "r", encoding='utf-8') as f:
                         style_sheet = f.read()
                         app = QApplication.instance()
                         if app:
                             app.setStyleSheet(style_sheet)
                             logging.info(f"Stile QSS caricato da: {qss_abs_path_alt}")
                         else:
                             logging.warning("Istanza QApplication non trovata durante l'applicazione dello stile QSS.")
                else:
                     logging.warning(f"File Stile QSS non trovato nei percorsi attesi:\n- {qss_abs_path}\n- {qss_abs_path_alt}")

        except Exception as e:
            logging.error(f"Errore durante il caricamento dello stile QSS: {e}")

        self.games_list = []
        self.download_queue = []
        self.active_downloads_widgets = {}
        self.roms_active_download_widgets = {}
        self.roms_progress_stats = {}
        self.roms_peak_speeds = {}
        self.last_speed = {}
        self.download_manager_worker = None
        self.download_manager_thread = None

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList")
        self.nav_list.setFixedWidth(180)
        
        self.nav_list.addItem("Cerca ROMs")
        self.nav_list.addItem("Libreria")
        self.nav_list.addItem("Gestione Download")
        self.nav_list.addItem("Controlli & Impostazioni")

        self.nav_list.currentRowChanged.connect(self.change_page)
        main_layout.addWidget(self.nav_list)

        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        menu_bar = self._create_menu_bar()
        content_layout.setMenuBar(menu_bar)

        self.stacked_widget = QStackedWidget()
        self.download_manager_page = QWidget()
        self.library_page = LibraryPage()
        self.roms_page = RomsPage()
        self.controls_page = ControlsPage(config_folder=EMULATOR_CONFIG_FOLDER)

        self.init_download_manager_page()

        self.stacked_widget.addWidget(self.download_manager_page)  # Indice 0
        self.stacked_widget.addWidget(self.library_page)           # Indice 1
        self.stacked_widget.addWidget(self.roms_page)              # Indice 2
        self.stacked_widget.addWidget(self.controls_page)          # Indice 3

        content_layout.addWidget(self.stacked_widget)

        main_layout.addWidget(content_container)

        self.nav_list.setCurrentRow(0)

        initial_console = list(CONSOLES.keys())[0] if CONSOLES else "Atari 2600"
        if hasattr(self, 'console_combo'):
            initial_console = self.console_combo.currentText()
        self.load_games(initial_console)

    def _create_menu_bar(self):
        """Creates and returns the main menu bar."""
        menu_bar = QMenuBar()
        settings_menu = QMenu("Impostazioni", self)
        menu_bar.addMenu(settings_menu)
        settings_action = QAction("Opzioni Generali", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(settings_action)

        return menu_bar

    def change_page(self, index):
        """Changes the current page in the QStackedWidget."""
        self.stacked_widget.setCurrentIndex(index)
        if index == 1:
             self.library_page.refresh_library()

    def init_download_manager_page(self):
        """Initializes the layout of the 'Find ROMs' page."""
        page_layout = QVBoxLayout(self.download_manager_page)
        page_layout.setContentsMargins(10, 10, 10, 10)
        page_layout.setSpacing(10)

        page_layout.addLayout(self._create_top_controls())

        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)

        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0,0,0,0)
        self.table = self._create_games_table()
        table_layout.addWidget(self.table)
        main_splitter.addWidget(table_container)

        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0,0,0,0)
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.setChildrenCollapsible(False)

        download_sections_widget = QWidget()
        download_sections_layout = self._create_download_sections()
        download_sections_widget.setLayout(download_sections_layout)
        bottom_splitter.addWidget(download_sections_widget)

        log_widget = QWidget()
        log_layout = self._create_log_area()
        log_widget.setLayout(log_layout)
        bottom_splitter.addWidget(log_widget)

        bottom_splitter.setStretchFactor(0, 6)
        bottom_splitter.setStretchFactor(1, 4)

        bottom_layout.addWidget(bottom_splitter)
        main_splitter.addWidget(bottom_container)

        main_splitter.setStretchFactor(0, 5)
        main_splitter.setStretchFactor(1, 5)

        page_layout.addWidget(main_splitter)

        if hasattr(self, 'btn_start_downloads'):
            self.btn_start_downloads.setEnabled(True)
        if hasattr(self, 'btn_cancel_downloads'):
            self.btn_cancel_downloads.setEnabled(False)

    def _create_top_controls(self):
        """Creates the layout for the top controls (console, search, filter)."""
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
        """Creates and returns the games table widget."""
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
        table.setSortingEnabled(True)
        return table

    def _create_download_sections(self):
        """Creates the layout for the download-related sections."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)

        layout.addWidget(QLabel("Coda Download (Attesa):"))
        self.waiting_queue_list = QListWidget()
        self.waiting_queue_list.setMaximumHeight(120)
        self.waiting_queue_list.itemDoubleClicked.connect(self.remove_waiting_item)
        layout.addWidget(self.waiting_queue_list)

        layout.addWidget(QLabel("Download Attivi:"))
        self.active_downloads_container = QWidget()
        self.active_downloads_layout = QVBoxLayout()
        self.active_downloads_layout.setContentsMargins(0,0,0,0)
        self.active_downloads_container.setLayout(self.active_downloads_layout)
        self.active_downloads_layout.addStretch()
        layout.addWidget(self.active_downloads_container, 1)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Progresso Globale:"))
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setValue(0)
        progress_layout.addWidget(self.overall_progress_bar)
        layout.addLayout(progress_layout)

        actions_layout = QHBoxLayout()
        self.btn_start_downloads = QPushButton("Avvia Download Coda")
        self.btn_start_downloads.clicked.connect(self.start_downloads)
        actions_layout.addWidget(self.btn_start_downloads)
        self.btn_cancel_downloads = QPushButton("Annulla Tutti")
        self.btn_cancel_downloads.clicked.connect(self.cancel_downloads)
        actions_layout.addWidget(self.btn_cancel_downloads)
        layout.addLayout(actions_layout)
        return layout

    def _create_log_area(self):
        """Creates the layout for the log area."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.addWidget(QLabel("Log:"))
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        return layout

    def select_download_folder(self):
        """Opens a dialog to select the download folder."""
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella download", USER_DOWNLOADS_FOLDER)
        if folder:
            set_user_download_folder(folder)
            self.log(f"Cartella download impostata su: {folder}")
            if hasattr(self, 'library_page'):
                self.library_page.load_library()

    def log(self, message):
        """Logs a message to the info level and appends to the log area."""
        logging.info(message)
        if hasattr(self, 'log_area'):
            self.log_area.appendPlainText(message)

    def console_changed(self, console_name):
        """Handles the change in the selected console."""
        self.log(f"Console cambiata: {console_name}")
        self.load_games(console_name)

    def load_games(self, console_name):
        """Loads the list of games for the selected console."""
        self.log(f"Caricamento giochi per '{console_name}'...")
        if not hasattr(self, 'table'):
             print("WARN: Table widget not ready for loading games.")
             return
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)

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
        """Handles the completion of the game scraping process."""
        self.log(f"Caricati {len(games)} giochi.")
        for game in games:
            game["nations"] = extract_nations(game.get("name", ""))
        self.games_list = games
        self.update_table()
        if hasattr(self, 'library_page'):
            self.library_page.load_library()

    def update_table(self):
        """Updates the games table based on the current list and filters."""
        if not hasattr(self, 'table'):
             print("WARN: Table widget not ready for updating.")
             return
        search_text = self.search_bar.text().lower().strip() if hasattr(self, 'search_bar') else ""
        search_terms = search_text.split()

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        selected_nation = getattr(self, "selected_nation", "").lower()

        for game in self.games_list:
            name_lower = game.get('name', '').lower()
            if search_terms and any(term not in name_lower for term in search_terms):
                continue
            if selected_nation:
                nations_lower = [n.lower() for n in game.get("nations", [])]
                if selected_nation not in nations_lower:
                    continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            item_name = QTableWidgetItem(game.get('name', 'N/A'))
            item_size = WeightItem(game.get('size_str', '0 B'))
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_size)

        self.table.setSortingEnabled(True)
        self.log(f"Tabella aggiornata, {self.table.rowCount()} giochi visualizzati.")

    def filter_by_nation(self):
        """Opens a dialog to filter games by nation."""
        nations = sorted(list(ALLOWED_NATIONS))
        nation, ok = QInputDialog.getItem(self, "Filtra per Nazione", "Seleziona nazione (vuoto per rimuovere filtro):", [""] + nations, 0, False)
        if ok:
            self.selected_nation = nation
            self.log(f"Filtro nazione impostato su: '{nation}'" if nation else "Filtro nazione rimosso.")
            self.update_table()

    def on_table_double_click(self, row, column):
        """Adds a game to the download queue on double-click."""
        start_enabled = self.btn_start_downloads.isEnabled() if hasattr(self, 'btn_start_downloads') else True
        if not start_enabled:
            QMessageBox.warning(self, "Attenzione", "Attendere il termine dei download prima di aggiungere altri giochi.")
            return

        if not hasattr(self, 'table'): return
        game_name_item = self.table.item(row, 0)
        if not game_name_item: return
        game_name = game_name_item.text()

        if hasattr(self, 'library_page') and hasattr(self.library_page, 'library_files'):
            game_already_downloaded = False
            for file_path in self.library_page.library_files:
                try:
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    if base_name.lower() == game_name.lower():
                        game_already_downloaded = True
                        break
                except Exception: continue
            if game_already_downloaded:
                QMessageBox.information(self, "Già scaricato", f"'{game_name}' è già presente nella tua libreria.")
                return

        if any(g['name'] == game_name for g in self.download_queue):
             QMessageBox.information(self, "Già in coda", f"'{game_name}' è già nella coda di download.")
             return

        game = next((g for g in self.games_list if g.get('name') == game_name), None)

        if game:
            self.download_queue.append(game)
            self.update_waiting_queue_list()
            if hasattr(self, 'roms_page'):
                self.roms_page.add_to_queue(game['name'])
            self.log(f"Aggiunto in coda: {game['name']}")
        else:
             self.log(f"ERRORE: Impossibile trovare i dati per '{game_name}'")

    def update_waiting_queue_list(self):
        """Updates the visual waiting queue list."""
        if not hasattr(self, 'waiting_queue_list'): return
        self.waiting_queue_list.clear()
        for game in self.download_queue:
            item = QListWidgetItem(game.get('name', 'N/A'))
            item.setData(Qt.ItemDataRole.UserRole, game.get('name'))
            self.waiting_queue_list.addItem(item)

    def remove_waiting_item(self, item):
        """Removes a game from the waiting queue on double-click."""
        if not hasattr(self, 'waiting_queue_list'): return
        game_name = item.data(Qt.ItemDataRole.UserRole)
        if game_name:
            row = self.waiting_queue_list.row(item)
            self.waiting_queue_list.takeItem(row)
            self.download_queue = [g for g in self.download_queue if g.get('name') != game_name]
            if hasattr(self, 'roms_page'):
                 self.roms_page.remove_from_queue(game_name)
            self.log(f"Rimosso dalla coda d'attesa: {game_name}")

    def update_file_progress(self, game_name, downloaded, total, speed, remaining_time):
        """Updates the specific widget for an active download."""
        if not hasattr(self, 'active_downloads_layout'): return

        widget = self.active_downloads_widgets.get(game_name)
        if not widget:
            game_data = {"name": game_name, "size_bytes": total}
            widget = DownloadQueueItemWidget(game_data)
            self.active_downloads_layout.insertWidget(0, widget)
            self.active_downloads_widgets[game_name] = widget

        percent = int(downloaded / total * 100) if total > 0 else 0
        widget.update_progress(percent)

        if hasattr(widget, 'update_stats'):
            speed_mb = speed / (1024 * 1024) if speed else 0
            peak_speed = self.roms_peak_speeds.get(game_name, 0)
            if speed_mb > peak_speed:
                self.roms_peak_speeds[game_name] = speed_mb
                peak_speed = speed_mb
            widget.update_stats(speed_mb, peak_speed)

        if hasattr(self, 'roms_page'):
             self.update_roms_active_download(game_name, downloaded, total, speed, remaining_time)

        self.update_overall_progress()

    def update_overall_progress(self):
        """Recalculates and updates the overall progress bar."""
        if not hasattr(self, 'overall_progress_bar'): return
        total_bytes_active = 0
        downloaded_bytes_active = 0
        for game_name, (downloaded, total, speed_mb) in self.roms_progress_stats.items():
             total_bytes_active += total
             downloaded_bytes_active += downloaded
        overall_percent = int(downloaded_bytes_active / total_bytes_active * 100) if total_bytes_active > 0 else 0
        self.overall_progress_bar.setValue(overall_percent)

    def remove_finished_file(self, finished_game_name):
        """Handles the removal of a completed file's widget."""
        widget = self.active_downloads_widgets.pop(finished_game_name, None)
        if widget:
            widget.setParent(None)
            widget.deleteLater()
        if hasattr(self, 'roms_page'):
             self.on_download_finished_roms(finished_game_name, None)
        self.update_overall_progress()

    def start_downloads(self):
        """Starts the download manager for the games in the queue."""
        if not self.download_queue:
            self.log("Nessun download in coda.")
            QMessageBox.information(self, "Coda Vuota", "Aggiungere giochi alla coda prima di avviare il download.")
            return

        current_queue_copy = self.download_queue[:]
        queue_size = len(current_queue_copy)

        if hasattr(self, 'btn_start_downloads'): self.btn_start_downloads.setEnabled(False)
        if hasattr(self, 'btn_cancel_downloads'): self.btn_cancel_downloads.setEnabled(True)
        if hasattr(self, 'waiting_queue_list'): self.waiting_queue_list.clear()

        self.log(f"Avvio coda download ({queue_size} giochi)...")
        self.cancel_downloads(silent=True)

        self.download_manager_thread = QThread(self)
        max_concurrent = MAX_CONCURRENT_DOWNLOADS

        self.download_manager_worker = DownloadManager(
            current_queue_copy,
            self.update_waiting_queue_list,
            max_concurrent
        )
        self.download_manager_worker.moveToThread(self.download_manager_thread)

        self.download_manager_worker.file_progress.connect(self.update_file_progress, Qt.ConnectionType.QueuedConnection)
        self.download_manager_worker.log.connect(self.log)
        self.download_manager_worker.file_finished.connect(self.remove_finished_file)
        self.download_manager_worker.finished.connect(self.on_all_downloads_finished)

        self.download_manager_thread.started.connect(self.download_manager_worker.process_queue)
        self.download_manager_worker.finished.connect(self.download_manager_thread.quit)
        self.download_manager_worker.finished.connect(self.download_manager_worker.deleteLater)
        self.download_manager_thread.finished.connect(self.download_manager_thread.deleteLater)
        self.download_manager_thread.finished.connect(self._clear_download_worker_refs)

        self.download_queue.clear()
        self.download_manager_thread.start()

    def cancel_downloads(self, silent=False):
        """Cancels all active downloads and cleans up the worker."""
        worker_existed = False
        if self.download_manager_worker:
            worker_existed = True
            if not silent: self.log("Annullamento download in corso...")
            self.download_manager_worker.cancel_all()

        if self.download_manager_thread and self.download_manager_thread.isRunning():
             self.download_manager_thread.quit()
             self.download_manager_thread.wait(500)

        self._clear_download_worker_refs()

        if hasattr(self, 'btn_start_downloads'): self.btn_start_downloads.setEnabled(True)
        if hasattr(self, 'btn_cancel_downloads'): self.btn_cancel_downloads.setEnabled(False)

        self.download_queue.clear()
        self.update_waiting_queue_list()

        if hasattr(self, 'active_downloads_layout'):
            for game_name in list(self.active_downloads_widgets.keys()):
                 widget = self.active_downloads_widgets.pop(game_name, None)
                 if widget:
                     widget.setParent(None)
                     widget.deleteLater()
        if hasattr(self, 'roms_page'):
            for game_name in list(self.roms_active_download_widgets.keys()):
                self.roms_page.remove_active_download(game_name)
            self.roms_active_download_widgets.clear()
            self.roms_page.queue_list.clear()
            self.roms_page.completed_list.clear()
            self.roms_page.update_global_progress(0, 0, 0, 0)

        self.roms_progress_stats.clear()
        self.roms_peak_speeds.clear()

        if worker_existed and not silent:
            self.log("Download annullati.")
            if hasattr(self, 'overall_progress_bar'): # Check before setting value
                self.overall_progress_bar.setValue(0)


    def _clear_download_worker_refs(self):
        """Resets references to the download worker and thread."""
        self.download_manager_worker = None
        self.download_manager_thread = None

    def on_all_downloads_finished(self):
        """Handles the completion of all downloads in the current batch."""
        self.log("Tutti i download nella coda attuale sono stati processati.")
        if hasattr(self, 'btn_start_downloads'): self.btn_start_downloads.setEnabled(True)
        if hasattr(self, 'btn_cancel_downloads'): self.btn_cancel_downloads.setEnabled(False)
        self.log("Pronto per avviare una nuova coda di download.")
        self._clear_download_worker_refs()

    def update_roms_active_download(self, game_name, downloaded, total, speed, remaining_time):
        """Updates the state of an active download on the RomsPage."""
        if not hasattr(self, 'roms_page'): return

        percent = int(downloaded / total * 100) if total else 0

        widget = self.roms_active_download_widgets.get(game_name)
        if not widget:
            widget = self.roms_page.add_active_download(game_name)
            if widget:
                 self.roms_active_download_widgets[game_name] = widget
            else:
                 self.log(f"ERRORE: Impossibile creare widget attivo per {game_name} nella pagina ROMS.")
                 return

        self.roms_page.update_active_download(game_name, percent)

        speed_mb = speed / (1024 * 1024) if speed else 0.0
        peak_speed_mb = self.roms_peak_speeds.get(game_name, 0.0)
        if speed_mb > peak_speed_mb:
            self.roms_peak_speeds[game_name] = speed_mb
            peak_speed_mb = speed_mb

        self.roms_page.update_active_stats(game_name, speed_mb, peak_speed_mb)

        self.roms_progress_stats[game_name] = (downloaded, total, speed_mb)

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

    def on_download_finished_roms(self, game_name, local_file_path):
        """Handles the completion of a specific download on the RomsPage."""
        if not hasattr(self, 'roms_page'): return

        self.roms_page.remove_active_download(game_name)
        self.roms_active_download_widgets.pop(game_name, None)

        self.roms_progress_stats.pop(game_name, None)
        self.roms_peak_speeds.pop(game_name, None)

        self.roms_page.remove_from_queue(game_name)
        self.roms_page.add_completed_download(game_name + (f" -> {local_file_path}" if local_file_path else " (Errore/Annullato)"))

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

        if hasattr(self, 'library_page'):
            self.library_page.refresh_library()

    def show_settings_dialog(self):
        """Shows the general settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec():
            values = dialog.get_values()
            if "download_folder" in values:
                 set_user_download_folder(values["download_folder"])
            if "max_dl" in values:
                 set_max_concurrent_downloads(values["max_dl"])
            self.log(f"Impostazioni generali aggiornate: Cartella='{USER_DOWNLOADS_FOLDER}', Max DL={MAX_CONCURRENT_DOWNLOADS}")
            if hasattr(self, 'library_page'):
                self.library_page.load_library()
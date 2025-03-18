import os
import sys
import weakref
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QPlainTextEdit, QListWidget, QListWidgetItem, QProgressBar,
    QStackedWidget, QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt, QThread
import logging

from src.config import CONSOLES, DOWNLOADS_FOLDER
from src.workers.scrape_worker import ScrapeWorker
from src.workers.download_manager import DownloadManager
from src.gui.download_queue_item import DownloadQueueItemWidget
from src.utils import extract_nations, launch_game, format_rate, format_space

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Manager - Like Steam")
        self.setGeometry(100, 100, 1200, 800)
        
        self.games_list = []      # Giochi ottenuti dallo scraping
        self.download_queue = []  # Giochi in attesa di download
        self.active_downloads_widgets = {}  # Mapping: nome gioco -> widget in download attivo
        
        self.stacked_widget = QStackedWidget()
        self.download_manager_page = QWidget()
        self.library_page = QWidget()
        self.init_download_manager_page()
        self.init_library_page()
        
        self.stacked_widget.addWidget(self.download_manager_page)
        self.stacked_widget.addWidget(self.library_page)
        
        main_layout = QVBoxLayout()
        nav_layout = QHBoxLayout()
        self.btn_download_manager = QPushButton("Download Manager")
        self.btn_library = QPushButton("Library")
        self.btn_download_manager.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.btn_library.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        nav_layout.addWidget(self.btn_download_manager)
        nav_layout.addWidget(self.btn_library)
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)
        
        # Carica inizialmente i giochi per la console "3ds"
        self.load_games("3ds")
    
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
        search_text = self.search_bar.text().lower()
        self.table.setRowCount(0)
        for game in self.games_list:
            if search_text and search_text not in game['name'].lower():
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            item_name = QTableWidgetItem(game['name'])
            item_size = QTableWidgetItem(game['size_str'])
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_size)
    
    def on_table_double_click(self, row, column):
        game_name = self.table.item(row, 0).text()
        # Verifica se il gioco è già nella libreria
        game_already_downloaded = False
        for file_path in self.library_files:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            if base_name.lower() == game_name.lower():
                game_already_downloaded = True
                break
        if game_already_downloaded:
            QMessageBox.information(self, "Già scaricato", "Questo gioco è già presente nella tua libreria!")
            return
        # Aggiungi il gioco alla coda (self.download_queue) e aggiorna la lista d'attesa
        game = next((g for g in self.games_list if g['name'] == game_name), None)
        if game and game not in self.download_queue:
            self.download_queue.append(game)
            self.update_waiting_queue_list()
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
        widget = self.active_downloads_widgets.get(game_name)
        if widget:
            widget.update_progress(percent)
        else:
            # Se non esiste ancora, crealo e aggiungilo al container degli active downloads
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
        self.download_manager_worker = DownloadManager(self.download_queue, lambda: self.update_waiting_queue_list(), max_concurrent)
        self.download_manager_worker.file_progress.connect(self.update_file_progress)
        self.download_manager_worker.overall_progress.connect(self.overall_progress_bar.setValue)
        self.download_manager_worker.detailed_progress.connect(self.update_detailed_progress)
        self.download_manager_worker.file_finished.connect(self.remove_active_download_widget)
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
        Se l'item selezionato è un file (foglia del QTreeWidget), tenta di lanciarlo
        con l'emulatore corrispondente.
        """
        # Se l'item ha dei figli, si tratta di un gruppo, quindi non fare nulla.
        if item.childCount() > 0:
            return
        file_path = item.data(0, Qt.UserRole)
        try:
            launch_game(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile avviare l'emulatore: {e}")

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


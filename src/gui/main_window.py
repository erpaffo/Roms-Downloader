import sys
import weakref
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QPlainTextEdit, QListWidget, QListWidgetItem, QProgressBar, QSplitter, QMessageBox,
    QCheckBox, QGroupBox
)
from PySide6.QtCore import Qt, QThread
import logging

from src.config import CONSOLES
from src.workers.scrape_worker import ScrapeWorker
from src.workers.download_manager import DownloadManager
from src.gui.download_queue_item import DownloadQueueItemWidget
from src.utils import extract_nations  

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Download Manager Giochi")
        self.setGeometry(100, 100, 1100, 600)
        self.games_list = []
        self.download_queue = []       # Lista dei giochi in coda
        self.queue_widgets = {}        # Mapping: nome gioco -> weakref al widget
        self.download_manager_thread = None
        self.download_manager_worker = None

        splitter = QSplitter(Qt.Horizontal)
        # Pannello sinistro: elenco giochi, controlli e log
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        # Raggruppa i controlli in un unico layout orizzontale
        top_layout = QHBoxLayout()
        # Selezione console
        top_layout.addWidget(QLabel("Seleziona Console:"))
        self.console_combo = QComboBox()
        self.console_combo.addItems(list(CONSOLES.keys()))
        self.console_combo.currentTextChanged.connect(self.console_changed)
        top_layout.addWidget(self.console_combo)
        # Barra di ricerca testuale
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Cerca gioco...")
        self.search_bar.textChanged.connect(self.update_table)
        top_layout.addWidget(self.search_bar)
        # Menù a tendina per ordinamento
        top_layout.addWidget(QLabel("Ordina per:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Nome", "Peso"])
        self.sort_combo.currentIndexChanged.connect(self.update_table)
        top_layout.addWidget(self.sort_combo)
        left_layout.addLayout(top_layout)

        # Sezione per filtro per nazione
        nation_group = QGroupBox("Filtra per Nazione")
        nation_layout = QHBoxLayout()
        self.nation_checkboxes = {}
        nation_list = ["Japan", "USA", "Europe", "Spain", "Italy", "Germany", "France", "China"]
        for nation in nation_list:
            cb = QCheckBox(nation)
            cb.stateChanged.connect(self.update_table)
            self.nation_checkboxes[nation] = cb
            nation_layout.addWidget(cb)
        nation_group.setLayout(nation_layout)
        left_layout.addWidget(nation_group)

        # Tabella dei giochi
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Nome Gioco", "Peso"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        left_layout.addWidget(self.table)

        # Pulsanti per il download e il log
        actions_layout = QHBoxLayout()
        self.start_download_btn = QPushButton("Avvia Download")
        self.start_download_btn.clicked.connect(self.start_downloads)
        actions_layout.addWidget(self.start_download_btn)
        self.cancel_download_btn = QPushButton("Annulla Download")
        self.cancel_download_btn.clicked.connect(self.cancel_downloads)
        actions_layout.addWidget(self.cancel_download_btn)
        self.show_completed_btn = QPushButton("Visualizza Download Precedenti")
        self.show_completed_btn.clicked.connect(self.show_completed_downloads)
        actions_layout.addWidget(self.show_completed_btn)
        left_layout.addLayout(actions_layout)

        left_layout.addWidget(QLabel("Log:"))
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(150)
        left_layout.addWidget(self.log_area)
        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)

        # Pannello destro: coda download e progress bar globale
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Coda Download:"))
        self.queue_list = QListWidget()
        # Connetti il doppio clic per rimuovere l'item dalla coda
        self.queue_list.itemDoubleClicked.connect(self.remove_queue_item)
        right_layout.addWidget(self.queue_list)
        right_layout.addWidget(QLabel("Progresso Globale:"))
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setValue(0)
        right_layout.addWidget(self.overall_progress_bar)
        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)
        splitter.setSizes([750, 350])
        main_layout = QVBoxLayout()
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self.load_games(self.console_combo.currentText())

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
        from src.workers.scrape_worker import ScrapeWorker
        self.scrape_worker = ScrapeWorker(console_name)
        self.scrape_worker.moveToThread(self.scrape_thread)
        self.scrape_thread.started.connect(self.scrape_worker.run)
        self.scrape_worker.progress.connect(self.log)
        self.scrape_worker.finished.connect(self.on_games_loaded)
        self.scrape_worker.finished.connect(self.scrape_thread.quit)
        self.scrape_worker.finished.connect(self.scrape_worker.deleteLater)
        self.scrape_thread.finished.connect(self.scrape_thread.deleteLater)
        self.scrape_thread.start()

    def update_queue_list(self):
        self.queue_list.clear()
        for game in self.download_queue:
            widget = DownloadQueueItemWidget(game)
            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.queue_list.addItem(item)
            self.queue_list.setItemWidget(item, widget)
            
    def on_games_loaded(self, games):
        from src.utils import extract_nations
        for game in games:
            game["nations"] = extract_nations(game["name"])
        self.games_list = games
        self.update_table()

    def update_table(self):
        search_text = self.search_bar.text().lower()
        selected_nations = [nation for nation, cb in self.nation_checkboxes.items() if cb.isChecked()]
        self.table.setRowCount(0)
        filtered_games = []
        for game in self.games_list:
            if search_text and search_text not in game['name'].lower():
                continue
            if selected_nations:
                game_nations = game.get("nations", [])
                if not any(n in game_nations for n in selected_nations):
                    continue
            filtered_games.append(game)
        sort_criteria = self.sort_combo.currentText()
        if sort_criteria == "Nome":
            filtered_games.sort(key=lambda x: x['name'].lower())
        elif sort_criteria == "Peso":
            filtered_games.sort(key=lambda x: x['size_bytes'])
        for game in filtered_games:
            row = self.table.rowCount()
            self.table.insertRow(row)
            item_name = QTableWidgetItem(game['name'])
            item_size = QTableWidgetItem(game['size_str'])
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_size)

    def sort_by_name(self):
        self.sort_combo.setCurrentText("Nome")
        self.update_table()

    def sort_by_size(self):
        self.sort_combo.setCurrentText("Peso")
        self.update_table()

    def on_table_double_click(self, row, column):
        game_name = self.table.item(row, 0).text()
        game = next((g for g in self.games_list if g['name'] == game_name), None)
        if game and game not in self.download_queue:
            self.download_queue.append(game)
            widget = DownloadQueueItemWidget(game)
            item = QListWidgetItem()
            item.setData(Qt.UserRole, game['name'])
            item.setSizeHint(widget.sizeHint())
            self.queue_list.addItem(item)
            self.queue_list.setItemWidget(item, widget)
            import weakref
            self.queue_widgets[game['name']] = weakref.ref(widget)
            self.log(f"Aggiunto in coda: {game['name']}")

    def remove_queue_item(self, item):
        game_name = item.data(Qt.UserRole)
        row = self.queue_list.row(item)
        self.queue_list.takeItem(row)
        self.download_queue = [g for g in self.download_queue if g['name'] != game_name]
        if game_name in self.queue_widgets:
            del self.queue_widgets[game_name]
        self.log(f"Rimosso dalla coda: {game_name}")

    def update_file_progress(self, game_name, percent):
        widget_ref = self.queue_widgets.get(game_name)
        if widget_ref is not None:
            widget = widget_ref()
            if widget is not None:
                widget.update_progress(percent)

    def start_downloads(self):
        if not self.download_queue:
            self.log("Nessun download in coda.")
            return
        self.log("Avvio coda download...")
        self.download_manager_thread = QThread()
        self.download_manager_worker = DownloadManager(self.download_queue, self.update_queue_list)
        self.download_manager_worker.file_progress.connect(self.update_file_progress)
        self.download_manager_worker.moveToThread(self.download_manager_thread)
        self.download_manager_worker.log.connect(self.log)
        self.download_manager_worker.overall_progress.connect(self.overall_progress_bar.setValue)
        self.download_manager_thread.started.connect(self.download_manager_worker.process_queue)
        self.download_manager_worker.finished.connect(self.download_manager_thread.quit)
        self.download_manager_worker.finished.connect(self.download_manager_worker.deleteLater)
        self.download_manager_thread.finished.connect(self.download_manager_thread.deleteLater)
        self.download_manager_thread.start()

    def cancel_downloads(self):
        if self.download_manager_worker:
            self.download_manager_worker.cancel_all()
            self.log("Download annullati.")

    def show_completed_downloads(self):
        completed = self.download_manager_worker.completed_downloads if self.download_manager_worker else []
        msg = "\n".join(completed) if completed else "Nessun download completato."
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Download Precedenti", msg)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

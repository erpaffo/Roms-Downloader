import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from src.config import DOWNLOADS_FOLDER, RETROARCH_NAME
from src.utils import extract_nations  
class LibraryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Library - Giochi Installati")
        self.library_files = []   
        self.init_ui()
        self.load_library()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Pannello di controllo: ricerca, ordinamento e filtro per console
        control_layout = QHBoxLayout()
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Cerca gioco...")
        self.search_bar.textChanged.connect(self.update_table)
        control_layout.addWidget(QLabel("Cerca:"))
        control_layout.addWidget(self.search_bar)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Nome Asc", "Nome Desc", "Console Asc", "Console Desc"])
        self.sort_combo.currentIndexChanged.connect(self.update_table)
        control_layout.addWidget(QLabel("Ordina per:"))
        control_layout.addWidget(self.sort_combo)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Tutte", "3ds", "nds", "gba", "gb"])
        self.filter_combo.currentIndexChanged.connect(self.update_table)
        control_layout.addWidget(QLabel("Filtra per console:"))
        control_layout.addWidget(self.filter_combo)
        
        layout.addLayout(control_layout)
        
        # Tabella per mostrare i giochi
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Nome File", "Console"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self.launch_game)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #2e2e2e;
                color: #f0f0f0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
            }
            QLineEdit, QComboBox, QTableWidget {
                background-color: #3e3e3e;
                color: #f0f0f0;
                border: 1px solid #555;
            }
            QHeaderView::section {
                background-color: #3e3e3e;
                padding: 4px;
                border: 1px solid #666;
            }
        """)

    def load_library(self):
        """Scansiona ricorsivamente DOWNLOADS_FOLDER per trovare file di gioco."""
        self.library_files = []
        for root, dirs, files in os.walk(DOWNLOADS_FOLDER):
            for file in files:
                if file.lower().endswith((".3ds", ".nds", ".gba", ".gb")):
                    full_path = os.path.join(root, file)
                    norm_path = os.path.normpath(full_path)
                    parts = norm_path.split(os.sep)
                    download_folder = os.path.basename(DOWNLOADS_FOLDER)
                    console = "Unknown"
                    try:
                        idx = parts.index(download_folder)
                        if len(parts) > idx + 1:
                            console = parts[idx + 1]
                    except ValueError:
                        console = "Unknown"
                    self.library_files.append((file, console, full_path))
        self.update_table()

    def update_table(self):
        """Filtra, ordina e aggiorna la tabella in base ai controlli di ricerca."""
        search_text = self.search_bar.text().lower()
        sort_criteria = self.sort_combo.currentText()
        filter_console = self.filter_combo.currentText()
        
        # Filtraggio
        filtered = []
        for name, console, full_path in self.library_files:
            if search_text and search_text not in name.lower():
                continue
            if filter_console != "Tutte" and console.lower() != filter_console.lower():
                continue
            filtered.append((name, console, full_path))
        
        # Ordinamento
        reverse = False
        key_func = None
        if "Nome" in sort_criteria:
            key_func = lambda x: x[0].lower()
            reverse = "Desc" in sort_criteria
        elif "Console" in sort_criteria:
            key_func = lambda x: x[1].lower()
            reverse = "Desc" in sort_criteria
        if key_func:
            filtered.sort(key=key_func, reverse=reverse)
        
        self.table.setRowCount(0)
        for i, (name, console, full_path) in enumerate(filtered):
            self.table.insertRow(i)
            item_name = QTableWidgetItem(name)
            item_console = QTableWidgetItem(console)
            item_name.setData(Qt.UserRole, full_path)
            self.table.setItem(i, 0, item_name)
            self.table.setItem(i, 1, item_console)


    def launch_game(self, row, column):
        """
        Al doppio clic, lancia la ROM con RetroArch.
        """
        item = self.table.item(row, 0)
        full_path = item.data(Qt.UserRole)
        try:
            subprocess.Popen([RETROARCH_NAME, full_path])
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile avviare RetroArch: {e}")

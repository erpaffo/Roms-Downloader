import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt
from src.config import USER_DOWNLOADS_FOLDER, RETROARCH_NAME, settings, DEFAULT_DOWNLOADS_FOLDER
from src.utils import format_space

class LibraryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.library_files = []  # Lista dei percorsi dei giochi
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Barra superiore con titolo, label del percorso e pulsante Refresh
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Library - Giochi Scaricati"))
        
        self.current_folder_label = QLabel(f"Cartella: {USER_DOWNLOADS_FOLDER}")
        top_layout.addWidget(self.current_folder_label)
        
        self.refresh_library_btn = QPushButton("Refresh")
        self.refresh_library_btn.clicked.connect(self.refresh_library)
        top_layout.addWidget(self.refresh_library_btn)
        
        layout.addLayout(top_layout)
        
        # QTreeWidget per visualizzare i giochi raggruppati per cartella
        self.library_tree_widget = QTreeWidget()
        self.library_tree_widget.setHeaderLabels(["Nome Gioco", "Dimensione"])
        self.library_tree_widget.itemDoubleClicked.connect(self.launch_game_from_library)
        layout.addWidget(self.library_tree_widget)
        
        self.setLayout(layout)

    def load_library(self):
        current_folder = settings.value("download_folder", DEFAULT_DOWNLOADS_FOLDER)
        
        self.library_tree_widget.clear()
        self.library_files = []
        files_by_console = {}
        
        for root, dirs, files in os.walk(current_folder):
            for file in files:
                full_path = os.path.join(root, file)
                if not os.path.isfile(full_path):
                    continue
                self.library_files.append(full_path)
                
                relative_path = os.path.relpath(full_path, current_folder)
                parts = relative_path.split(os.sep)
                console = parts[0] if len(parts) > 1 else "Root"
                
                if console not in files_by_console:
                    files_by_console[console] = []
                size = os.path.getsize(full_path)
                files_by_console[console].append((file, size, full_path))
        
        if not files_by_console:
            self.library_tree_widget.addTopLevelItem(QTreeWidgetItem(["Nessun gioco trovato"]))
        else:
            for console, games in files_by_console.items():
                top_item = QTreeWidgetItem([console])
                for game_name, size, full_path in games:
                    size_str = format_space(size)
                    child_item = QTreeWidgetItem([game_name, size_str])
                    child_item.setData(0, Qt.UserRole, full_path)
                    top_item.addChild(child_item)
                self.library_tree_widget.addTopLevelItem(top_item)

    def refresh_library(self):
        """Aggiorna la label della cartella e ricarica la libreria."""
        self.current_folder_label.setText(f"Cartella: {USER_DOWNLOADS_FOLDER}")
        self.load_library()

    def launch_game_from_library(self, item, column):
        """
        Se l'item selezionato è un file (foglia), lancia RetroArch con il percorso della ROM.
        """
        if item.childCount() > 0:
            return
        file_path = item.data(0, Qt.UserRole)
        try:
            subprocess.Popen([RETROARCH_NAME, file_path])
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile avviare RetroArch: {e}")

import os
import subprocess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox
from PySide6.QtCore import Qt
from src.config import RETROARCH_NAME, CORES_FOLDER, DEFAULT_CORES
from src.utils import format_space, find_retroarch

class LibraryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.library_files = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Barra superiore: titolo, percorso e pulsante Refresh
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Library - Giochi Scaricati"))
        from src.config import USER_DOWNLOADS_FOLDER
        self.current_folder_label = QLabel(f"Cartella: {USER_DOWNLOADS_FOLDER}")
        top_layout.addWidget(self.current_folder_label)
        self.refresh_library_btn = QPushButton("Refresh")
        self.refresh_library_btn.clicked.connect(self.refresh_library)
        top_layout.addWidget(self.refresh_library_btn)
        layout.addLayout(top_layout)
        
        # QTreeWidget per visualizzare la libreria
        self.library_tree_widget = QTreeWidget()
        self.library_tree_widget.setHeaderLabels(["Nome Gioco", "Dimensione"])
        self.library_tree_widget.itemDoubleClicked.connect(self.launch_game_from_library)
        layout.addWidget(self.library_tree_widget)
        
        self.setLayout(layout)

    def load_library(self):
        from src.config import settings, DEFAULT_DOWNLOADS_FOLDER
        current_folder = settings.value("download_folder", DEFAULT_DOWNLOADS_FOLDER)
        self.current_folder_label.setText(f"Cartella: {current_folder}")
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
                    if game_name.endswith(".i64"):
                        continue
                    size_str = format_space(size)
                    child_item = QTreeWidgetItem([game_name, size_str])
                    child_item.setData(0, Qt.UserRole, full_path)
                    top_item.addChild(child_item)
                self.library_tree_widget.addTopLevelItem(top_item)

    def refresh_library(self):
        self.load_library()

    def launch_game_from_library(self, item, column):
        """
        Al doppio clic su una ROM (foglia) lancia RetroArch con il core appropriato 
        e la configurazione personalizzata.
        Se RetroArch non è installato o il core non viene trovato, notifica l'utente.
        """
        if item.childCount() > 0:
            return
        rom_path = item.data(0, Qt.UserRole)
        parent_item = item.parent()
        if parent_item:
            console_name = parent_item.text(0)
        else:
            console_name = "Root"

        # Cerca l'eseguibile di RetroArch
        retroarch_exe = find_retroarch()
        if not retroarch_exe:
            QMessageBox.critical(self, "Errore", "RetroArch non è installato. È necessario installarlo per avviare le ROM.")
            return

        # Usa DEFAULT_CORES per ottenere il nome del core
        from src.config import DEFAULT_CORES, CORES_FOLDER
        core_filename = DEFAULT_CORES.get(console_name)
        if not core_filename:
            QMessageBox.critical(self, "Errore", f"Nessun core configurato per la console '{console_name}'.")
            return

        core_path = os.path.join(CORES_FOLDER, core_filename)
        if not os.path.exists(core_path):
            QMessageBox.critical(self, "Errore", f"Il core per '{console_name}' non è stato trovato in '{CORES_FOLDER}'.")
            return

        # Costruisci il percorso del file di configurazione personalizzato
        config_folder = os.path.join("emulator", "config")
        config_filename = core_filename + ".cfg"
        config_path = os.path.join(config_folder, config_filename)
        
        # Se il file di configurazione esiste, aggiungi l'opzione --config
        if os.path.exists(config_path):
            command = [retroarch_exe, "--config", config_path, "-L", core_path, rom_path]
        else:
            command = [retroarch_exe, "-L", core_path, rom_path]

        try:
            print("Lancio comando:", command)  # Debug
            subprocess.Popen(command)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile avviare RetroArch: {e}")

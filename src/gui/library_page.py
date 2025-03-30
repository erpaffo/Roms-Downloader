import os
import subprocess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QHeaderView ,QTreeWidgetItem, QMessageBox
from PySide6.QtCore import Qt
from src.utils import download_and_extract_core, format_space, find_retroarch, download_and_install_retroarch
from src.config import USER_DOWNLOADS_FOLDER, settings, DEFAULT_DOWNLOADS_FOLDER, CORES_FOLDER, DEFAULT_CORES, CORE_EXT

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

        self.current_folder_label = QLabel(f"Cartella: {USER_DOWNLOADS_FOLDER}")
        top_layout.addWidget(self.current_folder_label)
        self.refresh_library_btn = QPushButton("Refresh")
        self.refresh_library_btn.clicked.connect(self.refresh_library)
        top_layout.addWidget(self.refresh_library_btn)
        layout.addLayout(top_layout)
        
        # QTreeWidget per visualizzare la libreria
        self.library_tree_widget = QTreeWidget()
        self.library_tree_widget.setHeaderLabels(["Nome Gioco", "Dimensione"])
        self.library_tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.library_tree_widget.itemDoubleClicked.connect(self.launch_game_from_library)
        layout.addWidget(self.library_tree_widget)
        
        self.setLayout(layout)

    def load_library(self):
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
        if item.childCount() > 0:
            return
        rom_path = item.data(0, Qt.UserRole)
        parent_item = item.parent()
        console_name = parent_item.text(0) if parent_item else "Root"

        # 1. Verifica RetroArch
        retroarch_exe = find_retroarch()
        if not retroarch_exe:
            QMessageBox.critical(self, "Errore", "RetroArch non è installato. Visita https://www.retroarch.com/ per scaricarlo.")
            return

        # 2. Verifica che il core per la console esista.
        core_base = DEFAULT_CORES.get(console_name)
        if not core_base:
            QMessageBox.critical(self, "Errore", f"Nessun core configurato per la console '{console_name}'.")
            return

        core_filename = core_base + CORE_EXT
        core_path = os.path.join(CORES_FOLDER, core_filename)
        if not os.path.exists(core_path):
            # Se non esiste, prova a scaricarlo ed estrarlo
            self.parent().log(f"Core per '{console_name}' non trovato. Scaricamento in corso...")
            core_path = download_and_extract_core(core_base)
            if not core_path:
                QMessageBox.critical(self, "Errore", f"Impossibile scaricare il core per '{console_name}'.")
                return

        # 3. Costruisci il comando per avviare RetroArch
        config_folder = os.path.join("emulator", "config")
        config_filename = core_base + ".cfg"
        config_path = os.path.join(config_folder, config_filename)
        if os.path.exists(config_path):
            command = [retroarch_exe, "--config", config_path, "-L", core_path, rom_path]
        else:
            command = [retroarch_exe, "-L", core_path, rom_path]

        try:
            print("Lancio comando:", command)  # Debug
            subprocess.Popen(command)
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile avviare RetroArch: {e}")
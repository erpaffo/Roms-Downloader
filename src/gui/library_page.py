import os
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTreeWidget, QHeaderView,
                               QTreeWidgetItem, QMessageBox)
from PySide6.QtCore import Qt
from PySide6 import QtGui
from src.utils import format_space, find_retroarch
from src.config import (USER_DOWNLOADS_FOLDER, settings, DEFAULT_DOWNLOADS_FOLDER,
                        CORES_FOLDER, DEFAULT_CORES, CORE_EXT,
                        EMULATOR_CONFIG_FOLDER)
import logging

class LibraryPage(QWidget):
    """
    Page widget displaying the user's downloaded game library,
    grouped by console, allowing games to be launched.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.library_files = []
        self.init_ui()
        self.load_library()

    def init_ui(self):
        """Initializes the user interface of the Library page."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top_layout = QHBoxLayout()
        title_label = QLabel("Libreria - Giochi Scaricati")
        title_font = title_label.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        top_layout.addWidget(title_label)
        top_layout.addStretch()

        self.current_folder_label = QLabel(f"Cartella: {USER_DOWNLOADS_FOLDER}")
        top_layout.addWidget(self.current_folder_label)

        self.refresh_library_btn = QPushButton("Aggiorna")
        self.refresh_library_btn.setObjectName("RefreshButton")
        self.refresh_library_btn.clicked.connect(self.refresh_library)
        top_layout.addWidget(self.refresh_library_btn)
        layout.addLayout(top_layout)

        self.library_tree_widget = QTreeWidget()
        self.library_tree_widget.setObjectName("LibraryTree")
        self.library_tree_widget.setHeaderLabels(["Nome Gioco/Console", "Dimensione"])

        header = self.library_tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        self.library_tree_widget.itemDoubleClicked.connect(self.launch_game_from_library)

        self.library_tree_widget.setAlternatingRowColors(True)
        self.library_tree_widget.setRootIsDecorated(True)
        self.library_tree_widget.setUniformRowHeights(True)
        self.library_tree_widget.setSortingEnabled(False)

        layout.addWidget(self.library_tree_widget)

    def load_library(self):
        """Loads/Refreshes games from the download folder into the TreeWidget."""
        current_folder = settings.value("download_folder", DEFAULT_DOWNLOADS_FOLDER)
        self.current_folder_label.setText(f"Cartella: {current_folder}")

        self.library_tree_widget.clear()
        self.library_files = []
        files_by_console = {}

        try:
            if not os.path.isdir(current_folder):
                 self.library_tree_widget.addTopLevelItem(QTreeWidgetItem([f"Errore: Cartella non trovata '{current_folder}'"]))
                 logging.error(f"Library folder not found: {current_folder}")
                 return

            for root, dirs, files in os.walk(current_folder):
                for file in files:
                    full_path = os.path.join(root, file)
                    if not os.path.isfile(full_path):
                        continue

                    self.library_files.append(full_path)
                    relative_path = os.path.relpath(full_path, current_folder)
                    parts = relative_path.split(os.sep)
                    console = parts[0] if len(parts) > 1 else "Generale"

                    if console not in files_by_console:
                        files_by_console[console] = []

                    try:
                        size = os.path.getsize(full_path)
                        files_by_console[console].append((file, size, full_path))
                    except OSError as e:
                        logging.warning(f"Could not get size for {full_path}: {e}")
                        continue

        except Exception as e:
             error_msg = f"Errore durante la scansione della libreria: {e}"
             self.library_tree_widget.addTopLevelItem(QTreeWidgetItem([error_msg]))
             logging.exception(error_msg) # Logga anche il traceback
             return

        if not files_by_console:
            self.library_tree_widget.addTopLevelItem(QTreeWidgetItem(["Nessun gioco trovato"]))
        else:
            sorted_consoles = sorted(files_by_console.keys())
            for console in sorted_consoles:
                games = files_by_console[console]
                top_item = QTreeWidgetItem([console])

                font = top_item.font(0)
                font.setBold(True)
                top_item.setFont(0, font)

                sorted_games = sorted(games, key=lambda x: x[0])
                for game_name, size, full_path in sorted_games:
                    size_str = format_space(size)
                    child_item = QTreeWidgetItem([game_name, size_str])
                    child_item.setData(0, Qt.ItemDataRole.UserRole, full_path)
                    child_item.setToolTip(0, f"Percorso: {full_path}")
                    child_item.setToolTip(1, f"Byte: {size:,}")
                    top_item.addChild(child_item)

                self.library_tree_widget.addTopLevelItem(top_item)

            self.library_tree_widget.resizeColumnToContents(1)

    def refresh_library(self):
        """Action for the Refresh button: reloads the library."""
        self.load_library()

    def launch_game_from_library(self, item: QTreeWidgetItem, column: int):
        """Launches the selected game using RetroArch on double-click."""
        if item.childCount() > 0 or not item.data(0, Qt.ItemDataRole.UserRole):
            return

        rom_path = item.data(0, Qt.ItemDataRole.UserRole)
        parent_item = item.parent()
        console_name = parent_item.text(0) if parent_item else "Generale"

        retroarch_exe = find_retroarch()
        if not retroarch_exe:
            QMessageBox.critical(self, "Errore Avvio",
                                 "Eseguibile di RetroArch non trovato.\n"
                                 "Assicurati che sia installato e nel PATH di sistema, "
                                 "oppure che il percorso sia corretto in 'src/config.py'.")
            return

        core_base = DEFAULT_CORES.get(console_name)
        if not core_base:
            QMessageBox.warning(self, "Core Mancante",
                                f"Nessun core predefinito trovato per la console '{console_name}'.\n"
                                "Controlla la configurazione in 'src/config.py' (DEFAULT_CORES).")
            return

        core_filename = core_base + CORE_EXT
        core_path = os.path.join(CORES_FOLDER, core_filename)
        if not os.path.exists(core_path):
            QMessageBox.critical(self, "Errore Core",
                                 f"File del core non trovato per '{console_name}'.\n"
                                 f"Percorso atteso: {core_path}\n"
                                 "Assicurati che il core sia presente nella cartella 'cores'.")
            return

        config_filename = core_base + ".cfg"
        config_path = os.path.join(EMULATOR_CONFIG_FOLDER, config_filename)

        command = [retroarch_exe]
        if os.path.exists(config_path):
            command.extend(["--config", config_path])
            logging.info(f"Using core-specific config file: {config_path}")
        else:
            global_config_path = os.path.join(EMULATOR_CONFIG_FOLDER, "retroarch_global.cfg")
            if os.path.exists(global_config_path):
                 command.extend(["--config", global_config_path])
                 logging.info(f"Using global config file: {global_config_path}")

        command.extend(["-L", core_path, rom_path])

        try:
            logging.info(f"Launching command: {' '.join(command)}")
            subprocess.Popen(command)
        except OSError as e:
            logging.error(f"Failed to execute command: {' '.join(command)}. Error: {e}")
            QMessageBox.critical(self, "Errore Avvio Sistema",
                                 f"Impossibile eseguire il comando:\n{' '.join(command)}\n"
                                 f"Errore di sistema: {e}")
        except Exception as e:
            logging.exception(f"Unexpected error launching RetroArch: {e}")
            QMessageBox.critical(self, "Errore Imprevisto",
                                 f"Errore imprevisto durante l'avvio di RetroArch:\n{e}")
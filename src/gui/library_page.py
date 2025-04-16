import os
import subprocess
import logging
from datetime import datetime, timezone
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTreeWidget, QHeaderView,
                               QTreeWidgetItem, QMessageBox, QApplication, QDialog)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap

from src.utils import create_default_core_config, find_retroarch, clean_rom_title
from src.config import (settings, DEFAULT_DOWNLOADS_FOLDER, USER_DOWNLOADS_FOLDER,
                        CORES_FOLDER, DEFAULT_CORES, CORE_EXT,
                        EMULATOR_CONFIG_FOLDER)
from src.scraping import fetch_game_details
from src.metadata_manager import (load_metadata, save_metadata, download_cover,
                                  create_placeholder_metadata, delete_metadata_and_cover)
from src.gui.game_info_dialog import GameInfoDialog

class LibraryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.library_files = []
        self.library_data = {}
        self.init_ui()
        self.load_library()

    def init_ui(self):
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

        self.current_folder_label = QLabel(f"Cartella: {settings.value('download_folder', DEFAULT_DOWNLOADS_FOLDER)}")
        top_layout.addWidget(self.current_folder_label)

        self.refresh_library_btn = QPushButton(QIcon.fromTheme("view-refresh"), " Aggiorna Libreria")
        self.refresh_library_btn.setObjectName("RefreshButton")
        self.refresh_library_btn.setToolTip("Ricarica i giochi dalla cartella e aggiorna i metadati se necessario.")
        self.refresh_library_btn.clicked.connect(self.refresh_library)
        top_layout.addWidget(self.refresh_library_btn)
        layout.addLayout(top_layout)

        self.library_tree_widget = QTreeWidget()
        self.library_tree_widget.setObjectName("LibraryTree")
        self.library_tree_widget.setHeaderLabels(["Copertina", "Titolo", "Data Uscita", "Azioni"])

        header = self.library_tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.library_tree_widget.setIndentation(20)

        self.library_tree_widget.setIconSize(QSize(64, 64))

        self.library_tree_widget.itemClicked.connect(self.show_game_info)

        self.library_tree_widget.setAlternatingRowColors(True)
        self.library_tree_widget.setRootIsDecorated(True)
        self.library_tree_widget.setUniformRowHeights(False)
        self.library_tree_widget.setSortingEnabled(False)

        layout.addWidget(self.library_tree_widget)

    def load_library(self):
        logging.info("Caricamento libreria e metadati iniziato...")
        current_folder = settings.value("download_folder", DEFAULT_DOWNLOADS_FOLDER)
        self.current_folder_label.setText(f"Cartella: {current_folder}")

        self.library_tree_widget.clear()
        self.library_files.clear()
        self.library_data.clear()
        files_by_console_temp = {}

        try:
            if not os.path.isdir(current_folder):
                error_item = QTreeWidgetItem([f"Errore: Cartella libreria non trovata"])
                error_item.setToolTip(0, current_folder)
                error_item.setForeground(0, Qt.GlobalColor.red)
                self.library_tree_widget.addTopLevelItem(error_item)
                logging.error(f"Cartella libreria non trovata: {current_folder}")
                return

            logging.debug(f"Scansione cartella: {current_folder}")

            for root, dirs, files in os.walk(current_folder):
                relative_path_to_root = os.path.relpath(root, current_folder)
                console_name = relative_path_to_root.split(os.sep)[0] if relative_path_to_root != '.' else "Generale"

                if console_name not in files_by_console_temp:
                     files_by_console_temp[console_name] = []

                for file in files:
                    if file.startswith('.'): continue

                    full_path = os.path.join(root, file)
                    if not os.path.isfile(full_path): continue

                    self.library_files.append(full_path)

                    game_data = load_metadata(full_path)

                    if not game_data:
                        logging.info(f"Metadati mancanti per '{file}'. Tentativo di scraping/creazione...")

                        scraped_api_data = fetch_game_details(os.path.basename(full_path), console_name)
                        game_data = create_placeholder_metadata(full_path, console_name)

                        if scraped_api_data:
                            logging.debug(f"Dati API trovati per {file}: {scraped_api_data.get('api_title')}")
                            if scraped_api_data.get('api_title') and scraped_api_data.get('api_title') != game_data['title']:
                                game_data['title'] = scraped_api_data['api_title']
                            game_data['description'] = scraped_api_data.get('description', game_data['description'])
                            game_data['release_date'] = scraped_api_data.get('release_date', game_data['release_date'])
                            game_data['genres'] = scraped_api_data.get('genres', game_data['genres'])
                            game_data['languages'] = scraped_api_data.get('languages', game_data['languages'])
                            game_data['scrape_success'] = True

                            cover_url = scraped_api_data.get('cover_url')
                            if cover_url:
                                local_cover_path = download_cover(cover_url, full_path)
                                if local_cover_path:
                                    game_data['cover_path'] = local_cover_path
                                else:
                                    logging.warning(f"Download copertina fallito per {file} da {cover_url}")
                        else:
                            logging.info(f"Nessun dato API trovato per {file}, creato placeholder.")

                        if not save_metadata(full_path, game_data):
                             logging.error(f"Salvataggio metadati fallito per {file}")
                    else:
                        if game_data.get('rom_path') != full_path:
                            logging.info(f"Percorso ROM cambiato per {file}, aggiorno metadati.")
                            game_data['rom_path'] = full_path
                            save_metadata(full_path, game_data)
                        else:
                             logging.debug(f"Metadati caricati per '{file}'")

                    if game_data:
                        files_by_console_temp[console_name].append(game_data)

        except Exception as e:
             error_msg = f"Errore grave durante scansione/gestione metadati: {e}"
             error_item = QTreeWidgetItem([error_msg])
             error_item.setForeground(0, Qt.GlobalColor.red)
             self.library_tree_widget.addTopLevelItem(error_item)
             logging.exception(error_msg)
             return

        self.library_data = files_by_console_temp
        if not self.library_data:
            self.library_tree_widget.addTopLevelItem(QTreeWidgetItem(["Nessun gioco trovato."]))
        else:
            sorted_consoles = sorted(self.library_data.keys())
            for console in sorted_consoles:
                games_metadata = self.library_data[console]
                if not games_metadata: continue

                top_item = QTreeWidgetItem([console])
                font = top_item.font(0)
                font.setBold(True)
                top_item.setFont(0, font)
                self.library_tree_widget.addTopLevelItem(top_item)

                sorted_games = sorted(games_metadata, key=lambda x: x.get('title', '').lower())

                for game_data in sorted_games:
                    child_item = QTreeWidgetItem(top_item)

                    cover_path = game_data.get('cover_path')
                    icon = QIcon()
                    if cover_path and os.path.exists(cover_path):
                        loaded_pixmap = QPixmap(cover_path)
                        if not loaded_pixmap.isNull():
                            icon = QIcon(loaded_pixmap)
                        else:
                            logging.warning(f"Impossibile caricare pixmap copertina: {cover_path}")

                    child_item.setIcon(0, icon)
                    child_item.setSizeHint(0, QSize(68, 68))

                    title_text = game_data.get('title', 'Titolo Sconosciuto')
                    child_item.setText(1, title_text)
                    child_item.setData(1, Qt.ItemDataRole.UserRole, game_data)
                    tooltip_text = f"Console: {game_data.get('console', 'N/D')}\n" \
                                   f"File: {game_data.get('original_filename', 'N/D')}\n" \
                                   f"Percorso: {game_data.get('rom_path')}"
                    child_item.setToolTip(1, tooltip_text)

                    child_item.setText(2, game_data.get('release_date', 'N/D'))

                    action_widget = QWidget()
                    action_layout = QHBoxLayout(action_widget)
                    action_layout.setContentsMargins(2, 2, 2, 2)
                    action_layout.setSpacing(5)

                    launch_button = QPushButton(QIcon.fromTheme("media-playback-start"), "Avvia")
                    launch_button.setProperty("rom_path", game_data.get('rom_path'))
                    launch_button.setProperty("console_name", game_data.get('console'))
                    launch_button.clicked.connect(self.handle_launch_button)
                    action_layout.addWidget(launch_button)
                    action_layout.addStretch()

                    self.library_tree_widget.setItemWidget(child_item, 3, action_widget)

        logging.info("Caricamento libreria e popolamento UI completato.")

    def refresh_library(self):
        logging.info("Richiesta di aggiornamento libreria...")
        self.load_library()

    def handle_launch_button(self):
        sender_button = self.sender()
        if not sender_button:
            return

        rom_path = sender_button.property("rom_path")
        console_name = sender_button.property("console_name")

        if not rom_path or not console_name:
             logging.error("Proprietà mancanti (rom_path/console_name) nel pulsante Avvia.")
             QMessageBox.critical(self, "Errore Avvio", "Impossibile ottenere le informazioni necessarie per avviare.")
             return

        logging.info(f"Avvio richiesto per: {os.path.basename(rom_path)} ({console_name})")
        self.launch_game_logic(rom_path, console_name)

    def launch_game_logic(self, rom_path, console_name):
        retroarch_exe = find_retroarch()
        if not retroarch_exe:
            QMessageBox.critical(self, "Errore Avvio", "Eseguibile di RetroArch non trovato.\nVerifica l'installazione.")
            return

        core_base = DEFAULT_CORES.get(console_name)
        if not core_base:
            QMessageBox.warning(self, "Core Mancante", f"Nessun core predefinito trovato per '{console_name}'.")
            return

        core_filename = core_base + CORE_EXT
        core_path = os.path.join(CORES_FOLDER, core_filename)
        if not os.path.exists(core_path):
            QMessageBox.critical(self, "Errore Core", f"File del core non trovato:\n{core_path}")
            return

        core_config_filename = core_base + ".cfg"
        core_config_path = os.path.join(EMULATOR_CONFIG_FOLDER, core_config_filename)

        config_created_or_exists = True
        if not os.path.exists(core_config_path):
            logging.info(f"File config '{core_config_filename}' non trovato. Tentativo creazione default...")
            if not create_default_core_config(core_config_path, console_name, core_base):
                QMessageBox.warning(self, "Errore Creazione Config", f"Impossibile creare config predefinito:\n{core_config_path}")
                core_config_path = None
                config_created_or_exists = False
            else:
                logging.info(f"File config default creato: {core_config_path}")

        command_list = [retroarch_exe]
        if config_created_or_exists and core_config_path and os.path.exists(core_config_path):
            command_list.extend(["--config", core_config_path])
            logging.info(f"Uso config specifico: {core_config_path}")
        else:
            logging.warning(f"Avvio senza config specifico per {console_name}.")

        command_list.extend(["-L", core_path, rom_path, "-v"])

        try:
            logging.info(f"Esecuzione comando: {' '.join(command_list)}")
            process = subprocess.Popen(command_list,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding='utf-8', errors='replace')
            try:
                stdout, stderr = process.communicate(timeout=1)
                if stdout: logging.debug(f"RA stdout(1s): {stdout[:200]}...")
                if stderr: logging.warning(f"RA stderr(1s): {stderr[:200]}...")
            except subprocess.TimeoutExpired:
                 logging.info(f"RetroArch avviato (PID: {process.pid}), continua in background.")
            except Exception as comm_err:
                 logging.error(f"Errore comunicazione con processo RA: {comm_err}")

        except OSError as e:
            logging.error(f"OSError Avvio RA: {e} (Comando: {' '.join(command_list)})")
            QMessageBox.critical(self, "Errore Avvio Sistema", f"Impossibile eseguire RetroArch:\n{e}")
        except Exception as e:
            logging.exception(f"Errore imprevisto Avvio RA:")
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore avvio RetroArch:\n{e}")

    def show_game_info(self, item: QTreeWidgetItem, column: int):
        if not item or item.childCount() > 0 or column == 3:
            return

        game_data = item.data(1, Qt.ItemDataRole.UserRole)

        if isinstance(game_data, dict) and 'rom_path' in game_data:
            logging.debug(f"Apertura dettagli per: {game_data.get('title')}")
            dialog = GameInfoDialog(game_data, self)

            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                updated_data = dialog.get_updated_data()
                if updated_data is None:
                    logging.info(f"Gioco '{game_data.get('title')}' eliminato via dialogo.")
                    (item.parent() or self.library_tree_widget.invisibleRootItem()).removeChild(item)
                    console = game_data.get('console')
                    rom_path = game_data.get('rom_path')
                    if console and rom_path:
                         if console in self.library_data:
                             self.library_data[console] = [g for g in self.library_data[console] if g.get('rom_path') != rom_path]
                         if rom_path in self.library_files:
                             self.library_files.remove(rom_path)
                else:
                    logging.info(f"Metadati per '{updated_data.get('title')}' aggiornati via dialogo.")
                    self.update_library_item(item, updated_data)
                    console = updated_data.get('console')
                    rom_path = updated_data.get('rom_path')
                    if console and rom_path and console in self.library_data:
                         for i, g_data in enumerate(self.library_data[console]):
                             if g_data.get('rom_path') == rom_path:
                                 self.library_data[console][i] = updated_data
                                 break
        else:
            logging.warning(f"Nessun dato dizionario valido associato all'item cliccato: {item.text(1)}")

    def update_library_item(self, item: QTreeWidgetItem, data: dict):
        if not item or not data: return

        cover_path = data.get('cover_path')
        icon = QIcon()
        if cover_path and os.path.exists(cover_path):
            loaded_pixmap = QPixmap(cover_path)
            if not loaded_pixmap.isNull():
                icon = QIcon(loaded_pixmap)
            else:
                logging.warning(f"Impossibile caricare icona da: {cover_path}")
        item.setIcon(0, icon)

        item.setText(1, data.get('title', 'Titolo Sconosciuto'))
        item.setText(2, data.get('release_date', 'N/D'))
        item.setData(1, Qt.ItemDataRole.UserRole, data)
        tooltip_text = f"Console: {data.get('console', 'N/D')}\n" \
                       f"File: {data.get('original_filename', 'N/D')}\n" \
                       f"Percorso: {data.get('rom_path')}"
        item.setToolTip(1, tooltip_text)
        logging.debug(f"Item '{data.get('title')}' aggiornato visivamente nell'albero.")

    def find_console_for_rom(self, rom_path):
         if not self.library_data: return None
         for console, game_list in self.library_data.items():
             for game_data in game_list:
                 if game_data.get('rom_path') == rom_path:
                     return console
         logging.warning(f"Console non trovata per rom_path (find_console_for_rom): {rom_path}")
         return None
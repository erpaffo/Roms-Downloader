import os
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTreeWidget, QHeaderView,
                               QTreeWidgetItem, QMessageBox)
from PySide6.QtCore import Qt
from PySide6 import QtGui # Import necessario per QFont
from src.utils import format_space, find_retroarch
from src.config import (USER_DOWNLOADS_FOLDER, settings, DEFAULT_DOWNLOADS_FOLDER,
                        CORES_FOLDER, DEFAULT_CORES, CORE_EXT,
                        EMULATOR_CONFIG_FOLDER)

class LibraryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.library_files = [] # Mantiene la lista dei percorsi completi dei file trovati
        self.init_ui()
        # Carica la libreria all'inizio invece di aspettare il refresh manuale
        self.load_library()

    def init_ui(self):
        """Inizializza l'interfaccia utente della pagina Libreria."""
        # Applica il layout direttamente alla pagina
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10) # Margini interni per spaziatura
        layout.setSpacing(10) # Spaziatura tra elementi

        # --- Barra Superiore ---
        top_layout = QHBoxLayout()
        title_label = QLabel("Libreria - Giochi Scaricati")
        # Rendi il titolo più evidente
        title_font = title_label.font()
        title_font.setPointSize(12) # Dimensione leggermente maggiore
        title_font.setBold(True)    # Grassetto
        title_label.setFont(title_font)
        top_layout.addWidget(title_label)
        top_layout.addStretch() # Spinge gli elementi successivi a destra

        # Etichetta per mostrare la cartella corrente
        self.current_folder_label = QLabel(f"Cartella: {USER_DOWNLOADS_FOLDER}")
        top_layout.addWidget(self.current_folder_label)

        # Pulsante per aggiornare la libreria
        self.refresh_library_btn = QPushButton("Aggiorna") # Testo comune
        self.refresh_library_btn.setObjectName("RefreshButton") # Nome oggetto per QSS
        self.refresh_library_btn.clicked.connect(self.refresh_library) # Connessione al metodo
        top_layout.addWidget(self.refresh_library_btn)
        layout.addLayout(top_layout)

        # --- Tree Widget per la Libreria ---
        self.library_tree_widget = QTreeWidget()
        self.library_tree_widget.setObjectName("LibraryTree") # Nome oggetto per QSS
        self.library_tree_widget.setHeaderLabels(["Nome Gioco/Console", "Dimensione"]) # Intestazioni colonne

        # Configurazione Header
        header = self.library_tree_widget.header()
        # Colonna 0 (Nome): Si espande per riempire lo spazio disponibile
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        # Colonna 1 (Dimensione): Si adatta al contenuto
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        # Connessione doppio click per avviare gioco
        self.library_tree_widget.itemDoubleClicked.connect(self.launch_game_from_library)

        # Miglioramenti Visivi TreeWidget
        self.library_tree_widget.setAlternatingRowColors(True) # Righe con colori alternati
        self.library_tree_widget.setRootIsDecorated(True) # Mostra frecce espandi/collassa
        self.library_tree_widget.setUniformRowHeights(True) # Migliora prestazioni (se possibile)
        self.library_tree_widget.setSortingEnabled(False) # Disabilita ordinamento cliccando header (lo facciamo in codice)

        layout.addWidget(self.library_tree_widget)

        # Nota: Non serve self.setLayout(layout) perché è passato a QVBoxLayout(self)

    def load_library(self):
        """Carica/Aggiorna i giochi dalla cartella dei download nel TreeWidget."""
        # Ottieni la cartella dei download corrente dalle impostazioni
        current_folder = settings.value("download_folder", DEFAULT_DOWNLOADS_FOLDER)
        self.current_folder_label.setText(f"Cartella: {current_folder}") # Aggiorna etichetta

        # Pulisci la vista precedente e la lista interna
        self.library_tree_widget.clear()
        self.library_files = []
        files_by_console = {} # Dizionario per raggruppare: {nome_console: [(nome_file, size, path), ...]}

        # Scansiona ricorsivamente la cartella dei download
        try:
            if not os.path.isdir(current_folder):
                 self.library_tree_widget.addTopLevelItem(QTreeWidgetItem([f"Errore: Cartella non trovata '{current_folder}'"]))
                 return

            for root, dirs, files in os.walk(current_folder):
                for file in files:
                    full_path = os.path.join(root, file)
                    # Ignora se non è un file
                    if not os.path.isfile(full_path):
                        continue

                    # Aggiungi alla lista generale dei file trovati
                    self.library_files.append(full_path)

                    # Determina la console (nome della prima sottocartella)
                    relative_path = os.path.relpath(full_path, current_folder)
                    parts = relative_path.split(os.sep)
                    console = parts[0] if len(parts) > 1 else "Generale" # Usa "Generale" se nella root

                    # Inizializza la lista per la console se non esiste
                    if console not in files_by_console:
                        files_by_console[console] = []

                    # Ottieni dimensione e aggiungi alla lista della console
                    try:
                        size = os.path.getsize(full_path)
                        files_by_console[console].append((file, size, full_path))
                    except OSError:
                        # Ignora file se non si può ottenere la dimensione
                        continue

        except Exception as e:
             self.library_tree_widget.addTopLevelItem(QTreeWidgetItem([f"Errore durante la scansione: {e}"]))
             return

        # Popola il TreeWidget
        if not files_by_console:
            self.library_tree_widget.addTopLevelItem(QTreeWidgetItem(["Nessun gioco trovato"]))
        else:
            # Ordina le console alfabeticamente per nome
            sorted_consoles = sorted(files_by_console.keys())

            for console in sorted_consoles:
                games = files_by_console[console]
                # Crea l'elemento principale per la console
                top_item = QTreeWidgetItem([console]) # Mostra solo il nome nella prima colonna

                # Rendi il nome della console in grassetto
                font = top_item.font(0)
                font.setBold(True)
                top_item.setFont(0, font)
                # (Opzionale: Aggiungi icona per la console qui se hai le icone)
                # top_item.setIcon(0, QIcon(f"path/to/icons/{console}.png"))

                # Ordina i giochi all'interno della console per nome file
                sorted_games = sorted(games, key=lambda x: x[0])

                # Aggiungi i giochi come figli dell'elemento console
                for game_name, size, full_path in sorted_games:
                    # Formatta la dimensione in modo leggibile
                    size_str = format_space(size)
                    # Crea l'elemento figlio per il gioco
                    child_item = QTreeWidgetItem([game_name, size_str])
                    # Salva il percorso completo nei dati dell'item per usarlo al doppio click
                    child_item.setData(0, Qt.ItemDataRole.UserRole, full_path)
                    # Aggiungi tooltip utili
                    child_item.setToolTip(0, f"Percorso: {full_path}")
                    child_item.setToolTip(1, f"Byte: {size:,}") # Mostra byte con separatore migliaia
                    # Aggiungi il gioco come figlio della console
                    top_item.addChild(child_item)

                # Aggiungi l'elemento console (con i suoi giochi) al TreeWidget
                self.library_tree_widget.addTopLevelItem(top_item)
                # (Opzionale: Espandi tutti gli elementi all'inizio)
                # top_item.setExpanded(True)

            # Adatta la colonna della dimensione al contenuto dopo aver aggiunto tutto
            self.library_tree_widget.resizeColumnToContents(1)

    def refresh_library(self):
        """Azione del pulsante Refresh: ricarica la libreria."""
        self.load_library()

    def launch_game_from_library(self, item: QTreeWidgetItem, column: int):
        """Avvia il gioco selezionato con RetroArch al doppio click."""
        # Ignora il click se non è su un gioco (cioè se ha figli o non ha dati utente)
        if item.childCount() > 0 or not item.data(0, Qt.ItemDataRole.UserRole):
            return

        rom_path = item.data(0, Qt.ItemDataRole.UserRole)
        parent_item = item.parent()
        # Ottieni il nome della console dal testo dell'elemento padre
        console_name = parent_item.text(0) if parent_item else "Generale" # Usa "Generale" se non ha padre

        # --- Verifica Prerequisiti ---
        # 1. Trova l'eseguibile di RetroArch
        retroarch_exe = find_retroarch()
        if not retroarch_exe:
            QMessageBox.critical(self, "Errore Avvio",
                                 "Eseguibile di RetroArch non trovato.\n"
                                 "Assicurati che sia installato e nel PATH di sistema, "
                                 "oppure che il percorso sia corretto in 'src/config.py'.")
            return

        # 2. Trova il core associato alla console
        core_base = DEFAULT_CORES.get(console_name)
        if not core_base:
            QMessageBox.warning(self, "Core Mancante",
                                f"Nessun core predefinito trovato per la console '{console_name}'.\n"
                                "Controlla la configurazione in 'src/config.py' (DEFAULT_CORES).")
            return

        # 3. Verifica l'esistenza del file del core
        core_filename = core_base + CORE_EXT # Aggiunge l'estensione corretta (.dll, .so, ...)
        core_path = os.path.join(CORES_FOLDER, core_filename)
        if not os.path.exists(core_path):
            QMessageBox.critical(self, "Errore Core",
                                 f"File del core non trovato per '{console_name}'.\n"
                                 f"Percorso atteso: {core_path}\n"
                                 "Assicurati che il core sia presente nella cartella 'cores'.")
            return

        # --- Costruzione Comando ---
        # Cerca un file di configurazione specifico per il core
        config_filename = core_base + ".cfg"
        config_path = os.path.join(EMULATOR_CONFIG_FOLDER, config_filename)

        command = [retroarch_exe]
        # Se esiste un file di config specifico per il core, usalo
        if os.path.exists(config_path):
            command.extend(["--config", config_path])
            print(f"Info: Uso file di configurazione specifico del core: {config_path}")
        else:
            # Altrimenti, cerca un file di configurazione globale (opzionale)
            global_config_path = os.path.join(EMULATOR_CONFIG_FOLDER, "retroarch_global.cfg")
            if os.path.exists(global_config_path):
                 command.extend(["--config", global_config_path])
                 print(f"Info: Uso file di configurazione globale: {global_config_path}")

        # Aggiungi il core e il percorso della ROM
        command.extend(["-L", core_path, rom_path])

        # --- Avvio Processo ---
        try:
            print(f"Lancio comando: {' '.join(command)}") # Log del comando
            # Avvia RetroArch in un processo separato senza bloccare la GUI
            subprocess.Popen(command)
        except OSError as e:
            QMessageBox.critical(self, "Errore Avvio Sistema",
                                 f"Impossibile eseguire il comando:\n{' '.join(command)}\n"
                                 f"Errore di sistema: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Errore Imprevisto",
                                 f"Errore imprevisto durante l'avvio di RetroArch:\n{e}")

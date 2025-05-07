import logging
import os

from PySide6.QtCore import QSettings, Qt  # Aggiunto QSettings
from PySide6.QtWidgets import (  # Aggiunto QComboBox, QApplication
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from src.config import resource_path  # Aggiunto resource_path
from src.config import (
    CONSOLES,
    DEFAULT_THEME_FILENAME,
    MAX_CONCURRENT_DOWNLOADS,
    SETTINGS_APP,
    SETTINGS_ORG,
    STYLES_REL_PATH,
    USER_DOWNLOADS_FOLDER,
    add_console,
    set_max_concurrent_downloads,
    set_user_download_folder,
)


class SettingsDialog(QDialog):
    """
    Dialog window for configuring general application settings like
    download folder, max concurrent downloads, themes, and adding new consoles.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opzioni Generali")
        self.setMinimumWidth(500)
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)  # Istanzia QSettings
        self.theme_map = {}  # Dizionario per mappare nome visualizzato -> nome file
        self.init_ui()
        self._load_current_settings()

    def init_ui(self):
        """Initializes the user interface of the settings dialog."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # --- Sezione Download Folder ---
        dl_layout = QHBoxLayout()
        dl_layout.addWidget(QLabel("Cartella dei Download:"))
        self.download_folder_edit = QLineEdit()  # Rimuovi USER_DOWNLOADS_FOLDER da qui
        self.download_folder_edit.setReadOnly(True)
        dl_layout.addWidget(self.download_folder_edit)
        self.btn_browse = QPushButton("Sfoglia...")
        self.btn_browse.clicked.connect(self.browse_folder)
        dl_layout.addWidget(self.btn_browse)
        layout.addLayout(dl_layout)

        # --- Sezione Max Concurrent Downloads ---
        md_layout = QHBoxLayout()
        md_layout.addWidget(QLabel("Max download concorrenti:"))
        self.max_dl_spin = QSpinBox()
        self.max_dl_spin.setMinimum(1)
        self.max_dl_spin.setMaximum(10)
        # self.max_dl_spin.setValue(MAX_CONCURRENT_DOWNLOADS) # Impostato in _load_current_settings
        self.max_dl_spin.setFixedWidth(60)
        md_layout.addWidget(self.max_dl_spin)
        md_layout.addStretch()
        layout.addLayout(md_layout)

        # --- Sezione Tema GUI ---
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Tema Interfaccia:"))
        self.theme_combo = QComboBox()
        self._populate_theme_combo()  # Popola la combo box
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        # --- Sezione Nuova Console ---
        nc_group = QGroupBox("Aggiungi Nuova Console (Avanzato)")
        nc_layout = QFormLayout(nc_group)
        nc_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.new_console_name = QLineEdit()
        self.new_console_name.setPlaceholderText("Es. Sega Mega Drive")
        nc_layout.addRow("Titolo Visualizzato:", self.new_console_name)

        self.new_console_link = QLineEdit()
        self.new_console_link.setPlaceholderText(
            "Es. No-Intro/Sega%20-%20Mega%20Drive%20-%20Genesis/"
        )
        nc_layout.addRow("Percorso Relativo URL:", self.new_console_link)

        self.btn_add_console = QPushButton("Aggiungi Console alla Lista")
        self.btn_add_console.clicked.connect(self.add_new_console)
        nc_layout.addRow(self.btn_add_console)
        layout.addWidget(nc_group)

        layout.addStretch()

        # --- Pulsanti OK/Cancel ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_ok = QPushButton("OK")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept_settings)
        self.btn_cancel = QPushButton("Annulla")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def _populate_theme_combo(self):
        """Scans for themes and populates the theme selection combo box."""
        self.theme_map = {}
        styles_dir = resource_path(STYLES_REL_PATH)
        default_display_name = "Default"  # Nome per il tema di default

        if not os.path.isdir(styles_dir):
            logging.warning(f"Directory degli stili non trovata: {styles_dir}")
            self.theme_combo.addItem(default_display_name)  # Aggiungi almeno un default
            self.theme_map[default_display_name] = DEFAULT_THEME_FILENAME
            return

        try:
            found_themes = False
            for filename in os.listdir(styles_dir):
                if filename.lower().endswith("_theme.qss"):
                    theme_name_base = filename[
                        : -len("_theme.qss")
                    ]  # Es: "light", "dark_blue"
                    display_name = (
                        theme_name_base.replace("_", " ").title() + " Theme"
                    )  # Es: "Light Theme", "Dark Blue Theme"
                    self.theme_combo.addItem(display_name)
                    self.theme_map[display_name] = filename
                    found_themes = True
                    logging.debug(f"Trovato tema: '{display_name}' -> {filename}")

            # Assicurati che il tema di default sia presente se non è tra i _theme.qss
            if DEFAULT_THEME_FILENAME not in self.theme_map.values():
                if os.path.exists(os.path.join(styles_dir, DEFAULT_THEME_FILENAME)):
                    self.theme_combo.insertItem(
                        0, default_display_name
                    )  # Inserisci all'inizio
                    self.theme_map[default_display_name] = DEFAULT_THEME_FILENAME
                else:
                    # Se anche il default non esiste, scegli il primo trovato come fallback
                    if self.theme_map:
                        first_display_name = list(self.theme_map.keys())[0]
                        self.theme_map[default_display_name] = self.theme_map[
                            first_display_name
                        ]
                        logging.warning(
                            f"File tema di default '{DEFAULT_THEME_FILENAME}' non trovato. Usando '{self.theme_map[default_display_name]}' come fallback."
                        )
                    else:
                        # Caso estremo: nessun tema trovato
                        self.theme_combo.addItem("Nessun Tema")
                        self.theme_map["Nessun Tema"] = ""

            if not found_themes and default_display_name not in self.theme_map:
                logging.warning(
                    f"Nessun file *_theme.qss trovato in {styles_dir} e il default non è disponibile."
                )
                # Lascia la combo vuota o con un messaggio

        except Exception as e:
            logging.error(f"Errore durante la scansione dei temi in {styles_dir}: {e}")
            # Assicurati che ci sia almeno l'opzione di default
            if default_display_name not in self.theme_map:
                self.theme_combo.clear()
                self.theme_combo.addItem(default_display_name)
                self.theme_map[default_display_name] = DEFAULT_THEME_FILENAME

    def _load_current_settings(self):
        """Loads current values from QSettings and updates the UI elements."""
        # Carica Download Folder
        current_dl_folder = self.settings.value(
            "download_folder", USER_DOWNLOADS_FOLDER
        )
        self.download_folder_edit.setText(current_dl_folder)

        # Carica Max Concurrent Downloads
        current_max_dl = int(self.settings.value("max_dl", MAX_CONCURRENT_DOWNLOADS))
        self.max_dl_spin.setValue(current_max_dl)

        # Carica Tema Selezionato
        current_theme_filename = self.settings.value(
            "gui/theme", DEFAULT_THEME_FILENAME
        )
        selected_display_name = None
        for display, fname in self.theme_map.items():
            if fname == current_theme_filename:
                selected_display_name = display
                break

        if selected_display_name:
            self.theme_combo.setCurrentText(selected_display_name)
        else:
            # Se il tema salvato non esiste più, seleziona il default o il primo
            default_display = (
                "Default" if DEFAULT_THEME_FILENAME in self.theme_map.values() else None
            )
            if default_display and default_display in self.theme_map:
                self.theme_combo.setCurrentText(default_display)
            elif self.theme_combo.count() > 0:
                self.theme_combo.setCurrentIndex(0)
            logging.warning(
                f"Tema salvato ('{current_theme_filename}') non trovato. Selezionato tema di default/primo disponibile."
            )

    def browse_folder(self):
        """Opens a dialog to select the download folder."""
        current_folder = self.download_folder_edit.text()
        folder = QFileDialog.getExistingDirectory(
            self, "Seleziona cartella download", current_folder
        )
        if folder:
            self.download_folder_edit.setText(folder)

    def add_new_console(self):
        """Adds a new console entry to the configuration."""
        name = self.new_console_name.text().strip()
        link = self.new_console_link.text().strip()
        if not name or not link:
            QMessageBox.warning(
                self,
                "Dati Mancanti",
                "Inserire sia il Titolo che il Link per la nuova console.",
            )
            return

        # Nota: add_console modifica CONSOLES solo a runtime.
        # Potrebbe essere necessario un meccanismo per salvare/caricare queste console personalizzate.
        if name in CONSOLES:
            reply = QMessageBox.question(
                self,
                "Console Esistente",
                f"Una console con il nome '{name}' esiste già.\nVuoi sovrascrivere il suo link?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            add_console(name, link)
            QMessageBox.information(
                self,
                "Console Aggiunta",
                f"Console '{name}' aggiunta/aggiornata (solo per questa sessione).\n",
            )
            # "Potrebbe essere necessario riavviare l'applicazione per vederla nella lista principale.") # Rimosso finché non c'è persistenza
            logging.info(
                f"Nuova console aggiunta/aggiornata (runtime): {name} -> {link}"
            )
            self.new_console_name.clear()
            self.new_console_link.clear()
        except Exception as e:
            logging.error(f"Errore durante l'aggiunta della console '{name}': {e}")
            QMessageBox.critical(
                self, "Errore", f"Impossibile aggiungere la console:\n{e}"
            )

    def accept_settings(self):
        """Applies the selected settings and closes the dialog."""
        # Applica Download Folder
        new_folder = self.download_folder_edit.text()
        current_folder = self.settings.value("download_folder", USER_DOWNLOADS_FOLDER)
        if new_folder != current_folder:
            set_user_download_folder(
                new_folder
            )  # Questa funzione salva già in settings
            logging.info(f"Cartella download impostata su: {new_folder}")

        # Applica Max Concurrent Downloads
        new_max_dl = self.max_dl_spin.value()
        current_max_dl = int(self.settings.value("max_dl", MAX_CONCURRENT_DOWNLOADS))
        if new_max_dl != current_max_dl:
            set_max_concurrent_downloads(
                new_max_dl
            )  # Questa funzione salva già in settings
            logging.info(f"Max download concorrenti impostato su: {new_max_dl}")

        # Applica Tema
        selected_display_name = self.theme_combo.currentText()
        selected_filename = self.theme_map.get(selected_display_name)
        current_theme = self.settings.value("gui/theme", DEFAULT_THEME_FILENAME)

        if selected_filename is not None and selected_filename != current_theme:
            self.settings.setValue("gui/theme", selected_filename)
            logging.info(f"Tema GUI impostato su: {selected_filename}")
            # Qui è dove l'applicazione principale dovrebbe riapplicare lo stile
            self.apply_theme_immediately(
                selected_filename
            )  # Chiamata per applicazione immediata

        self.accept()  # Chiude il dialogo con stato accettato

    def apply_theme_immediately(self, theme_filename):
        """Applies the selected theme to the running application."""
        styles_dir = resource_path(STYLES_REL_PATH)
        theme_path = os.path.join(styles_dir, theme_filename)
        style_sheet = ""
        if os.path.exists(theme_path):
            try:
                with open(theme_path, "r", encoding="utf-8") as f:
                    style_sheet = f.read()
                logging.info(f"Applicazione immediata del tema: {theme_filename}")
            except Exception as e:
                logging.error(
                    f"Errore lettura tema per applicazione immediata {theme_path}: {e}"
                )
        else:
            logging.warning(
                f"File tema '{theme_filename}' non trovato per applicazione immediata."
            )

        app = QApplication.instance()
        if app:
            app.setStyleSheet(style_sheet)
        else:
            logging.error(
                "Impossibile ottenere QApplication instance per applicare il tema."
            )

    # get_values non è più strettamente necessario se applichiamo direttamente,
    # ma lo lasciamo se serve altrove.
    def get_values(self):
        """
        Returns the configured values. Note: Values are applied directly
        when 'OK' is clicked via accept_settings.
        """
        selected_display_name = self.theme_combo.currentText()
        selected_theme_filename = self.theme_map.get(
            selected_display_name, DEFAULT_THEME_FILENAME
        )

        return {
            "download_folder": self.download_folder_edit.text(),
            "max_dl": self.max_dl_spin.value(),
            "theme_filename": selected_theme_filename,
        }

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QSpinBox, QFileDialog,
                               QMessageBox, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt 
from src.config import (USER_DOWNLOADS_FOLDER, set_user_download_folder,
                        MAX_CONCURRENT_DOWNLOADS, set_max_concurrent_downloads,
                        CONSOLES, add_console)
import logging

class SettingsDialog(QDialog):
    """
    Dialog window for configuring general application settings like
    download folder, max concurrent downloads, and adding new consoles.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opzioni Generali")
        self.setMinimumWidth(500)
        self.init_ui()

    def init_ui(self):
        """Initializes the user interface of the settings dialog."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        dl_layout = QHBoxLayout()
        dl_layout.addWidget(QLabel("Cartella dei Download:"))
        self.download_folder_edit = QLineEdit(USER_DOWNLOADS_FOLDER)
        self.download_folder_edit.setReadOnly(True)
        dl_layout.addWidget(self.download_folder_edit)
        self.btn_browse = QPushButton("Sfoglia...")
        self.btn_browse.clicked.connect(self.browse_folder)
        dl_layout.addWidget(self.btn_browse)
        layout.addLayout(dl_layout)

        md_layout = QHBoxLayout()
        md_layout.addWidget(QLabel("Max download concorrenti:"))
        self.max_dl_spin = QSpinBox()
        self.max_dl_spin.setMinimum(1)
        self.max_dl_spin.setMaximum(10)
        self.max_dl_spin.setValue(MAX_CONCURRENT_DOWNLOADS)
        self.max_dl_spin.setFixedWidth(60) 
        md_layout.addWidget(self.max_dl_spin)
        md_layout.addStretch() 
        layout.addLayout(md_layout)

        nc_group = QGroupBox("Aggiungi Nuova Console (Avanzato)")
        nc_layout = QFormLayout(nc_group) 
        nc_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.new_console_name = QLineEdit()
        self.new_console_name.setPlaceholderText("Es. Sega Mega Drive")
        nc_layout.addRow("Titolo Visualizzato:", self.new_console_name)

        self.new_console_link = QLineEdit()
        self.new_console_link.setPlaceholderText("Es. No-Intro/Sega%20-%20Mega%20Drive%20-%20Genesis/")
        nc_layout.addRow("Percorso Relativo URL:", self.new_console_link)

        self.btn_add_console = QPushButton("Aggiungi Console alla Lista")
        self.btn_add_console.clicked.connect(self.add_new_console)
        nc_layout.addRow(self.btn_add_console)
        layout.addWidget(nc_group)

        layout.addStretch()

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

    def browse_folder(self):
        """Opens a dialog to select the download folder."""
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella download", USER_DOWNLOADS_FOLDER)
        if folder:
            self.download_folder_edit.setText(folder)

    def add_new_console(self):
        """Adds a new console entry to the configuration."""
        name = self.new_console_name.text().strip()
        link = self.new_console_link.text().strip()
        if not name or not link:
            QMessageBox.warning(self, "Dati Mancanti", "Inserire sia il Titolo che il Link per la nuova console.")
            return

        if name in CONSOLES:
             reply = QMessageBox.question(self, "Console Esistente",
                                          f"Una console con il nome '{name}' esiste già.\nVuoi sovrascrivere il suo link?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                          QMessageBox.StandardButton.No)
             if reply == QMessageBox.StandardButton.No:
                 return

        try:
            add_console(name, link) 
            QMessageBox.information(self, "Console Aggiunta",
                                    f"Console '{name}' aggiunta/aggiornata.\n"
                                    "Potrebbe essere necessario riavviare l'applicazione per vederla nella lista principale.")
            logging.info(f"Nuova console aggiunta/aggiornata: {name} -> {link}")
            self.new_console_name.clear()
            self.new_console_link.clear()
        except Exception as e:
            logging.error(f"Errore durante l'aggiunta della console '{name}': {e}")
            QMessageBox.critical(self, "Errore", f"Impossibile aggiungere la console:\n{e}")


    def accept_settings(self):
        """Applies the selected settings and closes the dialog."""
        new_folder = self.download_folder_edit.text()
        if new_folder != USER_DOWNLOADS_FOLDER:
             set_user_download_folder(new_folder)
             logging.info(f"Cartella download impostata su: {new_folder}")

        new_max_dl = self.max_dl_spin.value()
        if new_max_dl != MAX_CONCURRENT_DOWNLOADS:
             set_max_concurrent_downloads(new_max_dl)
             logging.info(f"Max download concorrenti impostato su: {new_max_dl}")

        self.accept() 


    def get_values(self):
        """
        Returns the configured values. Note: Values are applied directly
        when 'OK' is clicked via accept_settings. This method might
        not be strictly necessary anymore unless the caller needs the values again.
        """
        return {
            "download_folder": self.download_folder_edit.text(),
            "max_dl": self.max_dl_spin.value()
        }
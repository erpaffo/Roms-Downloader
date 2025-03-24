from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QFileDialog
from src.config import USER_DOWNLOADS_FOLDER, set_user_download_folder, MAX_CONCURRENT_DOWNLOADS, set_max_concurrent_downloads, CONSOLES, add_console
from src.utils import ALLOWED_NATIONS

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opzioni")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Sezione 1: Cartella dei download
        dl_layout = QHBoxLayout()
        dl_layout.addWidget(QLabel("Cartella dei Download:"))
        self.download_folder_edit = QLineEdit(USER_DOWNLOADS_FOLDER)
        self.download_folder_edit.setReadOnly(True)
        dl_layout.addWidget(self.download_folder_edit)
        self.btn_browse = QPushButton("Sfoglia...")
        self.btn_browse.clicked.connect(self.browse_folder)
        dl_layout.addWidget(self.btn_browse)
        layout.addLayout(dl_layout)
        
        # Sezione 2: Max download concorrenti
        md_layout = QHBoxLayout()
        md_layout.addWidget(QLabel("Max download concorrenti:"))
        self.max_dl_spin = QSpinBox()
        self.max_dl_spin.setMinimum(1)
        self.max_dl_spin.setMaximum(5)
        self.max_dl_spin.setValue(MAX_CONCURRENT_DOWNLOADS)
        md_layout.addWidget(self.max_dl_spin)
        layout.addLayout(md_layout)
        
        # Sezione 3: Aggiungi nuova console
        nc_layout = QVBoxLayout()
        nc_layout.addWidget(QLabel("Aggiungi nuova console:"))
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Titolo:"))
        self.new_console_name = QLineEdit()
        name_layout.addWidget(self.new_console_name)
        nc_layout.addLayout(name_layout)
        
        link_layout = QHBoxLayout()
        link_layout.addWidget(QLabel("Link:"))
        self.new_console_link = QLineEdit()
        link_layout.addWidget(self.new_console_link)
        nc_layout.addLayout(link_layout)
        
        self.btn_add_console = QPushButton("Aggiungi Console")
        self.btn_add_console.clicked.connect(self.add_new_console)
        nc_layout.addWidget(self.btn_add_console)
        layout.addLayout(nc_layout)
        
        # Pulsanti OK/Cancel
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella download", USER_DOWNLOADS_FOLDER)
        if folder:
            self.download_folder_edit.setText(folder)
            set_user_download_folder(folder)
    
    def add_new_console(self):
        name = self.new_console_name.text().strip()
        link = self.new_console_link.text().strip()
        if not name or not link:
            # Puoi mostrare un messaggio di errore
            return
        # Chiama una funzione (definita in config.py) per aggiungere la console
        add_console(name, link)
        # Puoi mostrare un messaggio di conferma
        self.new_console_name.clear()
        self.new_console_link.clear()
    
    def get_values(self):
        return {
            "download_folder": self.download_folder_edit.text(),
            "max_dl": self.max_dl_spin.value()
        }

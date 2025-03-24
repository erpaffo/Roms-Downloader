from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton, QMessageBox, QLabel
import os

# Lista delle opzioni utili che l'utente può modificare
USEFUL_OPTIONS = ["video_scale", "audio_volume", "input_driver", "input_player1_a", 
                  "input_player1_b", "input_player1_x", "input_player1_y", "input_player1_start",
                  "input_player1_select", "input_player1_up", "input_player1_down", "input_player1_left",
                  "input_player1_right", "input_player1_l", "input_player1_r"]

# TODO Implementare opzioni utili per i core più comuni
COMMON_ALLOCATED_OPTIONS = [
    "input_driver", "audio_driver", "video_aspect_ratio", "video_fullscreen",
    "video_vsync", "menu_font_color_red", "menu_font_color_green", "menu_font_color_blue"
]

class EmulatorSettingsDialog(QDialog):
    def __init__(self, core_name, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Impostazioni per {core_name}")
        self.config_path = config_path
        self.options = {}  # Dizionario contenente tutte le opzioni lette dal file
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Carica il file di configurazione se esiste
        if os.path.exists(self.config_path):
            self.load_config()
        else:
            QMessageBox.information(self, "Informazione", "Il file di configurazione non esiste. Verrà creato un file vuoto.")

        # Le Useful Options sono quelle definite in USEFUL_OPTIONS
        self.useful_options = {k: v for k, v in self.options.items() if k in USEFUL_OPTIONS}
        # Le Allocated Options saranno quelle che NON sono in USEFUL_OPTIONS
        # ma solo quelle che sono anche presenti in COMMON_ALLOCATED_OPTIONS
        self.allocated_options = {k: v for k, v in self.options.items() 
                                  if k not in USEFUL_OPTIONS and k in COMMON_ALLOCATED_OPTIONS and v.strip().lower() not in ["", "null", "nul"]}

        # Gruppo per Useful Options
        useful_group = QGroupBox("Useful Options")
        useful_form = QFormLayout()
        self.useful_inputs = {}
        for key in USEFUL_OPTIONS:
            value = self.useful_options.get(key, "")
            line_edit = QLineEdit(str(value))
            useful_form.addRow(key, line_edit)
            self.useful_inputs[key] = line_edit
        useful_group.setLayout(useful_form)
        layout.addWidget(useful_group)

        # Gruppo per Allocated Options (solo quelle chiavi comuni)
        allocated_group = QGroupBox("Allocated Options (comuni)")
        allocated_form = QFormLayout()
        self.allocated_inputs = {}
        for key, value in self.allocated_options.items():
            line_edit = QLineEdit(value)
            allocated_form.addRow(key, line_edit)
            self.allocated_inputs[key] = line_edit
        allocated_group.setLayout(allocated_form)
        layout.addWidget(allocated_group)

        # Pulsante OK per salvare le modifiche
        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self.save_config)
        layout.addWidget(self.btn_ok)
        self.setLayout(layout)

    def load_config(self):
        """Carica il file di configurazione in self.options come dizionario."""
        try:
            with open(self.config_path, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.split("=", 1)
                        # Rimuovi spazi e eventuali virgolette
                        self.options[key.strip()] = value.strip().strip('"').strip("'")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile caricare la configurazione: {e}")

    def save_config(self):
        """Aggiorna self.options con i valori degli input e salva il file di configurazione."""
        # Aggiorna le useful options
        for key, line_edit in self.useful_inputs.items():
            self.options[key] = line_edit.text().strip()
        # Aggiorna le allocated options
        for key, line_edit in self.allocated_inputs.items():
            self.options[key] = line_edit.text().strip()
        try:
            with open(self.config_path, "w") as f:
                for key, value in self.options.items():
                    f.write(f"{key} = {value}\n")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile salvare la configurazione: {e}")

    def get_config_path(self):
        return self.config_path
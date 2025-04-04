from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLineEdit, QPushButton, QMessageBox, QLabel
import os
import logging 

USEFUL_OPTIONS = ["video_scale", "audio_volume", "input_driver", "input_player1_a",
                  "input_player1_b", "input_player1_x", "input_player1_y", "input_player1_start",
                  "input_player1_select", "input_player1_up", "input_player1_down", "input_player1_left",
                  "input_player1_right", "input_player1_l", "input_player1_r"]

COMMON_ALLOCATED_OPTIONS = [
    "input_driver", "audio_driver", "video_aspect_ratio", "video_fullscreen",
    "video_vsync", "menu_font_color_red", "menu_font_color_green", "menu_font_color_blue"
]

class EmulatorSettingsDialog(QDialog):
    def __init__(self, core_name, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Impostazioni per {core_name}")
        self.config_path = config_path
        self.options = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        if os.path.exists(self.config_path):
            self.load_config()
        else:
            QMessageBox.information(self, "Informazione", f"Il file di configurazione '{os.path.basename(self.config_path)}' non esiste. Verrà creato al salvataggio.")
            self.options = {}


        self.useful_options = {k: v for k, v in self.options.items() if k in USEFUL_OPTIONS}
        self.allocated_options = {k: v for k, v in self.options.items()
                                  if k not in USEFUL_OPTIONS and k in COMMON_ALLOCATED_OPTIONS and v.strip().lower() not in ["", "null", "nul"]}

        useful_group = QGroupBox("Opzioni Utili Comuni")
        useful_form = QFormLayout()
        self.useful_inputs = {}
        for key in USEFUL_OPTIONS:
            value = self.useful_options.get(key, "")
            line_edit = QLineEdit(str(value))
            useful_form.addRow(key, line_edit)
            self.useful_inputs[key] = line_edit
        useful_group.setLayout(useful_form)
        layout.addWidget(useful_group)

        allocated_group = QGroupBox("Altre Opzioni Comuni Rilevate")
        allocated_form = QFormLayout()
        self.allocated_inputs = {}
        for key, value in self.allocated_options.items():
            line_edit = QLineEdit(value)
            allocated_form.addRow(key, line_edit)
            self.allocated_inputs[key] = line_edit
        allocated_group.setLayout(allocated_form)
        layout.addWidget(allocated_group)

        self.btn_ok = QPushButton("Salva e Chiudi")
        self.btn_ok.clicked.connect(self.save_config)
        layout.addWidget(self.btn_ok)


    def load_config(self):
        """Loads the configuration file into self.options dictionary."""
        temp_options = {}
        try:
            with open(self.config_path, "r", encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        temp_options[key] = value

            self.options = temp_options 
            logging.info(f"Configurazione caricata da: {self.config_path}")
        except Exception as e:
            logging.error(f"Errore durante il caricamento di {self.config_path}: {e}")
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare la configurazione:\n{e}")

    def save_config(self):
        """Updates self.options from inputs and saves to the configuration file."""
        for key, line_edit in self.useful_inputs.items():
            self.options[key] = line_edit.text().strip()
        for key, line_edit in self.allocated_inputs.items():
            self.options[key] = line_edit.text().strip()

        try:
            with open(self.config_path, "w", encoding='utf-8') as f:
                for key in sorted(self.options.keys()):
                    value = self.options[key]
                    line = f'{key} = "{str(value)}"\n'
                    f.write(line)
            logging.info(f"Configurazione salvata in: {self.config_path}")
        except Exception as e:
            logging.error(f"Errore durante il salvataggio di {self.config_path}: {e}")
            QMessageBox.critical(self, "Errore Salvataggio", f"Impossibile salvare la configurazione:\n{e}")


    def get_config_path(self):
        """Returns the path of the configuration file being edited."""
        return self.config_path
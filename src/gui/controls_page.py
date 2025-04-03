import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout,
    QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QKeySequence
from src.console_keybindings import CONSOLE_KEYBINDINGS
from src.conversion import convert_binding

# Dizionario per etichette migliorate
PRETTY_LABELS = {
    "input_player1_a": "A",
    "input_player1_b": "B",
    "input_player1_up": "Su",
    "input_player1_down": "Giù",
    "input_player1_left": "Sinistra",
    "input_player1_right": "Destra",
    "input_player1_start": "Start",
    "input_player1_select": "Select",
    "input_player1_cross": "Cross",
    "input_player1_circle": "Circle",
    "input_player1_square": "Square",
    "input_player1_triangle": "Triangle",
    "input_player1_l1": "L1",
    "input_player1_r1": "R1",
    "input_player1_l2": "L2",
    "input_player1_r2": "R2",
    "input_player1_z": "Z",
}

class HotkeyInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.on_timeout)
    
    def mousePressEvent(self, event):
        self.clear()
        self.setPlaceholderText("Premi un tasto...")
        self.recording = True
        self.timer.start(3000)  # Attende 3 secondi
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        if self.recording:
            self.timer.stop()
            self.recording = False
            key_text = event.text()
            if not key_text:
                key_text = QKeySequence(event.key()).toString()
            modifiers = []
            if event.modifiers() & Qt.ControlModifier:
                modifiers.append("Ctrl")
            if event.modifiers() & Qt.AltModifier:
                modifiers.append("Alt")
            if event.modifiers() & Qt.ShiftModifier:
                modifiers.append("Shift")
            if event.modifiers() & Qt.MetaModifier:
                modifiers.append("Meta")
            if modifiers:
                key_text = "+".join(modifiers + [key_text])
            converted_key = convert_binding(key_text)
            self.setText(converted_key)
        else:
            super().keyPressEvent(event)
    
    def on_timeout(self):
        self.recording = False
        self.setPlaceholderText("Nessun tasto rilevato")

class ControlsPage(QWidget):
    def __init__(self, config_folder, parent=None):
        super().__init__(parent)
        self.config_folder = config_folder  # Cartella in cui salvare il file di configurazione per il core
        if not os.path.exists(self.config_folder):
            os.makedirs(self.config_folder)
        self.current_console = None
        self.binding_widgets = {}  # Mappa comando -> widget (HotkeyInput)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        # Selezione della console
        self.console_combo = QComboBox()
        self.console_combo.addItems(sorted(CONSOLE_KEYBINDINGS.keys()))
        self.console_combo.currentTextChanged.connect(self.load_bindings_for_console)
        layout.addWidget(QLabel("Seleziona Console:"))
        layout.addWidget(self.console_combo)
        
        # Area per i controlli (griglia)
        self.bindings_container = QWidget()
        self.bindings_layout = QGridLayout(self.bindings_container)
        layout.addWidget(self.bindings_container)
        
        # Pulsante Salva
        self.btn_save = QPushButton("Salva")
        self.btn_save.clicked.connect(self.on_save)
        layout.addWidget(self.btn_save)
        
        self.setLayout(layout)
        # Carica i binding per la console iniziale
        self.load_bindings_for_console(self.console_combo.currentText())
    
    def load_bindings_for_console(self, console_name):
        self.current_console = console_name
        default_bindings = CONSOLE_KEYBINDINGS.get(console_name, {})
        # Pulisci il layout attuale
        while self.bindings_layout.count():
            child = self.bindings_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.binding_widgets.clear()
        row = 0
        for command, default_value in default_bindings.items():
            label_text = PRETTY_LABELS.get(command, command)
            label = QLabel(label_text)
            input_field = HotkeyInput()
            input_field.setText(default_value)
            self.bindings_layout.addWidget(label, row, 0)
            self.bindings_layout.addWidget(input_field, row, 1)
            self.binding_widgets[command] = input_field
            row += 1
    
    def on_save(self):
        updated_bindings = {}
        for command, widget in self.binding_widgets.items():
            value = widget.text().strip()
            if value:
                updated_bindings[command] = value
        filename = f"{self.current_console.replace(' ', '_').lower()}.cfg"
        config_path = os.path.join(self.config_folder, filename)
        try:
            with open(config_path, "w") as f:
                for command, value in updated_bindings.items():
                    f.write(f'{command} = "{value}"\n')
            print(f"Configurazione salvata in: {config_path}")
        except Exception as e:
            print("Errore nel salvataggio:", e)

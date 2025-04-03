from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox,
    QGridLayout, QTabWidget, QWidget, QCheckBox, QLineEdit
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from src.key_bindings import KeyBindings
from src.conversion import convert_binding

class HotkeyInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.on_timeout)
    
    def mousePressEvent(self, event):
        # Quando l'utente clicca, attiva la modalità registrazione
        self.clear()
        self.setPlaceholderText("Premi un tasto...")
        self.recording = True
        self.timer.start(3000)  # 3 secondi di attesa
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        if self.recording:
            self.timer.stop()
            self.recording = False
            # Ottieni il tasto premuto
            key_text = event.text()
            if not key_text:
                # Per tasti non testuali (es. F1, etc.)
                key_text = QKeySequence(event.key()).toString()
            # Gestisci eventuali modificatori
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
            # Converte il tasto nel mapping americano
            converted_key = convert_binding(key_text)
            self.setText(converted_key)
        else:
            super().keyPressEvent(event)
    
    def on_timeout(self):
        # Timeout scattato senza ricevere input
        self.recording = False
        self.setPlaceholderText("Nessun tasto rilevato")

class HotkeysDialog(QDialog):
    def __init__(self, bindings: KeyBindings, parent=None):
        super().__init__(parent)
        self.bindings = bindings
        self.setWindowTitle("Configura Hotkeys")

        # Suddividi i binding in "Controlli" e "Hotkeys"
        self.controls = {}
        self.others = {}
        for command, value in self.bindings.bindings.items():
            if command.startswith("input_player1_"):
                self.controls[command] = value
            else:
                self.others[command] = value

        self.controls_widgets = {}
        self.hotkeys_widgets = {}

        main_layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()

        self.controls_tab = self.create_tab(self.controls, self.controls_widgets)
        self.tab_widget.addTab(self.controls_tab, "Controlli")

        self.hotkeys_tab = self.create_tab(self.others, self.hotkeys_widgets)
        self.tab_widget.addTab(self.hotkeys_tab, "Hotkeys")

        main_layout.addWidget(self.tab_widget)

        btn_save = QPushButton("Salva")
        btn_save.clicked.connect(self.on_save)
        main_layout.addWidget(btn_save)

        self.setLayout(main_layout)

    def create_tab(self, commands_dict, widget_map):
        tab = QWidget()
        grid = QGridLayout(tab)
        col_count = 2  # Numero di colonne
        index = 0
        for command, value in commands_dict.items():
            container = QWidget()
            vbox = QVBoxLayout(container)
            label = QLabel(command)
            vbox.addWidget(label)
            # Se il valore è "true" o "false", usa un QCheckBox
            if value.strip().lower() in ["true", "false"]:
                input_widget = QCheckBox()
                input_widget.setChecked(value.strip().lower() == "true")
            else:
                # Usa il widget HotkeyInput aggiornato per la registrazione del tasto
                input_widget = HotkeyInput()
                input_widget.setText(value)
            vbox.addWidget(input_widget)
            container.setLayout(vbox)
            grid.addWidget(container, index // col_count, index % col_count)
            widget_map[command] = input_widget
            index += 1
        tab.setLayout(grid)
        return tab

    def on_save(self):
        # Aggiorna i binding per "Controlli"
        for command, widget in self.controls_widgets.items():
            if isinstance(widget, QCheckBox):
                new_value = "true" if widget.isChecked() else "false"
            else:
                new_value = widget.text().strip()
            if new_value:
                if not self.bindings.set_binding(command, new_value):
                    QMessageBox.warning(self, "Conflitto",
                        f"Il tasto '{new_value}' è già in uso per un altro comando. Scegliere un altro tasto.")
                    return

        # Aggiorna i binding per "Hotkeys"
        for command, widget in self.hotkeys_widgets.items():
            if isinstance(widget, QCheckBox):
                new_value = "true" if widget.isChecked() else "false"
            else:
                new_value = widget.text().strip()
            if new_value:
                if not self.bindings.set_binding(command, new_value):
                    QMessageBox.warning(self, "Conflitto",
                        f"Il tasto '{new_value}' è già in uso per un altro comando. Scegliere un altro tasto.")
                    return

        if not self.bindings.validate_all_bindings():
            QMessageBox.critical(self, "Errore di conflitto",
                                 "Rilevati conflitti nei binding. Correggere prima di salvare.")
            return

        self.accept()

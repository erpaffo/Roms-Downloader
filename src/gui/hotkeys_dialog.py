from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox,
    QGridLayout, QTabWidget, QWidget, QCheckBox, QLineEdit
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from src.key_bindings import KeyBindings
from src.conversion import convert_binding
import logging

class HotkeyInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.on_timeout)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPlaceholderText("Clicca per registrare")

    def mousePressEvent(self, event):
        if not self.recording:
            self.recording = True
            self.clear()
            self.setPlaceholderText("Premi un tasto...")
            self.timer.start(3000)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if self.recording:
            self.timer.stop()
            self.recording = False
            self.setPlaceholderText("Clicca per registrare")

            key = event.key()
            modifiers = event.modifiers()

            if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta, Qt.Key.Key_unknown):
                 self.setPlaceholderText("Tasto non valido")
                 return

            key_text = event.text().lower()
            if not key_text or key < Qt.Key.Key_Space or key > Qt.Key.Key_ydiaeresis:
                 seq = QKeySequence(key)
                 key_text = seq.toString(QKeySequence.SequenceFormat.NativeText).lower()
                 if '+' in key_text:
                      key_text = key_text.split('+')[-1]

            mod_list = []
            if modifiers & Qt.KeyboardModifier.ControlModifier: mod_list.append("ctrl")
            if modifiers & Qt.KeyboardModifier.AltModifier: mod_list.append("alt")
            if modifiers & Qt.KeyboardModifier.ShiftModifier: mod_list.append("shift")
            if modifiers & Qt.KeyboardModifier.MetaModifier: mod_list.append("meta")

            if not key_text:
                 logging.warning("HotkeyInput.keyPressEvent: key_text vuoto.")
                 return

            converted_key = convert_binding(key_text)

            if mod_list:
                final_text = "+".join(mod_list + [converted_key])
            else:
                final_text = converted_key

            self.setText(final_text)
        else:
            super().keyPressEvent(event)

    def on_timeout(self):
        if self.recording:
            self.recording = False
            self.setPlaceholderText("Timeout! Clicca")

    def focusOutEvent(self, event):
        if self.recording:
             self.timer.stop()
             self.recording = False
             self.setPlaceholderText("Annullato! Clicca")
        super().focusOutEvent(event)


class HotkeysDialog(QDialog):
    def __init__(self, bindings: KeyBindings, parent=None):
        super().__init__(parent)
        self.bindings = bindings
        self.setWindowTitle("Configura Hotkeys")

        self.controls = {}
        self.others = {}
        if hasattr(bindings, 'bindings') and isinstance(bindings.bindings, dict):
            for command, value in bindings.bindings.items():
                if command.startswith("input_player1_"):
                    self.controls[command] = value if value is not None else ""
                else:
                    self.others[command] = value if value is not None else ""
        else:
             logging.error("Oggetto bindings non valido passato a HotkeysDialog.")


        self.controls_widgets = {}
        self.hotkeys_widgets = {}

        main_layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()

        self.controls_tab = self.create_tab(self.controls, self.controls_widgets)
        self.tab_widget.addTab(self.controls_tab, "Controlli Giocatore 1")

        self.hotkeys_tab = self.create_tab(self.others, self.hotkeys_widgets)
        self.tab_widget.addTab(self.hotkeys_tab, "Tasti Rapidi Globali")

        main_layout.addWidget(self.tab_widget)

        btn_save = QPushButton("Salva")
        btn_save.clicked.connect(self.on_save)
        main_layout.addWidget(btn_save)

    def create_tab(self, commands_dict, widget_map):
        tab = QWidget()
        grid = QGridLayout(tab)
        col_count = 2
        index = 0
        for command in sorted(commands_dict.keys()):
            value = commands_dict[command]

            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(0,0,0,0)
            label = QLabel(command) 
            vbox.addWidget(label)

            value_str = str(value).strip().lower() 

            if value_str in ["true", "false"]:
                input_widget = QCheckBox()
                input_widget.setChecked(value_str == "true")
            else:
                input_widget = HotkeyInput()
                input_widget.setText(str(value) if value is not None else "")

            vbox.addWidget(input_widget)
            grid.addWidget(container, index // col_count, index % col_count)
            widget_map[command] = input_widget
            index += 1
        return tab

    def on_save(self):
        new_bindings_temp = {} 
        has_conflict = False

        all_widgets = {**self.controls_widgets, **self.hotkeys_widgets}

        for command, widget in all_widgets.items():
            if isinstance(widget, QCheckBox):
                new_value = "true" if widget.isChecked() else "false"
            else:
                new_value = widget.text().strip().lower()
                if not new_value:
                     new_value = "nul"

            if not isinstance(widget, QCheckBox) and new_value != "nul":
                if new_value in new_bindings_temp:
                     conflict_command = new_bindings_temp[new_value]
                     QMessageBox.warning(self, "Conflitto Tasti",
                                           f"Il tasto '{new_value}' è assegnato sia a '{command}' che a '{conflict_command}'.")
                     has_conflict = True
                     break
                else:
                     new_bindings_temp[new_value] = command

            if hasattr(self.bindings, 'bindings'):
                 self.bindings.bindings[command] = new_value
            else:
                 logging.error("Attributo 'bindings' non trovato nell'oggetto bindings.")
                 QMessageBox.critical(self,"Errore Interno", "Oggetto bindings non valido.")
                 return

        if has_conflict:
            return 
        
        self.accept()
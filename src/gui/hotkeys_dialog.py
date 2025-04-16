from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
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

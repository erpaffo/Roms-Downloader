from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QGridLayout, QTabWidget, QWidget, QCheckBox, QVBoxLayout
)
from src.key_bindings import KeyBindings

class HotkeysDialog(QDialog):
    def __init__(self, bindings: KeyBindings, parent=None):
        super().__init__(parent)
        self.bindings = bindings  # Istanza esistente di KeyBindings
        self.setWindowTitle("Configura Hotkeys")

        # Dividi i binding in due gruppi, ad esempio "Controlli" e "Hotkeys"
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
                input_widget = QLineEdit()
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
                # Applichiamo il mapping: la GUI mantiene il valore originale,
                # ma noi salvando usiamo convert_binding(new_value)
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

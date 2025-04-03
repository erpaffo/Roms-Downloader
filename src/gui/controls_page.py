import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QFormLayout,
    QComboBox, QLineEdit, QScrollArea, QGroupBox, QMessageBox, QSizePolicy,
    QTabWidget, QCheckBox, QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QKeySequence
from src.console_keybindings import CONSOLE_KEYBINDINGS
from src.default_keybindings import DEFAULT_KEYBINDINGS
from src.conversion import convert_binding
from src.utils import update_emulator_config
from src.config import EMULATOR_CONFIG_FOLDER, DEFAULT_CORES

PRETTY_LABELS = {
    "input_player1_a": "A", "input_player1_b": "B", "input_player1_x": "X", "input_player1_y": "Y",
    "input_player1_up": "Su", "input_player1_down": "Giù", "input_player1_left": "Sinistra", "input_player1_right": "Destra",
    "input_player1_start": "Start", "input_player1_select": "Select", "input_player1_l": "L", "input_player1_r": "R",
    "input_player1_l1": "L1", "input_player1_r1": "R1", "input_player1_l2": "L2", "input_player1_r2": "R2",
    "input_player1_l3": "L3 (Stick Sinistro)", "input_player1_r3": "R3 (Stick Destro)", "input_player1_z": "Z",
    "input_player1_c_up": "C-Su", "input_player1_c_down": "C-Giù", "input_player1_c_left": "C-Sinistra", "input_player1_c_right": "C-Destra",
    "input_player1_cross": "Cross (X)", "input_player1_circle": "Circle (O)", "input_player1_square": "Square", "input_player1_triangle": "Triangle",
    "input_player1_analog_left": "Stick Sinistro - Sinistra", "input_player1_analog_right": "Stick Sinistro - Destra",
    "input_player1_analog_up": "Stick Sinistro - Su", "input_player1_analog_down": "Stick Sinistro - Giù",
    "input_player1_analog_r_left": "Stick Destro - Sinistra", "input_player1_analog_r_right": "Stick Destro - Destra",
    "input_player1_analog_r_up": "Stick Destro - Su", "input_player1_analog_r_down": "Stick Destro - Giù",
    "input_player1_dpad_up": "D-Pad Su", "input_player1_dpad_down": "D-Pad Giù", "input_player1_dpad_left": "D-Pad Sinistra", "input_player1_dpad_right": "D-Pad Destra",
    "input_player1_fire": "Fuoco 1", "input_player1_fire2": "Fuoco 2",
    "input_player1_pause": "Pausa", "input_player1_ps": "Tasto PS/Home", "input_player1_zl": "ZL", "input_player1_zr": "ZR",
    "input_player1_minus": "Minus (-)", "input_player1_plus": "Plus (+)", "input_player1_home": "Home",
    "input_player1_1": "1", "input_player1_2": "2", "input_player1_c": "C (Nunchuk)",
    "input_menu_toggle": "Menu Principale", "input_save_state": "Salva Stato", "input_load_state": "Carica Stato",
    "input_exit_emulator": "Esci Emulatore", "input_pause_toggle": "Pausa/Riprendi", "input_reset": "Reset Gioco",
    "input_rewind": "Rewind", "input_hold_fast_forward": "Avanzamento Rapido (Tieni)", "input_toggle_fast_forward": "Avanzamento Rapido (Toggle)",
    "input_screenshot": "Screenshot", "input_toggle_fullscreen": "Schermo Intero", "input_volume_up": "Volume Su", "input_volume_down": "Volume Giù",
    "input_shader_next": "Shader Successivo", "input_shader_prev": "Shader Precedente", "input_shader_toggle": "Attiva/Disattiva Shader",
    "input_state_slot_increase": "Slot Stato (+)", "input_state_slot_decrease": "Slot Stato (-)",
    "video_vsync": "V-Sync", # Etichetta per nuova opzione
    "video_driver": "Driver Video", # Etichetta per nuova opzione
}

CORE_USEFUL_OPTIONS = ["video_scale", "audio_volume", "input_driver"]
CORE_COMMON_ALLOCATED_OPTIONS = [
    "audio_driver", "video_aspect_ratio", "video_fullscreen",
    "video_vsync", # Aggiunto qui o gestito separatamente
    "menu_font_color_red", "menu_font_color_green", "menu_font_color_blue"
]

# Lista dei driver video comuni (potrebbe variare per OS)
VIDEO_DRIVERS = ["gl", "glcore", "vulkan", "d3d11", "d3d12", "metal", "sdl2", "null"]

class HotkeyInput(QLineEdit):
    """
    Un QLineEdit personalizzato per catturare un singolo tasto o combinazione
    di tasti quando viene cliccato. (Versione corretta)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recording = False
        self.setProperty("recording", False)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.on_timeout)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPlaceholderText("Clicca per registrare")

    def _update_style(self):
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event):
        if not self.recording:
            self.recording = True
            self.setProperty("recording", True)
            self._update_style()
            self.clear()
            self.setPlaceholderText("Premi un tasto...")
            self.timer.start(3000)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if self.recording:
            self.timer.stop()
            self.recording = False
            self.setProperty("recording", False)
            self._update_style()
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
                 logging.warning("keyPressEvent: key_text vuoto dopo l'elaborazione.")
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
            self.setProperty("recording", False)
            self._update_style()
            self.setPlaceholderText("Timeout! Clicca")

    def focusOutEvent(self, event):
        if self.recording:
            self.timer.stop()
            self.recording = False
            self.setProperty("recording", False)
            self._update_style()
            self.setPlaceholderText("Annullato! Clicca")
        super().focusOutEvent(event)

# --- Fine Classe HotkeyInput ---

class ControlsPage(QWidget):
    """
    Pagina unificata per configurare controlli P1, tasti rapidi globali
    e impostazioni specifiche del core per diverse console.
    """
    def __init__(self, config_folder, parent=None):
        super().__init__(parent)
        self.config_folder = config_folder
        if not os.path.exists(self.config_folder):
            try:
                os.makedirs(self.config_folder)
            except OSError as e:
                logging.error(f"Impossibile creare cartella config '{self.config_folder}': {e}")

        self.current_console = None
        self.current_core_base = None
        self.core_config_path = None
        self.global_config_path = os.path.join(self.config_folder, "retroarch_global.cfg")

        self.p1_widgets = {}
        self.global_hotkey_widgets = {}
        self.core_setting_widgets = {}

        self.core_settings = {}
        self.global_settings = {}

        self.init_ui()

    def init_ui(self):
        """Inizializza l'interfaccia utente della pagina con le tab."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Seleziona Console/Core:"))
        self.console_combo = QComboBox()
        sorted_consoles = sorted(DEFAULT_CORES.keys())
        self.console_combo.addItems(sorted_consoles)
        self.console_combo.currentTextChanged.connect(self.load_bindings_and_settings)
        self.console_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        top_layout.addWidget(self.console_combo)
        main_layout.addLayout(top_layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("SettingsTabs")

        self.p1_controls_tab = self._create_scrollable_tab()
        self.global_hotkeys_tab = self._create_scrollable_tab()
        self.core_settings_tab = self._create_scrollable_tab()

        self.tab_widget.addTab(self.p1_controls_tab, "Controlli Giocatore 1")
        self.tab_widget.addTab(self.global_hotkeys_tab, "Tasti Rapidi Globali")
        self.tab_widget.addTab(self.core_settings_tab, "Impostazioni Core")

        main_layout.addWidget(self.tab_widget, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.btn_save = QPushButton("Salva Tutte le Impostazioni")
        self.btn_save.setObjectName("SaveControlsButton")
        self.btn_save.clicked.connect(self.on_save)
        button_layout.addWidget(self.btn_save)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        if sorted_consoles:
            self.load_bindings_and_settings(self.console_combo.currentText())

    def _create_scrollable_tab(self):
        """Crea un widget base per una tab contenente uno QScrollArea."""
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(5, 5, 5, 5)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_area_content = QWidget()
        scroll_area.setWidget(scroll_area_content)

        tab_layout.addWidget(scroll_area)
        return tab_widget

    def _get_scroll_content_widget(self, tab_index):
        """Ottiene il widget contenitore interno dello QScrollArea di una tab specifica."""
        try:
             tab_main_widget = self.tab_widget.widget(tab_index)
             if tab_main_widget:
                 scroll_area = tab_main_widget.findChild(QScrollArea)
                 if scroll_area:
                     return scroll_area.widget()
        except Exception as e:
             logging.error(f"Errore nell'ottenere scroll content widget per tab {tab_index}: {e}")
        return None

    def _load_config_file(self, file_path):
        """Carica un file di configurazione (.cfg) e restituisce un dizionario."""
        settings_dict = {}
        if not os.path.exists(file_path):
            logging.warning(f"File di configurazione non trovato: {file_path}")
            return settings_dict

        try:
            with open(file_path, "r", encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        settings_dict[key] = value
        except Exception as e:
            logging.error(f"Errore nel caricamento di '{file_path}': {e}")
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare {os.path.basename(file_path)}:\n{e}")
        return settings_dict

    def load_bindings_and_settings(self, console_name):
        """Carica tutte le impostazioni (P1, globali, core) per la console selezionata."""
        logging.info(f"Caricamento impostazioni per: {console_name}")
        self.current_console = console_name
        self.current_core_base = DEFAULT_CORES.get(console_name)

        if not self.current_core_base:
            QMessageBox.critical(self, "Errore", f"Core base non definito per {console_name} in config.py")
            self._clear_all_tabs()
            return

        core_cfg_filename = f"{self.current_core_base}.cfg"
        self.core_config_path = os.path.join(self.config_folder, core_cfg_filename)

        self.core_settings = self._load_config_file(self.core_config_path)
        self.global_settings = self._load_config_file(self.global_config_path)

        self._populate_p1_controls_tab()
        self._populate_global_hotkeys_tab()
        self._populate_core_settings_tab()

    def _clear_layout(self, layout):
        """Rimuove tutti i widget da un layout."""
        if layout is None: return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                inner_layout = item.layout()
                if inner_layout:
                    self._clear_layout(inner_layout)

    def _clear_all_tabs(self):
         """Pulisce il contenuto di tutte le tab."""
         try:
             self._clear_layout(self._get_scroll_content_widget(0).layout() if self._get_scroll_content_widget(0) else None)
             self._clear_layout(self._get_scroll_content_widget(1).layout() if self._get_scroll_content_widget(1) else None)
             self._clear_layout(self._get_scroll_content_widget(2).layout() if self._get_scroll_content_widget(2) else None)
             self.p1_widgets.clear()
             self.global_hotkey_widgets.clear()
             self.core_setting_widgets.clear()
         except Exception as e:
              logging.error(f"Errore durante la pulizia delle tab: {e}")

    def _populate_p1_controls_tab(self):
        """Popola la tab 'Controlli Giocatore 1'."""
        content_widget = self._get_scroll_content_widget(0)
        if not content_widget: return

        layout = content_widget.layout()
        if layout:
            self._clear_layout(layout)
        else:
            layout = QGridLayout(content_widget)
            layout.setSpacing(10)
            layout.setColumnStretch(0, 0)
            layout.setColumnStretch(1, 1)

        self.p1_widgets.clear()

        default_bindings = CONSOLE_KEYBINDINGS.get(self.current_console, {})
        sorted_commands = sorted(default_bindings.keys())
        row = 0
        for command in sorted_commands:
            default_value = default_bindings.get(command, "nul")
            current_value = self.core_settings.get(command, default_value)
            label_text = PRETTY_LABELS.get(command, command.replace("input_player1_", "").replace("_", " ").title())
            label = QLabel(label_text + ":")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            input_field = HotkeyInput()
            input_field.setText(current_value if current_value != "nul" else "")

            layout.addWidget(label, row, 0)
            layout.addWidget(input_field, row, 1)
            self.p1_widgets[command] = input_field
            row += 1

        layout.setRowStretch(row, 1)

    def _populate_global_hotkeys_tab(self):
        """Popola la tab 'Tasti Rapidi Globali'."""
        content_widget = self._get_scroll_content_widget(1)
        if not content_widget: return

        layout = content_widget.layout()
        if layout:
            self._clear_layout(layout)
        else:
            layout = QFormLayout(content_widget)
            layout.setSpacing(10)
            layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.global_hotkey_widgets.clear()

        sorted_commands = sorted(DEFAULT_KEYBINDINGS.keys())
        for command in sorted_commands:
            if command.startswith("input_player1_"):
                continue

            default_value = DEFAULT_KEYBINDINGS.get(command, "nul")
            current_value = self.global_settings.get(command, default_value)
            label_text = PRETTY_LABELS.get(command, command.replace("input_", "").replace("_", " ").title())
            is_boolean = current_value.lower() in ["true", "false"] or default_value.lower() in ["true", "false"]

            if is_boolean:
                input_widget = QCheckBox()
                input_widget.setChecked(current_value.lower() == "true")
                layout.addRow(label_text + ":", input_widget)
            else:
                input_widget = HotkeyInput()
                input_widget.setText(current_value if current_value != "nul" else "")
                layout.addRow(label_text + ":", input_widget)

            self.global_hotkey_widgets[command] = input_widget

    def _populate_core_settings_tab(self):
        """Popola la tab 'Impostazioni Core', includendo V-Sync e Video Driver."""
        content_widget = self._get_scroll_content_widget(2)
        if not content_widget: return

        layout = content_widget.layout()
        if layout:
            self._clear_layout(layout)
        else:
            layout = QFormLayout(content_widget)
            layout.setSpacing(10)
            layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.core_setting_widgets.clear()

        # --- Gestione Specifica V-Sync ---
        vsync_key = "video_vsync"
        vsync_label = PRETTY_LABELS.get(vsync_key, "V-Sync") + ":"
        # Default a 'false' se non trovato
        vsync_current_value = self.core_settings.get(vsync_key, "false").lower()
        vsync_widget = QCheckBox()
        vsync_widget.setChecked(vsync_current_value == "true")
        layout.addRow(vsync_label, vsync_widget)
        self.core_setting_widgets[vsync_key] = vsync_widget # Salva riferimento
        # ------------------------------------

        # --- Gestione Specifica Video Driver ---
        vdriver_key = "video_driver"
        vdriver_label = PRETTY_LABELS.get(vdriver_key, "Driver Video") + ":"
        # Default a 'gl' se non trovato o vuoto
        vdriver_current_value = self.core_settings.get(vdriver_key) or "gl"
        vdriver_widget = QComboBox()
        vdriver_widget.addItems(VIDEO_DRIVERS) # Aggiunge opzioni definite globalmente
        # Seleziona il valore corrente nel ComboBox
        current_index = vdriver_widget.findText(vdriver_current_value, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive)
        if current_index >= 0:
            vdriver_widget.setCurrentIndex(current_index)
        else:
            # Se il valore salvato non è nella lista, aggiungilo temporaneamente e selezionalo
            # o seleziona il default 'gl'
            logging.warning(f"Valore salvato '{vdriver_current_value}' per {vdriver_key} non trovato nella lista standard. Seleziono 'gl'.")
            default_index = vdriver_widget.findText("gl")
            if default_index >=0: vdriver_widget.setCurrentIndex(default_index)
            # Alternativa: vdriver_widget.addItem(vdriver_current_value); vdriver_widget.setCurrentText(vdriver_current_value)

        layout.addRow(vdriver_label, vdriver_widget)
        self.core_setting_widgets[vdriver_key] = vdriver_widget # Salva riferimento
        # --------------------------------------

        # Gestione altre opzioni core (da liste, escludendo quelle già gestite)
        options_already_handled = {vsync_key, vdriver_key}
        p1_keys = set(CONSOLE_KEYBINDINGS.get(self.current_console, {}).keys())
        options_to_exclude = options_already_handled.union(p1_keys)

        core_options_to_show = sorted(list(set(CORE_USEFUL_OPTIONS + CORE_COMMON_ALLOCATED_OPTIONS) - options_to_exclude))

        for key in core_options_to_show:
            current_value = self.core_settings.get(key, "")
            is_boolean = current_value.lower() in ["true", "false"]
            label_text = PRETTY_LABELS.get(key, key.replace("_", " ").title()) + ":"

            if is_boolean:
                 input_widget = QCheckBox()
                 input_widget.setChecked(current_value.lower() == "true")
                 layout.addRow(label_text, input_widget)
            else:
                 input_widget = QLineEdit()
                 input_widget.setText(current_value)
                 layout.addRow(label_text, input_widget)

            self.core_setting_widgets[key] = input_widget


    def on_save(self):
        """Salva tutte le impostazioni modificate nei file .cfg appropriati."""
        if not self.current_console or not self.current_core_base:
            QMessageBox.warning(self, "Errore", "Nessuna console/core valido selezionato.")
            return

        p1_values = {}
        global_values = {}
        core_values = {}
        all_keys_to_check_conflict = {}
        has_conflict = False

        for command, widget in self.p1_widgets.items():
            value = widget.text().strip().lower()
            current_val = value if value else "nul"
            p1_values[command] = current_val
            if value and value != "nul":
                 all_keys_to_check_conflict[value] = command

        for command, widget in self.global_hotkey_widgets.items():
            if isinstance(widget, QCheckBox):
                value = "true" if widget.isChecked() else "false"
            else:
                value = widget.text().strip().lower()
            current_val = value if value else "nul"
            global_values[command] = current_val
            if not isinstance(widget, QCheckBox) and value and value != "nul":
                 if value in all_keys_to_check_conflict:
                      conflict_command = all_keys_to_check_conflict[value]
                      QMessageBox.critical(self, "Conflitto Tasti",
                                           f"Il tasto '{value}' è usato sia per '{PRETTY_LABELS.get(command, command)}' che per '{PRETTY_LABELS.get(conflict_command, conflict_command)}'.\n"
                                           "Risolvi il conflitto prima di salvare.")
                      has_conflict = True
                      break
                 else:
                      all_keys_to_check_conflict[value] = command
        if has_conflict: return

        # Raccogli Core Settings (inclusi VSync e Video Driver)
        for command, widget in self.core_setting_widgets.items():
            if isinstance(widget, QCheckBox):
                value = "true" if widget.isChecked() else "false"
            elif isinstance(widget, QComboBox): # Gestisci ComboBox per Video Driver
                value = widget.currentText()
            else: # QLineEdit
                value = widget.text().strip()
            core_values[command] = value # Salva il valore raccolto

        success = True
        errors = []

        try:
            converted_global = {cmd: convert_binding(val) if cmd in self.global_hotkey_widgets and isinstance(self.global_hotkey_widgets[cmd], HotkeyInput) else val for cmd, val in global_values.items()}
            update_emulator_config(self.global_config_path, converted_global)
            logging.info(f"Impostazioni globali salvate in: {self.global_config_path}")
        except Exception as e:
            success = False
            errors.append(f"Errore salvataggio globali ({os.path.basename(self.global_config_path)}): {e}")
            logging.error(f"Errore salvataggio '{self.global_config_path}': {e}")

        if self.core_config_path:
            core_specific_values = {}
            converted_p1 = {cmd: convert_binding(val) for cmd, val in p1_values.items()}
            core_specific_values.update(converted_p1)
            core_specific_values.update(core_values) # Aggiunge/sovrascrive con le core settings raccolte

            try:
                update_emulator_config(self.core_config_path, core_specific_values)
                logging.info(f"Impostazioni core per '{self.current_console}' salvate in: {self.core_config_path}")
            except Exception as e:
                success = False
                errors.append(f"Errore salvataggio core ({os.path.basename(self.core_config_path)}): {e}")
                logging.error(f"Errore salvataggio '{self.core_config_path}': {e}")
        else:
             success = False
             errors.append("Percorso file configurazione core non valido.")

        if success:
            QMessageBox.information(self, "Salvataggio Completato",
                                    f"Le impostazioni sono state salvate con successo.")
        else:
            QMessageBox.critical(self, "Errore Salvataggio",
                                 "Si sono verificati errori durante il salvataggio:\n\n" + "\n".join(errors))
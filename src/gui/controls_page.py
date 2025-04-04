import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QFormLayout,
    QComboBox, QLineEdit, QScrollArea, QGroupBox, QMessageBox, QSizePolicy, QFileDialog,
    QTabWidget, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QKeySequence
from src.console_keybindings import CONSOLE_KEYBINDINGS
from src.default_keybindings import DEFAULT_KEYBINDINGS
from src.conversion import convert_binding
from src.utils import update_emulator_config
from src.config import EMULATOR_CONFIG_FOLDER, DEFAULT_CORES, get_save_directory

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
    "video_vsync": "V-Sync",
    "video_driver": "Driver Video",
    "fps_show": "Mostra FPS",
    "input_cheat_index_minus": "Cheat Index (-)", "input_cheat_index_plus": "Cheat Index (+)", "input_cheat_toggle": "Attiva/Disattiva Cheat",
    "input_desktop_menu_toggle": "Menu Desktop", "input_driver": "Driver Input", "input_grab_mouse_toggle": "Cattura/Rilascia Mouse",
    "input_hold_slowmotion": "Slow Motion (Tieni)", "input_netplay_game_watch": "Netplay Guarda",
    "audio_volume": "Volume Audio (dB)", "video_scale": "Scala Video", "audio_driver": "Driver Audio",
    "video_aspect_ratio": "Aspect Ratio", "video_fullscreen": "Schermo Intero (Opzione)",
    "menu_font_color_red": "Colore Font Menu (Rosso)", "menu_font_color_green": "Colore Font Menu (Verde)", "menu_font_color_blue": "Colore Font Menu (Blu)",
}

CORE_USEFUL_OPTIONS = ["video_scale", "audio_volume", "input_driver"]
CORE_COMMON_ALLOCATED_OPTIONS = [
    "audio_driver", "video_aspect_ratio", "video_fullscreen",
    "video_vsync",
    "menu_font_color_red", "menu_font_color_green", "menu_font_color_blue"
]

CORE_SETTINGS_DEFAULTS = {
    "video_vsync": "false",
    "video_driver": "gl",
    "video_fullscreen": "false",
    "audio_driver": "",
    "input_driver": "",
}


VIDEO_DRIVERS = ["gl", "glcore", "vulkan", "d3d11", "d3d12", "metal", "sdl2", "null"]

SAVEFILE_DIR_KEY = "savefile_directory"
SAVESTATE_DIR_KEY = "savestate_directory"
SYSTEM_DIR_KEY = "system_directory"
SCREENSHOT_DIR_KEY = "screenshot_directory"

PRETTY_LABELS.update({
    SAVEFILE_DIR_KEY: "Cartella Salvataggi (.srm)",
    SAVESTATE_DIR_KEY: "Cartella Stati (.state)",
    SYSTEM_DIR_KEY: "Cartella System (BIOS)",
    SCREENSHOT_DIR_KEY: "Cartella Screenshot",
})

CORE_PATH_OPTIONS = {SAVEFILE_DIR_KEY, SAVESTATE_DIR_KEY, SYSTEM_DIR_KEY, SCREENSHOT_DIR_KEY}
CORE_USEFUL_OPTIONS = ["video_scale", "audio_volume", "input_driver"]
CORE_COMMON_ALLOCATED_OPTIONS = [
    "audio_driver", "video_aspect_ratio", "video_fullscreen",
    "video_vsync",
    "menu_font_color_red", "menu_font_color_green", "menu_font_color_blue"
]

class HotkeyInput(QLineEdit):
    """
    A custom QLineEdit for capturing a single key or key combination upon click.
    (Corrected version)
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
        """Forces a style update to apply QSS changes."""
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event):
        """Activates recording mode on click."""
        if not self.recording:
            self.recording = True
            self.setProperty("recording", True)
            self._update_style()
            self.clear()
            self.setPlaceholderText("Premi un tasto...")
            self.timer.start(3000)
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """Captures the pressed key during recording."""
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
                 logging.warning("keyPressEvent: key_text empty after processing.")
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
        """Handles timeout if no key is pressed."""
        if self.recording:
            self.recording = False
            self.setProperty("recording", False)
            self._update_style()
            self.setPlaceholderText("Timeout! Clicca")

    def focusOutEvent(self, event):
        """Cancels recording if focus is lost."""
        if self.recording:
            self.timer.stop()
            self.recording = False
            self.setProperty("recording", False)
            self._update_style()
            self.setPlaceholderText("Annullato! Clicca")
        super().focusOutEvent(event)

class ControlsPage(QWidget):
    """
    Unified page for configuring P1 controls, global hotkeys,
    and core-specific settings for different consoles.
    Includes a button to reset the current tab to defaults.
    """
    def __init__(self, config_folder, parent=None):
        super().__init__(parent)
        self.config_folder = config_folder
        if not os.path.exists(self.config_folder):
            try:
                os.makedirs(self.config_folder)
            except OSError as e:
                logging.error(f"Cannot create config folder '{self.config_folder}': {e}")

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
        """Initializes the user interface for the page with tabs."""
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
        self.btn_reset_tab = QPushButton("Ripristina Predefiniti Tab")
        self.btn_reset_tab.setObjectName("ResetTabButton")
        self.btn_reset_tab.clicked.connect(self.reset_current_tab_to_defaults)
        button_layout.addWidget(self.btn_reset_tab)

        self.btn_save = QPushButton("Salva Tutte le Impostazioni")
        self.btn_save.setObjectName("SaveControlsButton")
        self.btn_save.clicked.connect(self.on_save)
        button_layout.addWidget(self.btn_save)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        if sorted_consoles:
            self.load_bindings_and_settings(self.console_combo.currentText())

    def _create_scrollable_tab(self):
        """Creates a base widget for a tab containing a QScrollArea."""
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
        """Gets the inner container widget of a specific tab's QScrollArea."""
        try:
             tab_main_widget = self.tab_widget.widget(tab_index)
             if tab_main_widget:
                 scroll_area = tab_main_widget.findChild(QScrollArea)
                 if scroll_area:
                     return scroll_area.widget()
        except Exception as e:
             logging.error(f"Error getting scroll content widget for tab {tab_index}: {e}")
        return None

    def _load_config_file(self, file_path):
        """Loads a configuration file (.cfg) and returns a dictionary."""
        settings_dict = {}
        if not os.path.exists(file_path):
            logging.warning(f"Configuration file not found: {file_path}")
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
            logging.error(f"Error loading '{file_path}': {e}")
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare {os.path.basename(file_path)}:\n{e}")
        return settings_dict

    def load_bindings_and_settings(self, console_name):
        """Loads all settings (P1, global, core) for the selected console."""
        logging.info(f"Loading settings for: {console_name}")
        self.current_console = console_name
        self.current_core_base = DEFAULT_CORES.get(console_name)

        if not self.current_core_base:
            QMessageBox.critical(self, "Errore", f"Core base not defined for {console_name} in config.py")
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
        """Removes all widgets from a layout."""
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
         """Clears the content of all setting tabs."""
         try:
             self._clear_layout(self._get_scroll_content_widget(0).layout() if self._get_scroll_content_widget(0) else None)
             self._clear_layout(self._get_scroll_content_widget(1).layout() if self._get_scroll_content_widget(1) else None)
             self._clear_layout(self._get_scroll_content_widget(2).layout() if self._get_scroll_content_widget(2) else None)
             self.p1_widgets.clear()
             self.global_hotkey_widgets.clear()
             self.core_setting_widgets.clear()
         except Exception as e:
              logging.error(f"Error clearing setting tabs: {e}")

    def _populate_p1_controls_tab(self):
        """Populates the 'Player 1 Controls' tab, displaying converted default values."""
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
            raw_default_value = default_bindings.get(command, "nul")
            current_value_from_config = self.core_settings.get(command)

            if current_value_from_config is not None:
                display_value = current_value_from_config
            else:
                display_value = convert_binding(raw_default_value) if raw_default_value != "nul" else "nul"

            label_text = PRETTY_LABELS.get(command, command.replace("input_player1_", "").replace("_", " ").title())
            label = QLabel(label_text + ":")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            input_field = HotkeyInput()
            input_field.setText(display_value if display_value != "nul" else "")

            layout.addWidget(label, row, 0)
            layout.addWidget(input_field, row, 1)
            self.p1_widgets[command] = input_field
            row += 1

        layout.setRowStretch(row, 1)


    def _populate_global_hotkeys_tab(self):
        """Populates the 'Global Hotkeys' tab, displaying converted default values."""
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

            raw_default_value = DEFAULT_KEYBINDINGS.get(command, "nul")
            current_value_from_config = self.global_settings.get(command)

            label_text = PRETTY_LABELS.get(command, command.replace("input_", "").replace("_", " ").title())

            is_boolean = raw_default_value.lower() in ["true", "false"] or \
                         (current_value_from_config is not None and current_value_from_config.lower() in ["true", "false"])

            if is_boolean:
                current_value = current_value_from_config if current_value_from_config is not None else raw_default_value
                input_widget = QCheckBox()
                input_widget.setChecked(current_value.lower() == "true")
                layout.addRow(label_text + ":", input_widget)
            else:

                if current_value_from_config is not None:
                    display_value = current_value_from_config
                else:
                    display_value = convert_binding(raw_default_value) if raw_default_value != "nul" else "nul"

                input_widget = HotkeyInput()
                input_widget.setText(display_value if display_value != "nul" else "")
                layout.addRow(label_text + ":", input_widget)

            self.global_hotkey_widgets[command] = input_widget

    def _populate_core_settings_tab(self):
        """Populates the 'Core Settings' tab, including paths, V-Sync and Video Driver."""
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

        path_keys_to_add = [SAVEFILE_DIR_KEY, SAVESTATE_DIR_KEY, SYSTEM_DIR_KEY, SCREENSHOT_DIR_KEY]
        default_save_path = ""
        if self.current_console:
             try:
                 from src.config import get_save_directory, SYSTEM_FOLDER # Importa SYSTEM_FOLDER qui
                 default_save_path = get_save_directory(self.current_console)
             except ImportError:
                  logging.error("Funzioni get_save_directory o SYSTEM_FOLDER non trovate in config.py")
                  SYSTEM_FOLDER = "" # Fallback se import fallisce
             except Exception as e:
                  logging.error(f"Errore nel chiamare get_save_directory: {e}")
                  SYSTEM_FOLDER = "" # Fallback

        default_paths = {
            SAVEFILE_DIR_KEY: default_save_path,
            SAVESTATE_DIR_KEY: default_save_path,
            SYSTEM_DIR_KEY: SYSTEM_FOLDER,
            SCREENSHOT_DIR_KEY: ""
        }

        for key in path_keys_to_add:
            label_text = PRETTY_LABELS.get(key, key.replace("_", " ").title()) + ":"
            current_value = self.core_settings.get(key, default_paths.get(key, ""))

            path_layout = QHBoxLayout()
            line_edit = QLineEdit(current_value)
            line_edit.setPlaceholderText(f"Default RetroArch o {default_paths.get(key, 'N/D')}")
            browse_button = QPushButton("Sfoglia...")
            browse_button.clicked.connect(lambda checked=False, le=line_edit, start=default_paths.get(key, os.path.expanduser("~")): self._browse_directory(le, start))

            path_layout.addWidget(line_edit)
            path_layout.addWidget(browse_button)

            layout.addRow(label_text, path_layout)
            self.core_setting_widgets[key] = line_edit

        vsync_key = "video_vsync"
        vsync_label = PRETTY_LABELS.get(vsync_key, "V-Sync") + ":"
        vsync_default = CORE_SETTINGS_DEFAULTS.get(vsync_key, "false")
        vsync_current_value = self.core_settings.get(vsync_key, vsync_default).lower()
        vsync_widget = QCheckBox()
        vsync_widget.setChecked(vsync_current_value == "true")
        layout.addRow(vsync_label, vsync_widget)
        self.core_setting_widgets[vsync_key] = vsync_widget

        vdriver_key = "video_driver"
        vdriver_label = PRETTY_LABELS.get(vdriver_key, "Driver Video") + ":"
        vdriver_default = CORE_SETTINGS_DEFAULTS.get(vdriver_key, "gl")
        vdriver_current_value = self.core_settings.get(vdriver_key) or vdriver_default
        vdriver_widget = QComboBox()
        vdriver_widget.addItems(VIDEO_DRIVERS)
        current_index = vdriver_widget.findText(vdriver_current_value, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive)
        if current_index >= 0:
            vdriver_widget.setCurrentIndex(current_index)
        else:
            logging.warning(f"Saved value '{vdriver_current_value}' for {vdriver_key} not found in standard list. Selecting default '{vdriver_default}'.")
            default_index = vdriver_widget.findText(vdriver_default)
            if default_index >=0: vdriver_widget.setCurrentIndex(default_index)
        layout.addRow(vdriver_label, vdriver_widget)
        self.core_setting_widgets[vdriver_key] = vdriver_widget

        options_already_handled = {vsync_key, vdriver_key}.union(CORE_PATH_OPTIONS)
        p1_keys = set(CONSOLE_KEYBINDINGS.get(self.current_console, {}).keys())
        options_to_exclude = options_already_handled.union(p1_keys)
        core_options_to_show = sorted(list(set(CORE_USEFUL_OPTIONS + CORE_COMMON_ALLOCATED_OPTIONS) - options_to_exclude))

        for key in core_options_to_show:
            current_value = self.core_settings.get(key, CORE_SETTINGS_DEFAULTS.get(key, ""))
            is_boolean = current_value.lower() in ["true", "false"] or CORE_SETTINGS_DEFAULTS.get(key, "").lower() in ["true", "false"]
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

    def reset_current_tab_to_defaults(self):
        """Resets the widgets in the currently visible tab to their default values (converted)."""
        current_index = self.tab_widget.currentIndex()
        tab_name = self.tab_widget.tabText(current_index)

        reply = QMessageBox.question(self, "Conferma Reset",
                                     f"Sei sicuro di voler ripristinare le impostazioni predefinite per la tab '{tab_name}'?\n"
                                     "Le modifiche non saranno salvate finché non premi 'Salva Tutte le Impostazioni'.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.No:
            return

        logging.info(f"Resetting tab '{tab_name}' to defaults.")

        if current_index == 0:
            default_bindings = CONSOLE_KEYBINDINGS.get(self.current_console, {})
            for command, widget in self.p1_widgets.items():
                raw_default_value = default_bindings.get(command, "nul")

                converted_default = convert_binding(raw_default_value) if raw_default_value != "nul" else "nul"
                widget.setText(converted_default if converted_default != "nul" else "")
        elif current_index == 1:
            for command, widget in self.global_hotkey_widgets.items():
                raw_default_value = DEFAULT_KEYBINDINGS.get(command, "nul")
                if isinstance(widget, QCheckBox):
                     widget.setChecked(raw_default_value.lower() == "true")
                elif isinstance(widget, HotkeyInput):

                     converted_default = convert_binding(raw_default_value) if raw_default_value != "nul" else "nul"
                     widget.setText(converted_default if converted_default != "nul" else "")
        elif current_index == 2:
             for command, widget in self.core_setting_widgets.items():
                  default_value = CORE_SETTINGS_DEFAULTS.get(command, "")
                  if isinstance(widget, QCheckBox):
                       widget.setChecked(default_value.lower() == "true")
                  elif isinstance(widget, QComboBox):
                       default_index = widget.findText(default_value, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive)
                       if default_index >= 0:
                            widget.setCurrentIndex(default_index)
                       else:
                            widget.setCurrentIndex(0)
                  elif isinstance(widget, QLineEdit):
                       widget.setText(default_value)

        QMessageBox.information(self, "Reset Completato",
                                f"I valori nella tab '{tab_name}' sono stati ripristinati ai predefiniti.\n"
                                "Premi 'Salva Tutte le Impostazioni' per renderli permanenti.")

    def on_save(self):
            """Saves all modified settings to the appropriate .cfg files."""
            if not self.current_console or not self.current_core_base:
                QMessageBox.warning(self, "Errore", "Nessuna console/core valido selezionato.")
                return


            p1_values = {}
            global_values_from_ui = {}
            core_values_from_ui = {}
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
                global_values_from_ui[command] = current_val
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


            for command, widget in self.core_setting_widgets.items():
                if isinstance(widget, QCheckBox):
                    value = "true" if widget.isChecked() else "false"
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                else:
                    value = widget.text().strip()

                core_values_from_ui[command] = value



            combined_settings = {}
            combined_settings.update(DEFAULT_KEYBINDINGS)
            combined_settings.update(global_values_from_ui)
            combined_settings.update(core_values_from_ui)
            combined_settings.update(p1_values)






            final_settings_to_save = {}
            all_hotkey_widgets = {**self.p1_widgets, **self.global_hotkey_widgets}
            for command, value in combined_settings.items():
                if command in all_hotkey_widgets and isinstance(all_hotkey_widgets[command], HotkeyInput) and value != "nul":
                    final_settings_to_save[command] = convert_binding(value)
                else:
                    final_settings_to_save[command] = value


            success = True
            errors = []
            if self.core_config_path:
                try:
                    update_emulator_config(self.core_config_path, final_settings_to_save)
                    logging.info(f"Impostazioni COMBINATE (con percorsi UI) per '{self.current_console}' salvate in: {self.core_config_path}")
                except Exception as e:
                    success = False
                    errors.append(f"Errore salvataggio file core ({os.path.basename(self.core_config_path)}): {e}")
                    logging.error(f"Errore salvataggio '{self.core_config_path}': {e}")
            else:
                success = False
                errors.append("Percorso file configurazione core non valido.")


            if success:
                QMessageBox.information(self, "Salvataggio Completato",
                                        f"Le impostazioni per '{self.current_console}' sono state salvate nel file del core:\n{os.path.basename(self.core_config_path)}")
            else:
                QMessageBox.critical(self, "Errore Salvataggio",
                                    "Si sono verificati errori durante il salvataggio:\n\n" + "\n".join(errors))

    def _browse_directory(self, target_line_edit: QLineEdit, start_dir: str = ""):
        """Opens a directory selection dialog and updates the target QLineEdit."""
        current_dir = target_line_edit.text()
        initial_dir = start_dir
        if os.path.isdir(current_dir):
            initial_dir = current_dir
        elif not os.path.isdir(initial_dir):
             initial_dir = os.path.expanduser("~")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleziona Cartella",
            initial_dir
        )
        if folder:
            target_line_edit.setText(folder)
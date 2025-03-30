# key_bindings.py
from typing import Dict, Optional

class KeyBindings:
    def __init__(self, initial_bindings=None):
        if initial_bindings is None:
            self.bindings = {}
        else:
            self.bindings = initial_bindings.copy()

    def get_binding(self, command):
        return self.bindings.get(command)

    def set_binding(self, command, new_key):
        for cmd, key in self.bindings.items():
            if key == new_key and cmd != command:
                return False
        self.bindings[command] = new_key
        return True

    def validate_all_bindings(self):
        keys = list(self.bindings.values())
        return len(keys) == len(set(keys))

    def remove_binding(self, command: str):
        if command in self.bindings:
            self.bindings[command] = None
            print(f"🗑️ Binding rimosso dal comando '{command}'.")

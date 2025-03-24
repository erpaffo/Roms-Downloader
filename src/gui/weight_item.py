import re
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtCore import Qt

class WeightItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)
        self.value = self.convert_text_to_value(text)
        # Salviamo il valore normalizzato in MiB nel ruolo UserRole
        self.setData(Qt.UserRole, self.value)
        # Impostiamo il testo visualizzato (DisplayRole) in modo da mostrare le unità originali
        self.setData(Qt.DisplayRole, text)

    def convert_text_to_value(self, text):
        """
        Converte il testo in un valore numerico in MiB.
        Esempi:
          - "1.0 GiB" → 1.0 * 1024 = 1024 MiB
          - "25.4 MiB" → 25.4 MiB
          - "512 KiB"  → 512/1024 ≈ 0.5 MiB
        """
        try:
            text = text.strip().upper()
            match = re.match(r"([\d\.]+)\s*([GMK]I?B)", text)
            if match:
                number = float(match.group(1))
                unit = match.group(2)
                if unit in ["GIB", "GB"]:
                    # 1 GiB = 1024 MiB
                    return number * 1024
                elif unit in ["MIB", "MB"]:
                    return number
                elif unit in ["KIB", "KB"]:
                    # 1 MiB = 1024 KiB
                    return number / 1024
            else:
                # Se non viene riconosciuta un'unità, assumiamo byte e convertiamo in MiB
                return float(text) / (1024 * 1024)
        except Exception:
            return 0

    def __lt__(self, other):
        # Utilizziamo il valore normalizzato memorizzato in Qt.UserRole per il confronto
        try:
            self_val = self.data(Qt.UserRole)
            other_val = other.data(Qt.UserRole)
            if self_val is not None and other_val is not None:
                return float(self_val) < float(other_val)
        except Exception:
            pass
        return super().__lt__(other)

from PySide6.QtWidgets import QTableWidgetItem

class WeightItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)
        try:
            text = text.strip().upper()
            if "MB" in text:
                self.value = float(text.replace("MB", "").strip())
            elif "KB" in text:
                # Convertiamo in MB dividendo per 1024
                self.value = float(text.replace("KB", "").strip()) / 1024
            else:
                # Se non contiene unità, assumiamo che sia in byte e lo convertiamo in MB
                self.value = float(text) / (1024 * 1024)
        except Exception:
            self.value = 0

    def __lt__(self, other):
        if isinstance(other, WeightItem):
            return self.value < other.value
        return super().__lt__(other)

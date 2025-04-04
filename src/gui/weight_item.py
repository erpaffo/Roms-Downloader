import re
import logging
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtCore import Qt

class WeightItem(QTableWidgetItem):
    """
    A QTableWidgetItem subclass designed to handle file size strings (like "1.5 GiB").
    It stores the original text for display but uses a normalized numerical value
    (in MiB) for sorting purposes.
    """
    def __init__(self, text):
        super().__init__(text)
        self.value = self.convert_text_to_value(text)
        self.setData(Qt.ItemDataRole.UserRole, self.value)
        self.setData(Qt.ItemDataRole.DisplayRole, text)
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def convert_text_to_value(self, text):
        """
        Converts a size string (e.g., "1.0 GiB", "25.4 MiB", "512 KiB")
        into a numerical value in MiB (Mebibytes) for sorting.

        Examples:
          - "1.0 GiB" -> 1.0 * 1024 = 1024.0
          - "25.4 MiB" -> 25.4
          - "512 KiB"  -> 512 / 1024 = 0.5
          - "10000000" (bytes) -> 10000000 / (1024*1024) approx 9.54
          - "Unknown" -> 0
        """
        if not isinstance(text, str):
             return 0

        try:
            text_upper = text.strip().upper().replace(',', '.')
            match = re.match(r"([\d\.]+)\s*([KMGT]I?B|[BKMG])?", text_upper)

            if match:
                number_str = match.group(1)
                unit = match.group(2) if match.group(2) else 'B'

                try:
                     number = float(number_str)
                except ValueError:
                     logging.warning(f"Could not convert number part '{number_str}' to float in WeightItem for '{text}'")
                     return 0

                if unit in ["GIB", "GB", "G"]:
                    return number * 1024.0
                elif unit in ["MIB", "MB", "M"]:
                    return number
                elif unit in ["KIB", "KB", "K"]:
                    return number / 1024.0
                elif unit == 'B':
                    return number / (1024.0 * 1024.0)
                else:
                     try:
                         return float(text_upper) / (1024.0 * 1024.0)
                     except ValueError:
                          logging.warning(f"Unrecognized unit or non-numeric value in WeightItem: '{text}'")
                          return 0
            else:
                 try:
                      return float(text_upper) / (1024.0 * 1024.0)
                 except ValueError:
                      logging.warning(f"Could not parse WeightItem text as size: '{text}'")
                      return 0
        except Exception as e:
            logging.exception(f"Error converting WeightItem text '{text}': {e}")
            return 0

    def __lt__(self, other):
        """
        Overrides the less-than operator to compare items based on their
        normalized numerical value stored in Qt.UserRole. Allows proper numerical
        sorting in QTableWidget.
        """
        if isinstance(other, QTableWidgetItem):
            try:
                self_val = self.data(Qt.ItemDataRole.UserRole)
                other_val = other.data(Qt.ItemDataRole.UserRole)

                if self_val is not None and other_val is not None:
                    return float(self_val) < float(other_val)
                elif self_val is not None:
                     return False
                elif other_val is not None:
                     return True
                else:
                     return False
            except (ValueError, TypeError) as e:
                logging.debug(f"Error comparing WeightItems numerically ({self.text()} vs {other.text()}): {e}")
                pass

        return super().__lt__(other)
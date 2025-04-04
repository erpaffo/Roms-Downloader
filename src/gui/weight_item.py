import re
import logging # Aggiunto per logging
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
        # Tenta di convertire il testo in valore numerico all'inizializzazione
        self.value = self.convert_text_to_value(text)
        # Salva il valore normalizzato (in MiB) nel ruolo UserRole per l'ordinamento
        self.setData(Qt.ItemDataRole.UserRole, self.value)
        # Imposta il testo visualizzato (DisplayRole) per mostrare le unità originali
        # Questo è già fatto da super().__init__(text), ma riaffermarlo non nuoce
        self.setData(Qt.ItemDataRole.DisplayRole, text)
        # Allinea il testo a destra per i numeri
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
             return 0 # Gestisce input non stringa

        try:
            text_upper = text.strip().upper().replace(',', '.') # Normalizza separatore decimale
            # Regex per catturare numero (con decimali) e unità (KB, KiB, MB, MiB, GB, GiB)
            match = re.match(r"([\d\.]+)\s*([KMGT]I?B|[BKMG])?", text_upper)

            if match:
                number_str = match.group(1)
                unit = match.group(2) if match.group(2) else 'B' # Default a Byte se non c'è unità

                try:
                     number = float(number_str)
                except ValueError:
                     logging.warning(f"Could not convert number part '{number_str}' to float in WeightItem for '{text}'")
                     return 0 # Non è un numero valido

                if unit in ["GIB", "GB", "G"]:
                    return number * 1024.0
                elif unit in ["MIB", "MB", "M"]:
                    return number
                elif unit in ["KIB", "KB", "K"]:
                    return number / 1024.0
                elif unit == 'B': # Byte esplicito o implicito
                    return number / (1024.0 * 1024.0)
                else:
                     # Unità non riconosciuta, potrebbe essere solo un numero (bytes?)
                     # O un testo non valido. Tentiamo di interpretarlo come byte.
                     try:
                         return float(text_upper) / (1024.0 * 1024.0)
                     except ValueError:
                          logging.warning(f"Unrecognized unit or non-numeric value in WeightItem: '{text}'")
                          return 0 # Non numerico
            else:
                 # Nessuna corrispondenza con la regex (potrebbe essere solo testo?)
                 # Prova a convertirlo direttamente in float (assumendo bytes)
                 try:
                      return float(text_upper) / (1024.0 * 1024.0)
                 except ValueError:
                      logging.warning(f"Could not parse WeightItem text as size: '{text}'")
                      return 0 # Non è un numero
        except Exception as e:
            # Errore generico durante la conversione
            logging.exception(f"Error converting WeightItem text '{text}': {e}")
            return 0 # Ritorna 0 in caso di qualsiasi errore

    def __lt__(self, other):
        """
        Overrides the less-than operator to compare items based on their
        normalized numerical value stored in Qt.UserRole. Allows proper numerical
        sorting in QTableWidget.
        """
        if isinstance(other, QTableWidgetItem):
            try:
                # Recupera i valori numerici salvati
                self_val = self.data(Qt.ItemDataRole.UserRole)
                other_val = other.data(Qt.ItemDataRole.UserRole)

                # Assicurati che entrambi i valori siano validi (non None) e convertibili in float
                if self_val is not None and other_val is not None:
                    return float(self_val) < float(other_val)
                elif self_val is not None: # self ha valore, other no -> self è >
                     return False
                elif other_val is not None: # other ha valore, self no -> self è <
                     return True
                else: # Nessuno dei due ha valore numerico valido
                     return False # Considerali uguali in termini numerici?
            except (ValueError, TypeError) as e:
                # Errore nella conversione o comparazione, usa fallback
                logging.debug(f"Error comparing WeightItems numerically ({self.text()} vs {other.text()}): {e}")
                pass # Usa comparazione di testo standard come fallback

        # Fallback alla comparazione di testo se other non è un QTableWidgetItem
        # o se la comparazione numerica fallisce
        return super().__lt__(other)
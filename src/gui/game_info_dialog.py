import os
import json
import logging
import shutil
from PySide6.QtWidgets import (QDialog, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QTextEdit, QPushButton, QMessageBox, QFileDialog,
                               QGroupBox, QFormLayout, QScrollArea, QWidget)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from src.config import COVERS_FOLDER
from src.metadata_manager import save_metadata, get_metadata_path, delete_metadata_and_cover

class GameInfoDialog(QDialog):
    def __init__(self, game_data: dict, parent=None):
        super().__init__(parent)
        self.game_data = game_data.copy()
        self.metadata_path = get_metadata_path(self.game_data['rom_path'])
        self.is_deleted = False

        self.setWindowTitle(f"Dettagli - {self.game_data.get('title', 'Gioco')}")
        self.setMinimumWidth(600)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        main_layout = QVBoxLayout(self)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(15)

        top_h_layout = QHBoxLayout()
        top_h_layout.setSpacing(15)

        cover_v_layout = QVBoxLayout()
        self.cover_label = QLabel("Nessuna\ncopertina")
        self.cover_label.setMinimumSize(150, 150)
        self.cover_label.setMaximumSize(250, 250)
        self.cover_label.setScaledContents(False)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self._load_cover()
        cover_v_layout.addWidget(self.cover_label, 0, Qt.AlignmentFlag.AlignCenter)

        self.btn_change_cover = QPushButton("Cambia Copertina...")
        self.btn_change_cover.clicked.connect(self.change_cover)
        cover_v_layout.addWidget(self.btn_change_cover)
        cover_v_layout.addStretch(1)
        top_h_layout.addLayout(cover_v_layout, 1)


        details_group = QGroupBox("Informazioni Modificabili")
        form_layout = QFormLayout(details_group)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.title_edit = QLineEdit(self.game_data.get('title', ''))
        form_layout.addRow("Titolo:", self.title_edit)

        self.release_edit = QLineEdit(self.game_data.get('release_date', ''))
        self.release_edit.setPlaceholderText("YYYY-MM-DD")
        form_layout.addRow("Data Uscita:", self.release_edit)

        self.genres_edit = QLineEdit(", ".join(self.game_data.get('genres', [])))
        form_layout.addRow("Generi (virgola):", self.genres_edit)

        self.langs_edit = QLineEdit(", ".join(self.game_data.get('languages', [])))
        form_layout.addRow("Lingue (virgola):", self.langs_edit)

        top_h_layout.addWidget(details_group, 3)

        layout.addLayout(top_h_layout)

        desc_group = QGroupBox("Descrizione")
        desc_layout = QVBoxLayout(desc_group)
        self.desc_edit = QTextEdit(self.game_data.get('description', ''))
        self.desc_edit.setAcceptRichText(False)
        self.desc_edit.setMinimumHeight(100)
        self.desc_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        desc_layout.addWidget(self.desc_edit)
        layout.addWidget(desc_group)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 10, 0, 0)
        self.btn_delete = QPushButton(QIcon.fromTheme("edit-delete"), "Elimina Gioco")
        self.btn_delete.setStyleSheet("background-color: #FF6961; color: white;")
        self.btn_delete.clicked.connect(self.delete_game)
        bottom_layout.addWidget(self.btn_delete)
        bottom_layout.addStretch()

        self.btn_save = QPushButton(QIcon.fromTheme("document-save"), "Salva Modifiche")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self.save_changes)
        bottom_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("Annulla")
        self.btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(bottom_layout)


    def _load_cover(self):
        cover_path = self.game_data.get('cover_path')
        pixmap = QPixmap()
        if cover_path and os.path.exists(cover_path):
            if pixmap.load(cover_path):
                scaled_pixmap = pixmap.scaled(self.cover_label.maximumSize(),
                                              Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                self.cover_label.setPixmap(scaled_pixmap)
                self.cover_label.setText("")
                return
            else:
                logging.warning(f"Impossibile caricare QPixmap da: {cover_path}")

        self.cover_label.setText("Nessuna\ncopertina")
        self.cover_label.setPixmap(QPixmap())

    def change_cover(self):
        start_dir = os.path.expanduser("~")
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Seleziona Nuova Copertina", start_dir,
            "Immagini (*.png *.jpg *.jpeg *.bmp *.gif)")

        if filepath:
            if not self.metadata_path:
                 QMessageBox.critical(self, "Errore Interno", "Impossibile determinare il nome per la copertina.")
                 return

            base_name = os.path.splitext(os.path.basename(self.metadata_path))[0]
            ext = os.path.splitext(filepath)[1]
            new_cover_filename = f"{base_name}{ext}"
            new_cover_path = os.path.join(COVERS_FOLDER, new_cover_filename)

            try:
                os.makedirs(os.path.dirname(new_cover_path), exist_ok=True)

                old_cover = self.game_data.get('cover_path')
                if old_cover and os.path.exists(old_cover) and old_cover != new_cover_path \
                   and os.path.dirname(old_cover) == COVERS_FOLDER:
                    try:
                        os.remove(old_cover)
                        logging.info(f"Vecchia copertina rimossa: {old_cover}")
                    except Exception as remove_err:
                        logging.warning(f"Impossibile rimuovere vecchia copertina {old_cover}: {remove_err}")

                shutil.copy2(filepath, new_cover_path)

                self.game_data['cover_path'] = new_cover_path
                self.game_data['user_edited'] = True
                self._load_cover()
                logging.info(f"Nuova copertina selezionata e copiata in: {new_cover_path}")

            except Exception as e:
                logging.error(f"Errore nel copiare/gestire la nuova copertina da {filepath} a {new_cover_path}: {e}")
                QMessageBox.warning(self, "Errore Copertina", f"Impossibile impostare la nuova immagine:\n{e}")

    def save_changes(self):
        if not self.metadata_path:
             QMessageBox.critical(self, "Errore Interno", "Percorso metadati non valido, impossibile salvare.")
             return

        self.game_data['title'] = self.title_edit.text().strip()
        self.game_data['description'] = self.desc_edit.toPlainText().strip()
        self.game_data['release_date'] = self.release_edit.text().strip()
        self.game_data['genres'] = [g.strip() for g in self.genres_edit.text().split(',') if g.strip()]
        self.game_data['languages'] = [l.strip() for l in self.langs_edit.text().split(',') if l.strip()]
        self.game_data['user_edited'] = True

        try:
            if save_metadata(self.game_data['rom_path'], self.game_data):
                 logging.info(f"Metadati salvati per {self.game_data['rom_path']} in {self.metadata_path}")
                 self.accept()
            else:
                 QMessageBox.critical(self, "Errore Salvataggio", f"Impossibile salvare i metadati nel file:\n{self.metadata_path}")

        except Exception as e:
            logging.exception(f"Errore imprevisto nel salvataggio dei metadati in {self.metadata_path}: {e}")
            QMessageBox.critical(self, "Errore Salvataggio Imprevisto", f"Errore imprevisto durante il salvataggio:\n{e}")

    def delete_game(self):
        rom_path = self.game_data.get('rom_path')
        title = self.game_data.get('title', 'questo gioco')

        if not rom_path or not self.metadata_path:
            QMessageBox.critical(self, "Errore Interno", "Informazioni sul percorso del gioco o dei metadati mancanti.")
            return

        reply = QMessageBox.question(self, "Conferma Eliminazione",
                                     f"Sei sicuro di voler eliminare definitivamente '{title}'?\n"
                                     f"Verranno rimossi:\n"
                                     f"  - Il file ROM: {os.path.basename(rom_path)}\n"
                                     f"  - Il file metadati: {os.path.basename(self.metadata_path)}\n"
                                     f"  - La sua copertina (se presente)\n\n"
                                     f"L'operazione non è reversibile.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Cancel)

        if reply == QMessageBox.StandardButton.Yes:
            logging.info(f"Inizio eliminazione per gioco: {title} (ROM: {rom_path})")
            try:
                if os.path.exists(rom_path):
                    os.remove(rom_path)
                    logging.info(f"  - File ROM eliminato: {rom_path}")
                else:
                    logging.warning(f"  - File ROM non trovato o già eliminato: {rom_path}")
            except Exception as e:
                logging.error(f"  - Errore eliminazione ROM {rom_path}: {e}")
                QMessageBox.warning(self, "Errore Eliminazione ROM", f"Impossibile eliminare il file ROM:\n{e}")

            meta_errors = delete_metadata_and_cover(rom_path)

            if meta_errors:
                 QMessageBox.warning(self, "Eliminazione Metadati/Copertina con Errori",
                                    "Alcuni file di metadati o copertina potrebbero non essere stati eliminati:\n\n" + "\n".join(meta_errors))

            logging.info(f"Eliminazione completata per: {title}")
            self.is_deleted = True
            self.accept()

    def get_updated_data(self):
        return None if self.is_deleted else self.game_data
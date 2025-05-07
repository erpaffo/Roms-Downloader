import os
import json
import logging
import requests
import shutil
import re
from datetime import datetime, timezone
from src.config import METADATA_FOLDER, COVERS_FOLDER
from src.utils import clean_rom_title


def sanitize_filename(filename):
    """Rimuove o sostituisce caratteri non validi per i nomi di file."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", filename)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    max_len = 100
    if len(sanitized) > max_len:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[: max_len - len(ext)] + ext
    return sanitized


def get_metadata_path(rom_path):
    """Genera il percorso del file JSON di metadati basato sul percorso della ROM."""
    if not rom_path:
        return None
    rom_filename = os.path.basename(rom_path)
    sanitized_base = sanitize_filename(os.path.splitext(rom_filename)[0])
    json_filename = f"{sanitized_base}.json"
    return os.path.join(METADATA_FOLDER, json_filename)


def load_metadata(rom_path):
    """Carica i metadati dal file JSON. Restituisce un dizionario o None."""
    metadata_path = get_metadata_path(rom_path)
    if metadata_path and os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except json.JSONDecodeError:
            logging.error(f"Errore di decodifica JSON nel file: {metadata_path}")
            return None
        except Exception as e:
            logging.error(
                f"Errore nel caricamento dei metadati da {metadata_path}: {e}"
            )
            return None
    return None


def save_metadata(rom_path, data):
    """Salva il dizionario di metadati nel file JSON appropriato."""
    metadata_path = get_metadata_path(rom_path)
    if not metadata_path:
        logging.error(f"Impossibile determinare il percorso metadati per {rom_path}")
        return False
    try:
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logging.debug(f"Metadati salvati in: {metadata_path}")
        return True
    except Exception as e:
        logging.error(f"Errore nel salvataggio dei metadati in {metadata_path}: {e}")
        return False


def download_cover(image_url, rom_path):
    """Scarica una copertina e la salva nella cartella COVERS_FOLDER.
    Restituisce il percorso locale del file scaricato o None in caso di errore.
    """
    if not image_url or not rom_path:
        return None

    metadata_base = sanitize_filename(os.path.splitext(os.path.basename(rom_path))[0])
    try:
        ext = os.path.splitext(image_url.split("?")[0])[-1]
        if not ext or len(ext) > 5:
            ext = ".jpg"
    except Exception:
        ext = ".jpg"

    cover_filename = f"{metadata_base}{ext}"
    save_path = os.path.join(COVERS_FOLDER, cover_filename)

    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(1024 * 8):
                f.write(chunk)
        logging.info(f"Copertina scaricata da {image_url} a {save_path}")
        return save_path
    except requests.exceptions.RequestException as e:
        logging.error(f"Errore network scaricando {image_url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Errore generico scaricando {image_url} a {save_path}: {e}")
        return None


def delete_metadata_and_cover(rom_path):
    """Elimina il file JSON e la copertina associata a una ROM."""
    metadata_path = get_metadata_path(rom_path)
    errors = []

    # 1. Trova e cancella la copertina (potrebbe avere diverse estensioni)
    if metadata_path:
        metadata_base = os.path.splitext(metadata_path)[0]
        found_cover = False
        possible_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]
        for ext in possible_exts:
            potential_cover_path = os.path.join(
                COVERS_FOLDER, os.path.basename(metadata_base) + ext
            )
            if os.path.exists(potential_cover_path):
                try:
                    os.remove(potential_cover_path)
                    logging.info(f"File copertina eliminato: {potential_cover_path}")
                    found_cover = True
                except Exception as e:
                    err_msg = f"Errore eliminazione copertina ({os.path.basename(potential_cover_path)}): {e}"
                    errors.append(err_msg)
                    logging.error(err_msg)
        if not found_cover:
            logging.warning(
                f"Nessun file copertina trovato per {rom_path} in {COVERS_FOLDER}"
            )

    # 2. Elimina Metadati JSON
    try:
        if metadata_path and os.path.exists(metadata_path):
            os.remove(metadata_path)
            logging.info(f"File metadati eliminato: {metadata_path}")
        else:
            logging.warning(
                f"File metadati non trovato o già eliminato: {metadata_path}"
            )
    except Exception as e:
        err_msg = (
            f"Errore eliminazione metadati ({os.path.basename(metadata_path)}): {e}"
        )
        errors.append(err_msg)
        logging.error(err_msg)

    return errors


def create_placeholder_metadata(rom_path, console_name):
    """Crea un dizionario di metadati placeholder."""
    cleaned_title = clean_rom_title(os.path.basename(rom_path))
    data = {
        "rom_path": rom_path,
        "original_filename": os.path.basename(rom_path),
        "console": console_name,
        "title": cleaned_title,
        "cover_path": None,
        "description": "Informazioni non disponibili.",
        "release_date": "N/D",
        "genres": [],
        "languages": [],
        "last_scrape_attempt": datetime.now(timezone.utc).isoformat(),
        "scrape_success": False,
        "user_edited": False,
    }
    return data

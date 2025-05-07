import json
import logging
import os
import time
from datetime import datetime
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz

from src.config import BASE_URL, CACHE_FOLDER, CONSOLES
from src.mapping import apply_title_term_map, simplify_title
from src.utils import clean_rom_title


def get_console_url(console_name):
    return BASE_URL + CONSOLES.get(console_name, "")


def parse_size_string(size_str):
    try:
        parts = size_str.split()
        if len(parts) >= 2:
            value = float(parts[0].replace(",", "."))
            unit = parts[1].lower()
            if unit.startswith("mib"):
                return int(value * 1024 * 1024)
            elif unit.startswith("mb"):
                return int(value * 1000 * 1000)
            elif unit.startswith("kib"):
                return int(value * 1024)
            elif unit.startswith("kb"):
                return int(value * 1000)
            else:
                return int(value)
        return 0
    except Exception as e:
        logging.error(f"Errore nel parsing della dimensione '{size_str}': {e}")
        return 0


def get_games_for_console(console_name):
    url = get_console_url(console_name)
    logging.info(f"Inizio scraping per console '{console_name}' all'URL: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    games = []
    rows = soup.find_all("tr")
    for idx, row in enumerate(rows):
        link_td = row.find("td", class_="link")
        if not link_td:
            continue
        a_tag = link_td.find("a", href=True)
        if not a_tag:
            continue
        href = a_tag["href"]
        full_link = urljoin(url, href)
        file_name = unquote(a_tag.get("title", os.path.basename(full_link)))
        name, _ = os.path.splitext(file_name)
        size_td = row.find("td", class_="size")
        size_text = size_td.text.strip() if size_td else "0 MB"
        size_bytes = parse_size_string(size_text)
        game = {
            "name": name,
            "link": full_link,
            "size_bytes": size_bytes,
            "size_str": size_text,
            "console": console_name,
        }
        games.append(game)
        if idx % 100 == 0 and idx > 0:
            logging.debug(f"Processati {idx} giochi...")
    logging.info(f"Scraping completato: trovati {len(games)} giochi")
    return games


def get_games_for_console_cached(console_name):
    filename = os.path.join(CACHE_FOLDER, f"cache_{console_name}.json")
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                games = json.load(f)
            logging.info(f"Cache caricata per console '{console_name}'")
            for game in games:
                if "console" not in game:
                    game["console"] = console_name
            return games
        except Exception as e:
            logging.error(f"Errore nel caricamento della cache: {e}")
    games = get_games_for_console(console_name)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(games, f, ensure_ascii=False, indent=4)
        logging.info(f"Cache salvata per console '{console_name}'")
    except Exception as e:
        logging.error(f"Errore nel salvataggio della cache: {e}")
    return games


class GameApiClient:
    def __init__(self):
        self.twitch_client_id = os.getenv("TWITCH_CLIENT_ID")
        self.twitch_client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        self.rawg_api_key = os.getenv("RAWG_API_KEY")

        if not self.twitch_client_id or not self.twitch_client_secret:
            logging.warning(
                "Credenziali Twitch (Client ID/Secret) non trovate nelle variabili d'ambiente. Le ricerche IGDB falliranno."
            )
        if not self.rawg_api_key:
            logging.warning(
                "API Key RAWG non trovata nelle variabili d'ambiente. Le ricerche RAWG falliranno."
            )

        self.twitch_token = None
        self.token_expiry_time = 0
        self.twitch_token_url = "https://id.twitch.tv/oauth2/token"
        self.igdb_api_url = "https://api.igdb.com/v4"

    def _get_twitch_token(self):
        if not self.twitch_client_id or not self.twitch_client_secret:
            logging.error(
                "Impossibile ottenere token Twitch: Client ID o Secret mancanti."
            )
            return False

        if self.twitch_token and time.time() < self.token_expiry_time - 60:
            logging.debug("Token Twitch esistente ancora valido.")
            return True

        logging.info("Richiesta nuovo token di accesso Twitch...")
        payload = {
            "client_id": self.twitch_client_id,
            "client_secret": self.twitch_client_secret,
            "grant_type": "client_credentials",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = requests.post(
                self.twitch_token_url, data=payload, headers=headers, timeout=10
            )
            response.raise_for_status()
            token_data = response.json()

            self.twitch_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in")

            if not self.twitch_token or not expires_in:
                logging.error(f"Risposta token Twitch non valida: {token_data}")
                self.twitch_token = None
                return False

            self.token_expiry_time = time.time() + expires_in
            logging.info(
                f"Nuovo token Twitch ottenuto, valido per circa {expires_in // 3600} ore."
            )
            return True

        except requests.exceptions.RequestException as e:
            logging.error(f"Errore richiesta token Twitch: {e}")
            self.twitch_token = None
            return False
        except json.JSONDecodeError:
            logging.error(
                f"Errore decodifica risposta JSON token Twitch: {response.text}"
            )
            self.twitch_token = None
            return False

    def _make_igdb_request(self, endpoint, query_body):
        if not self._get_twitch_token():
            return None

        headers = {
            "Client-ID": self.twitch_client_id,
            "Authorization": f"Bearer {self.twitch_token}",
        }
        full_url = f"{self.igdb_api_url}/{endpoint}"

        try:
            response = requests.post(
                full_url, headers=headers, data=query_body.encode("utf-8"), timeout=15
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Errore richiesta IGDB a '{endpoint}': {e}")
            return None
        except json.JSONDecodeError:
            logging.error(
                f"Errore decodifica risposta JSON IGDB da '{endpoint}': {response.text}"
            )
            return None

    def search_igdb(self, title, platform_name=None):
        if not self.twitch_client_id:
            return None
        platform_id = IGDB_PLATFORM_MAP.get(platform_name)
        query = f"""
            fields name, summary, first_release_date, genres.name, cover.url;
            search "{title}";
            limit 5;
            """
        if platform_id:
            query += f" where platforms = ({platform_id});"
        else:
            logging.warning(
                f"[IGDB] ID piattaforma non trovato per '{platform_name}', ricerca senza filtro piattaforma."
            )

        results = self._make_igdb_request("games", query)

        if not results:
            logging.info(f"[IGDB] Nessun risultato per '{title}'")
            return None

        game = results[0]
        logging.info(f"[IGDB] Trovato risultato per '{title}': {game.get('name')}")

        cover_url = game.get("cover", {}).get("url")
        if cover_url:
            cover_url = "https:" + cover_url.replace("t_thumb", "t_cover_big")

        release_ts = game.get("first_release_date")
        release_date_str = (
            datetime.fromtimestamp(release_ts).strftime("%Y-%m-%d")
            if release_ts
            else None
        )

        genres = [g.get("name") for g in game.get("genres", []) if g.get("name")]

        return {
            "api_source": "IGDB",
            "api_title": game.get("name"),
            "description": game.get("summary"),
            "release_date": release_date_str,
            "genres": genres,
            "languages": [],
            "cover_url": cover_url,
        }

    def search_rawg(self, title, platform_name=None):
        if not self.rawg_api_key:
            return None

        base_url = "https://api.rawg.io/api/games"
        platform_id = RAWG_PLATFORM_MAP.get(platform_name)
        params = {"key": self.rawg_api_key, "search": title, "page_size": 1}
        if platform_id:
            params["platforms"] = platform_id
        else:
            logging.warning(
                f"[RAWG] ID piattaforma non trovato per '{platform_name}', ricerca senza filtro piattaforma."
            )

        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data and data.get("results"):
                game = data["results"][0]
                logging.info(
                    f"[RAWG] Trovato risultato per '{title}': {game.get('name')}"
                )

                release_date_str = game.get("released")
                genres = [
                    g.get("name") for g in game.get("genres", []) if g.get("name")
                ]
                cover_url = game.get("background_image")
                description = f"Descrizione non recuperata da RAWG (richiede chiamata addizionale all'ID: {game.get('id')})"

                return {
                    "api_source": "RAWG",
                    "api_title": game.get("name"),
                    "description": description,
                    "release_date": release_date_str,
                    "genres": genres,
                    "languages": [],
                    "cover_url": cover_url,
                }
            else:
                logging.info(f"[RAWG] Nessun risultato per '{title}'")
                return None

        except requests.exceptions.RequestException as e:
            logging.error(f"Errore richiesta RAWG per '{title}': {e}")
            return None
        except json.JSONDecodeError:
            logging.error(
                f"Errore decodifica risposta JSON RAWG per '{title}': {response.text}"
            )
            return None


game_api_client_instance = GameApiClient()


def fetch_game_details(original_filename, console_name):
    if not original_filename:
        return None

    # Assume clean_rom_title, apply_title_term_map, simplify_title sono definite/importate
    cleaned_title = clean_rom_title(original_filename)
    if not cleaned_title:
        logging.warning(f"[API Fetch] Titolo pulito vuoto per '{original_filename}'")
        return None

    logging.info(
        f"[API Fetch] Inizio ricerca per '{original_filename}' -> Pulito: '{cleaned_title}'"
    )

    search_attempts = []
    search_attempts.append(cleaned_title)
    mapped_title = apply_title_term_map(cleaned_title)
    if mapped_title.lower() != cleaned_title.lower():
        search_attempts.append(mapped_title)
    simplified = simplify_title(cleaned_title)
    if simplified != cleaned_title and simplified.lower() not in [
        t.lower() for t in search_attempts
    ]:
        search_attempts.append(simplified)
    if " - " in cleaned_title:
        base_title = cleaned_title.split(" - ")[0].strip()
        if base_title != cleaned_title and base_title.lower() not in [
            t.lower() for t in search_attempts
        ]:
            search_attempts.append(base_title)

    seen = set()
    unique_attempts = []
    for item in search_attempts:
        lowered = item.lower()
        if lowered not in seen:
            seen.add(lowered)
            unique_attempts.append(item)

    logging.debug(f"[API Fetch] Tentativi di ricerca ordinati: {unique_attempts}")

    MIN_SIMILARITY_THRESHOLD = 80

    for attempt_title in unique_attempts:
        logging.debug(
            f"[API Fetch] Tentativo IGDB con '{attempt_title}' (Console: {console_name})..."
        )
        igdb_details = game_api_client_instance.search_igdb(attempt_title, console_name)
        if igdb_details:
            api_title = igdb_details.get("api_title", "")
            similarity_score = fuzz.token_set_ratio(
                attempt_title.lower(), api_title.lower()
            )
            logging.debug(
                f"[API Validation IGDB] Confronto: '{attempt_title}' vs API '{api_title}' -> Score: {similarity_score}"
            )
            if similarity_score >= MIN_SIMILARITY_THRESHOLD:
                logging.info(
                    f"[API Fetch] SUCCESSO (IGDB): Trovato '{api_title}' con score {similarity_score} >= {MIN_SIMILARITY_THRESHOLD}"
                )
                return igdb_details
            else:
                logging.warning(
                    f"[API Fetch] RISULTATO SCARTATO (IGDB): API ha trovato '{api_title}', ma similarità ({similarity_score}) troppo bassa rispetto a '{attempt_title}'."
                )

        logging.debug(
            f"[API Fetch] Tentativo RAWG con '{attempt_title}' (Console: {console_name})..."
        )
        rawg_details = game_api_client_instance.search_rawg(attempt_title, console_name)
        if rawg_details:
            api_title = rawg_details.get("api_title", "")
            similarity_score = fuzz.token_set_ratio(
                attempt_title.lower(), api_title.lower()
            )
            logging.debug(
                f"[API Validation RAWG] Confronto: '{attempt_title}' vs API '{api_title}' -> Score: {similarity_score}"
            )
            if similarity_score >= MIN_SIMILARITY_THRESHOLD:
                logging.info(
                    f"[API Fetch] SUCCESSO (RAWG): Trovato '{api_title}' con score {similarity_score} >= {MIN_SIMILARITY_THRESHOLD}"
                )
                return rawg_details
            else:
                logging.warning(
                    f"[API Fetch] RISULTATO SCARTATO (RAWG): API ha trovato '{api_title}', ma similarità ({similarity_score}) troppo bassa rispetto a '{attempt_title}'."
                )

    logging.warning(
        f"[API Fetch] FALLIMENTO TOTALE: Nessun risultato valido trovato per '{original_filename}' dopo tutti i tentativi e validazioni."
    )
    return None


IGDB_PLATFORM_MAP = {
    "Nintendo DS": 20,
    "Nintendo Game Boy Advance": 24,
    "Sony PlayStation": 7,
}
RAWG_PLATFORM_MAP = {
    "Nintendo DS": 27,
    "Nintendo Game Boy Advance": 26,
    "PlayStation": 1,
}

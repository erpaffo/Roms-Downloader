import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from src.config import BASE_URL, CONSOLES
import logging

def get_console_url(console_name):
    return BASE_URL + CONSOLES.get(console_name, "")

def parse_size_string(size_str):
    try:
        parts = size_str.split()
        if len(parts) >= 2:
            value = float(parts[0].replace(',', '.'))
            unit = parts[1].lower()
            if unit.startswith('mib'):
                return int(value * 1024 * 1024)
            elif unit.startswith('mb'):
                return int(value * 1000 * 1000)
            elif unit.startswith('kib'):
                return int(value * 1024)
            elif unit.startswith('kb'):
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
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    games = []
    rows = soup.find_all('tr')
    for idx, row in enumerate(rows):
        link_td = row.find('td', class_='link')
        if not link_td:
            continue
        a_tag = link_td.find('a', href=True)
        if not a_tag:
            continue
        href = a_tag['href']
        full_link = urljoin(url, href)
        file_name = unquote(a_tag.get('title', os.path.basename(full_link)))
        name, _ = os.path.splitext(file_name)
        size_td = row.find('td', class_='size')
        size_text = size_td.text.strip() if size_td else "0 MB"
        size_bytes = parse_size_string(size_text)
        game = {
            'name': name,
            'link': full_link,
            'size_bytes': size_bytes,
            'size_str': size_text,
            'console': console_name
        }
        games.append(game)
        if idx % 100 == 0 and idx > 0:
            logging.debug(f"Processati {idx} giochi...")
    logging.info(f"Scraping completato: trovati {len(games)} giochi")
    return games


def get_games_for_console_cached(console_name):
    filename = f"cache_{console_name}.json"
    games = None
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                games = json.load(f)
            logging.info(f"Cache caricata per console '{console_name}'")
            for game in games:
                if 'console' not in game:
                    game['console'] = console_name
            return games
        except Exception as e:
            logging.error(f"Errore nel caricamento della cache: {e}")
    games = get_games_for_console(console_name)
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(games, f, ensure_ascii=False, indent=4)
        logging.info(f"Cache salvata per console '{console_name}'")
    except Exception as e:
        logging.error(f"Errore nel salvataggio della cache: {e}")
    return games


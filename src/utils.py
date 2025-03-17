import re

ALLOWED_NATIONS = {"Japan", "USA", "Europe", "Spain", "Italy", "Germany", "France", "China", "Canada"}

def extract_nations(game_name):
    pattern = r'\((.*?)\)'
    match = re.search(pattern, game_name)
    if match:
        nations_str = match.group(1)
        nations = [s.strip() for s in nations_str.split(',')]
        return [nation for nation in nations if nation in ALLOWED_NATIONS]
    return []

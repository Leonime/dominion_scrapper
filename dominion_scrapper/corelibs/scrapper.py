import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


class Scrapper:
    def __init__(self):
        self.base_url = 'https://wiki.dominionstrategy.com/'

    def get_expansions_urls(self):
        url = self.base_url + 'index.php/Expansion'
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'class': 'wikitable'})
            if table:
                return [row.find('td').find('a').get('href') for row in table.find_all('tr')[1:] if
                        row.find('td').find('a')]

    def get_cards(self):
        url = self.base_url + 'index.php/List_of_cards'
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'class': 'wikitable'})
            if table:
                rows = table.find_all('tr')
                expansions = {}
                for row in rows[1:]:
                    cells = row.find_all(['th', 'td'])
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    card = {
                        'name': row_data[0].strip(),
                        'type': row_data[2].strip(),
                        'cost': row_data[3].strip(),
                        'text': row_data[4].strip(),
                    }
                    expansion = row_data[1].split(',')
                    if len(expansion) > 1:
                        exp_name = expansion[0].strip()
                        exp_edition = expansion[1].strip()
                    else:
                        exp_name = expansion[0]
                        exp_edition = '1E'
                    if exp_name not in expansions:
                        expansions[exp_name] = {
                            'name': exp_name,
                            'cards': []
                        }
                        card['edition'] = exp_edition
                        expansions[exp_name]['cards'].append(card)
                    else:
                        card['edition'] = exp_edition
                        expansions[exp_name]['cards'].append(card)

                    print(card['name'])
                folder_path = Path('output')
                folder_path.mkdir(parents=True, exist_ok=True)
                with open(folder_path / 'dominion_cards.json', 'w') as f:
                    json.dump(expansions, f, indent=4)

    def run(self):
        links = self.get_expansions_urls()
        for link in links:
            print(link)

        self.get_cards()

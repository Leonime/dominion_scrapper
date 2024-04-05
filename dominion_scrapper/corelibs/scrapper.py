import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup


class Scrapper:
    def __init__(self):
        self.base_url = 'https://wiki.dominionstrategy.com/'

    def get_soup(self, url):
        url = url[1:] if url.startswith('/') else url
        complete_url = self.base_url + url
        response = requests.get(complete_url)
        if response.status_code == 200:
            return BeautifulSoup(response.content, 'html.parser')
        return None

    def get_card_languages(self, url):
        soup = self.get_soup(url)
        languages = {}
        if soup:
            table = soup.find('table', {'class': 'wikitable mw-collapsible autocollapse'})
            if table:
                rows = table.find_all('tr')
                i_lan, i_name, i_text = None, None, None
                for i, cell in enumerate(rows[0].find_all('th')):
                    if cell.get_text(strip=True) == 'Language':
                        i_lan = i
                    if cell.get_text(strip=True) == 'Name':
                        i_name = i
                    if cell.get_text(strip=True) == 'Text':
                        i_text = i

                for row in rows[1:]:
                    if i_lan is not None and i_name is not None and i_text is not None:
                        cells = row.find_all(['th', 'td'])
                        row_data = [cell.get_text(strip=True) for cell in cells]
                        if row_data and len(row_data) > i_text:
                            language = row_data[i_lan].strip()
                            if language not in languages:
                                languages[language] = {
                                    'language': row_data[0].strip(),
                                }
                            languages[language]['name'] = row_data[i_name].strip()
                            languages[language]['text'] = row_data[i_text].strip()
                    else:
                        continue
        return languages

    def get_expansions_urls(self):
        soup = self.get_soup('index.php/Expansion')
        if soup:
            table = soup.find('table', {'class': 'wikitable'})
            if table:
                return [row.find('td').find('a').get('href') for row in table.find_all('tr')[1:] if
                        row.find('td').find('a')]

    def get_cards(self):
        soup = self.get_soup('index.php/List_of_cards')
        if soup:
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
                    card_url = cells[0].find('a').get('href')

                    print(card['name'])
                    languages = self.get_card_languages(card_url)
                    if languages:
                        card['languages'] = languages
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
                folder_path = Path('output')
                folder_path.mkdir(parents=True, exist_ok=True)
                with open(folder_path / 'dominion_cards.json', 'w') as f:
                    json.dump(expansions, f, indent=4)

    def run(self):
        self.get_cards()

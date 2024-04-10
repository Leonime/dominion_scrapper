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

    def get_costs(self, cell):
        results = []
        cost = {}
        images = cell.find_all('img')
        for img in images:
            alt = img.get('alt').strip()
            img_url = img.get('src').strip()
            img_url = img_url[1:] if img_url.startswith('/') else img_url
            if '$' in alt and all(subs not in alt for subs in ['star', 'plus']):
                cost['treasure'] = {
                    'symbol': '$',
                    'value': int(alt[1:])
                }
                results.append(cost)
            elif 'P' in alt:
                cost['potion'] = {
                    'symbol': 'P',
                    'value': 0
                }
                results.append(cost)
            elif 'D' in alt:
                cost['debt'] = {
                    'symbol': 'D',
                    'value': int(alt.replace('D', ''))
                }
                results.append(cost)
            elif '$' in alt and 'star' in alt:
                cost['star'] = {
                    'symbol': '$',
                    'value': int(alt.replace('$', '').replace('star', '')),
                    'star': '*',
                }
                results.append(cost)
            elif '$' in alt and 'plus' in alt:
                cost['plus'] = {
                    'symbol': '$',
                    'value': int(alt.replace('$', '').replace('plus', '')),
                    'plus': '+',
                }
                results.append(cost)
            response = requests.get(self.base_url + img_url)
            if response.status_code == 200:
                folder_path = Path('output') / 'images' / 'assets'
                folder_path.mkdir(parents=True, exist_ok=True)
                folder_path = folder_path / f'{alt}.png'
                if not folder_path.exists():
                    with open(folder_path, 'wb') as f:
                        f.write(response.content)
        return results

    def get_image(self, cell, card):
        images = cell.find('img')
        img_url = images.get('src')
        img_url = img_url[1:] if img_url.startswith('/') else img_url
        response = requests.get(self.base_url + img_url)
        if response.status_code == 200:
            folder_path = Path('output') / 'images' / 'expansions' / f'{card['expansion']}'
            folder_path.mkdir(parents=True, exist_ok=True)
            with open(folder_path / f'{card["name"]}.jpg', 'wb') as f:
                f.write(response.content)

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
                    costs = self.get_costs(cells[3])
                    card = {
                        'name': row_data[0].strip(),
                        'types': [substring.strip() for substring in row_data[2].split('-')],
                        'costs': costs,
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
                        card['expansion'] = exp_name
                        expansions[exp_name]['cards'].append(card)
                    else:
                        card['edition'] = exp_edition
                        card['expansion'] = exp_name
                        expansions[exp_name]['cards'].append(card)
                    self.get_image(cells[0], card)
                folder_path = Path('output')
                folder_path.mkdir(parents=True, exist_ok=True)
                with open(folder_path / 'dominion_cards.json', 'w') as f:
                    json.dump(expansions, f, indent=4)

    def run(self):
        self.get_cards()

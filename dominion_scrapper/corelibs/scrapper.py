import json
import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from bs4 import BeautifulSoup
from colorama import Fore, Style


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
            tables = soup.find_all('table', {'class': 'wikitable'})
            if tables:
                for table in tables:
                    rows = table.find_all('tr')
                    i_lan, i_name, i_text = None, None, None
                    match = 0
                    for i, cell in enumerate(rows[0].find_all('th')):
                        if cell.get_text(strip=True) == 'Language':
                            match += 1
                            i_lan = i
                        if cell.get_text(strip=True) == 'Name':
                            match += 1
                            i_name = i
                        if cell.get_text(strip=True) == 'Text':
                            match += 1
                            i_text = i

                    if match != 3:
                        continue
                    if i_lan is not None and i_name is not None and i_text is not None:
                        for row in rows[1:]:
                            cells = row.find_all(['th', 'td'])
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            if row_data and len(row_data) > i_text:
                                language = row_data[i_lan].strip()
                                if language not in languages:
                                    languages[language] = {
                                        'language': row_data[0].strip(),
                                    }
                                languages[language]['name'] = row_data[i_name].strip()
                                languages[language]['text'] = self.clean_text(cells[i_text])
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
            alt, folder_path, image = self.get_image_data(img)
            if '$' in alt and all(subs not in alt for subs in ['star', 'plus']):
                cost['treasure'] = {
                    'symbol': '$',
                    'value': int(alt[1:]),
                    'alt': alt,
                    'image': image,
                    'folder_path': str(folder_path)
                }
                results.append(cost)
            elif 'P' in alt:
                cost['potion'] = {
                    'symbol': 'P',
                    'value': 0,
                    'alt': alt,
                    'image': image,
                    'folder_path': str(folder_path)
                }
                results.append(cost)
            elif 'D' in alt:
                cost['debt'] = {
                    'symbol': 'D',
                    'value': int(alt.replace('D', '')),
                    'alt': alt,
                    'image': image,
                    'folder_path': str(folder_path)
                }
                results.append(cost)
            elif '$' in alt and 'star' in alt:
                cost['star'] = {
                    'symbol': '$',
                    'value': int(alt.replace('$', '').replace('star', '')),
                    'star': '*',
                    'alt': alt,
                    'image': image,
                    'folder_path': str(folder_path)
                }
                results.append(cost)
            elif '$' in alt and 'plus' in alt:
                cost['plus'] = {
                    'symbol': '$',
                    'value': int(alt.replace('$', '').replace('plus', '')),
                    'plus': '+',
                    'alt': alt,
                    'image': image,
                    'folder_path': str(folder_path)
                }
                results.append(cost)
        return results

    def get_image_data(self, img):
        alt = img.get('alt').strip()
        img_url = img.get('src').strip()
        img_url = img_url[1:] if img_url.startswith('/') else img_url
        folder_path = Path('output') / 'images' / 'assets'
        image = self.save_image(alt, img_url, folder_path)
        return alt, folder_path, image

    def save_image(self, alt, img_url, folder_path):
        response = requests.get(self.base_url + img_url)
        if response.status_code == 200:
            img_data = BytesIO(response.content)
            img = Image.open(img_data)
            width = img.width
            folder_path.mkdir(parents=True, exist_ok=True)
            file_name = f'{alt}_{width}px.png'
            folder_path = folder_path / file_name
            if not folder_path.exists():
                with open(folder_path, 'wb') as f:
                    f.write(response.content)
            return file_name
        return ''

    def get_image(self, cell, card):
        image = cell.find('img')
        alt = image.get('alt').strip()
        img_url = image.get('src')
        img_url = img_url[1:] if img_url.startswith('/') else img_url
        folder_path = Path('output') / 'images' / 'expansions' / f'{card['expansion']}'
        return {
            'alt': alt,
            'folder_path': str(folder_path),
            'image': self.save_image(alt, img_url, folder_path)
        }

    def clean_text(self, cell):
        images = cell.find_all('img')
        raw_text = cell.prettify()
        images_list = []
        if images:
            for img in images:
                alt, folder_path, image = self.get_image_data(img)
                raw_img = img.prettify() if img else None
                raw_text = raw_text.replace(raw_img, f'{{{{{image}}}}} ')
                images_list.append({
                    'image': image,
                    'alt': alt,
                    'folder_path': str(folder_path)
                })
        soup = BeautifulSoup(raw_text, 'html.parser')
        td = soup.find('td')
        text = {
            'text': td.get_text(strip=True).replace('}}', '}} '),
            'images': images_list
        }
        return text

    def progress(self, card, start, end):
        done = int(30 * start / end)
        sys.stdout.write(
            f'\r[{Fore.GREEN + ("█" * done)}'
            f'{Fore.BLACK + ("█" * (30 - done)) + Style.RESET_ALL}]'
            f' scraping {start} of {end} currently: "{card}"')
        sys.stdout.flush()

    def get_effects(self, soup):
        div_effects = soup.find('div', {'id': 'mw-content-text'})
        if div_effects:
            li_effects = div_effects.find_all('li')
            if li_effects:
                for li in li_effects:

    def get_cards(self):
        soup = self.get_soup('index.php/List_of_cards')
        if soup:
            effects = self.get_effects(soup)
            table = soup.find('table', {'class': 'wikitable'})
            if table:
                rows = table.find_all('tr')
                expansions = {}
                total = len(rows[1:])
                for i, row in enumerate(rows[1:]):
                    cells = row.find_all(['th', 'td'])
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    costs = self.get_costs(cells[3])
                    text = self.clean_text(cells[4])
                    card = {
                        'name': row_data[0].strip(),
                        'types': [substring.strip() for substring in row_data[2].split('-')],
                        'costs': costs,
                        'text': text,
                    }
                    card_url = cells[0].find('a').get('href')

                    self.progress(card['name'], i + 1, total)
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
                    else:
                        card['edition'] = exp_edition
                        card['expansion'] = exp_name
                    image = self.get_image(cells[0], card)
                    if image:
                        card['image'] = image
                    expansions[exp_name]['cards'].append(card)
                folder_path = Path('output')
                folder_path.mkdir(parents=True, exist_ok=True)
                with open(folder_path / 'dominion_cards.json', 'w') as f:
                    json.dump(expansions, f, indent=4)

    def run(self):
        self.get_cards()

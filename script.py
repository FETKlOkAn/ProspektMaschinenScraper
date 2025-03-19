#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraper pre ziskanie letakov z webu prospektmaschine.de
"""

import json
import datetime
import logging
import time
import re

from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

import requests

class ProspektMaschinenScraper:
    """Trieda na ziskanie letakov z webu prospektmaschine.de"""

    BASE_URL = "https://www.prospektmaschine.de"
    HYPERMARKETS_PATH = "/hypermarkte/"
    
    def __init__(self, output_file: str = "brochures.json"):
        """Inicializacia scrapera
        
        Args:
            output_file: Nazov vystupneho suboru
        """
        self.output_file = output_file
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        self.configure_logging()
        
    def configure_logging(self) -> None:
        """Konfiguracia logovania"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("scraper.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Ziskanie obsahu stranky
        
        Args:
            url: URL stranky na ziskanie
            
        Returns:
            BeautifulSoup objekt alebo None v pripade chyby
        """
        try:
            self.logger.info("Nacitavam stranku: %s", url)
            response = self.session.get(url, headers=self.headers)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except requests.exceptions.RequestException as e:
            self.logger.error("Chyba pri ziskavani stranky %s: %s", url, e)
            return None
    
    def parse_date(self, date_str: str) -> tuple:
        """Extrakcia datumov z textu
        
        Args:
            date_str: Retazec obsahujuci datumy
            
        Returns:
            Tuple (valid_from, valid_to)
        """
        try:
            # Rozdelenie textu na datumy
            parts = date_str.strip().split('-')
            
            if len(parts) != 2:
                self.logger.warning("Neocakavany format datumu: %s", date_str)
                return None, None
            
            # Extrakcia a parsovanie datumov
            date_from_str = parts[0].strip()
            date_to_str = parts[1].strip()
            
            # Format datumov: DD.MM.YYYY alebo DD.MM.
            date_pattern_full = r'(\d{2})\.(\d{2})\.(\d{4})'
            date_pattern_short = r'(\d{2})\.(\d{2})\.'
            
            # Skusime najprv plny format
            from_match_full = re.search(date_pattern_full, date_from_str)
            to_match_full = re.search(date_pattern_full, date_to_str)
            
            if from_match_full and to_match_full:
                from_day, from_month, from_year = from_match_full.groups()
                to_day, to_month, to_year = to_match_full.groups()
                valid_from = f"{from_year}-{from_month}-{from_day}"
                valid_to = f"{to_year}-{to_month}-{to_day}"
                return valid_from, valid_to
            
            # Ak plny format nefunguje, skusime kratky format
            from_match_short = re.search(date_pattern_short, date_from_str)
            to_match_short = re.search(date_pattern_short, date_to_str)
            
            if from_match_short and to_match_short:
                from_day, from_month = from_match_short.groups()
                to_day, to_month = to_match_short.groups()
                # Predpokladame aktualny rok alebo hladame ho v texte
                current_year = str(datetime.datetime.now().year)
                
                # Skusime najst rok v texte
                year_match = re.search(r'(\d{4})', date_str)
                year = year_match.group(1) if year_match else current_year
                
                valid_from = f"{year}-{from_month}-{from_day}"
                valid_to = f"{year}-{to_month}-{to_day}"
                return valid_from, valid_to
            
            self.logger.warning("Nepodarilo sa extrahovat datumy z: %s", date_str)
            return None, None
        except Exception as e:
            self.logger.error("Chyba pri parsovani datumu %s: %s", date_str, e)
            return None, None
    
    def get_hypermarket_links(self) -> List[Dict[str, str]]:
        """Ziskanie zoznamu hypermarketov
        
        Returns:
            Zoznam slovnikov s URL a nazvom hypermarketu
        """
        hypermarkets = []
        
        soup = self.get_page_content(urljoin(self.BASE_URL, self.HYPERMARKETS_PATH))
        if not soup:
            self.logger.error("Nepodarilo sa ziskat zoznam hypermarketov")
            return hypermarkets
        
        categories = soup.find("ul", class_="list-unstyled categories")
        if not categories:
            self.logger.error("Nepodarilo sa najst kategorie na stranke")
            return hypermarkets
        
        for link in categories.find_all("a"):
            hypermarkets.append({
                "url": link.get("href"),
                "name": link.text.strip()
            })
        
        self.logger.info("Najdenych %d hypermarketov", len(hypermarkets))
        return hypermarkets
    
    def extract_brochure_data(self, brochure, shop_name: str) -> Optional[Dict[str, Any]]:
        """Extrahovanie dat z letaku
        
        Args:
            brochure: BeautifulSoup element letaku
            shop_name: Nazov obchodu
            
        Returns:
            Slovnik s datami o letaku alebo None v pripade chyby
        """
        try:
            # Kontrola, ci je letak platny (nie je oznaceny ako stary)
            if brochure.find("div", class_="grid-item-old"):
                return None
            
            # Ziskanie nadpisu letaku
            title_element = brochure.find("strong")
            if not title_element:
                self.logger.warning("Chyba nadpis letaku pre obchod %s", shop_name)
                return None
            title = title_element.text.strip()
            
            # Ziskanie obrazku letaku - upravena metoda pre lazy loading
            img_element = brochure.find("img", class_="lazyloadBrochure")
            if img_element and img_element.get("data-src"):
                thumbnail = img_element.get("data-src")
            else:
                # Skusime alternativne metody
                img_element = brochure.find("img")
                if not img_element:
                    self.logger.warning("Chyba thumbnail letaku pre obchod %s", shop_name)
                    return None
                
                # Skusime src alebo data-src
                thumbnail = img_element.get("src") or img_element.get("data-src")
                if not thumbnail:
                    self.logger.warning("Chyba URL thumbnailov pre obchod %s", shop_name)
                    return None
            
            # Ak URL nie je absolutna, doplnime BASE_URL
            if not thumbnail.startswith(('http://', 'https://')):
                thumbnail = urljoin(self.BASE_URL, thumbnail)
            
            # Ziskanie datumov platnosti
            date_element = brochure.find("small", class_="visible-sm")
            if not date_element:
                # Skusime alternativne triedy
                date_element = brochure.find("small", class_="hidden-sm")
                if not date_element:
                    self.logger.warning("Chybaju datumy platnosti letaku pre obchod %s", shop_name)
                    return None
            
            valid_from, valid_to = self.parse_date(date_element.text.strip())
            if not valid_from or not valid_to:
                return None
            
            # Vytvorenie slovnika s datami letaku
            return {
                "title": title,
                "thumbnail": thumbnail,
                "shop_name": shop_name,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "parsed_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            self.logger.error("Chyba pri extrakcii dat letaku pre obchod %s: %s", shop_name, e)
            return None
    
    def get_brochures_for_shop(self, shop_url: str, shop_name: str) -> List[Dict[str, Any]]:
        """Ziskanie letakov pre konkretny obchod
        
        Args:
            shop_url: URL obchodu
            shop_name: Nazov obchodu
            
        Returns:
            Zoznam slovnikov s datami letakov
        """
        brochures = []
        
        full_url = urljoin(self.BASE_URL, shop_url)
        self.logger.info("Spracovavam obchod %s, URL: %s", shop_name, full_url)
        
        soup = self.get_page_content(full_url)
        if not soup:
            self.logger.error("Nepodarilo sa ziskat stranku obchodu %s", shop_name)
            return brochures
        
        # Hladame brochures
        brochure_elements = soup.find_all("div", class_="brochure-thumb")
        self.logger.info("Najdenych %d letakov pre obchod %s", len(brochure_elements), shop_name)
        
        for brochure in brochure_elements:
            brochure_data = self.extract_brochure_data(brochure, shop_name)
            if brochure_data:
                brochures.append(brochure_data)
                self.logger.info("Extrahovany letakovy data pre %s: %s (%s - %s)", 
                               shop_name, brochure_data['title'], 
                               brochure_data['valid_from'], brochure_data['valid_to'])
            else:
                self.logger.warning("Nepodarilo sa extrahovat data z letaku pre obchod %s", shop_name)
        
        return brochures
    
    def scrape_all_hypermarkets(self) -> List[Dict[str, Any]]:
        """Ziskanie letakov pre vsetky hypermarkety
        
        Returns:
            Zoznam slovnikov s datami letakov pre vsetky obchody
        """
        all_brochures = []
        hypermarkets = self.get_hypermarket_links()
        
        for i, hypermarket in enumerate(hypermarkets):
            self.logger.info("Spracovavam obchod %s (%d/%d)", 
                           hypermarket['name'], i+1, len(hypermarkets))
            brochures = self.get_brochures_for_shop(hypermarket['url'], hypermarket['name'])
            all_brochures.extend(brochures)
            
            # Pridanie pauzy medzi poziadavkami
            if i < len(hypermarkets) - 1:
                time.sleep(1)
        
        return all_brochures
    
    def save_to_json(self, data: List[Dict[str, Any]]) -> None:
        """Ulozenie dat do JSON suboru
        
        Args:
            data: Data na ulozenie
        """
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info("Data uspesne ulozene do suboru %s", self.output_file)
        except Exception as e:
            self.logger.error("Chyba pri ukladani dat do suboru %s: %s", self.output_file, e)
    
    def run(self) -> None:
        """Spustenie scrapera"""
        self.logger.info("Spustam scraper pre prospektmaschine.de")
        start_time = time.time()
        all_brochures = self.scrape_all_hypermarkets()
        self.logger.info("Celkovo najdenych %d letakov", len(all_brochures))
        self.save_to_json(all_brochures)
        end_time = time.time()
        self.logger.info("Scraper uspesne dokonceny, trvanie: %.2f sekund", end_time - start_time)


if __name__ == "__main__":
    scraper = ProspektMaschinenScraper()
    scraper.run()

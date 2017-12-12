#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Core module"""

# Standard libraries
import os
import signal
import time
import re
from subprocess import Popen, PIPE

# External libraries
from pyvirtualdisplay import Display
from selenium import webdriver
from cachetools import Cache
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm

# Internal modules
from milanuncios.utils import create_logger

class MilAnuncios:
    """Main Scraper class

    Args:
        time_loading (float, optional): Time to wait until the page is loaded
            before scrap it. As default, 1.0
        timeout (float, optional): Timeout for requests. As default 15
        executable_path (str, optional): Geckodriver executable path.
            As default, "geckodriver" (needs to be in sys.path)
        log_path (str, optional): Geckodriver log path. As default,
            "geckodriver.log"
    """
    def __init__(self, time_loading=1.3, timeout=15, init_cache=False,
    	            executable_path="geckodriver", log_path="geckodriver.log"):
        self.main_url = "https://www.milanuncios.com"

        self.timeout = timeout
        self.time_loading = time_loading

        self.logger = create_logger("milanuncios")
        self.cache = Cache(256)

        self.browser = webdriver.Firefox(executable_path=executable_path,
        	                                log_path=log_path)
        self._initialize_geckodriver()
        # Save user firefox processes
        self._user_firefox_procs = self._get_firefox_processes()

        if init_cache:
            self._initialize_cache()

    def _initialize_geckodriver(self):
        """Internal function to unitialize geckodriver"""
        self.browser.set_script_timeout(self.timeout)
        self.browser.set_page_load_timeout(self.timeout)

    def _initialize_cache(self):
        """Internal function to initialize cache"""
        self.logger.info("Caching categories tree, please wait...")
        for category in tqdm(self.categories):
            self.subcategories(category)

    @staticmethod
    def _get_firefox_processes():
        """Internal function to get already opened user firefox processes"""
        pipeline = Popen(["pgrep", "firefox"], stdout=PIPE, stderr=PIPE)
        stdout, stderr = pipeline.communicate()
        procs = stdout.decode("utf-8").split("\n")[:-1]
        return procs

    def _clean_firefox_processes(self):
        """Internal function to kill all new firefox processes
        opened by requests."""
        procs = self._get_firefox_processes()
        killone, informed = (False, False)
        for pid in procs:
            if pid not in self._user_firefox_procs:
                killone = True
                os.kill(int(pid), signal.SIGKILL)
            if killone and not informed:
                msg = "Killing Firefox processes for avoid to overload memory... "
                self.logger.info(msg)
                informed = True

    def kill_all_firefox(self):
        """Function to kill all firefox processes. Util for development
        or if you experiments errors in requests."""
        for pid in self._get_firefox_processes():
            os.kill(int(pid), signal.SIGKILL)

    def clean(self):
        """Syntax sugar to kill firefox processes opened by requests"""
        self._clean_firefox_processes()

    def _get_regions(self):
        """Search in milanuncios.com all the regions
        (use regions property for a faster response)"""
        def parser(soup):
            """Regions parser"""
            response = []
            for prov in soup.find(id="protmp").find_all("option"):
                prov = prov["value"]
                if prov != "":
                    response.append(prov)
            return response
        url = "https://www.milanuncios.com/ofertas-de-empleo/"
        response = self.__call__(url, parser)
        self.clean()
        return response

    @property
    def regions(self):
        """Returns all posible regions hardcoded for filter responses"""
        return [
            'alava', 'albacete', 'alicante', 'almeria', 'andalucia', 'aragon',
            'asturias', 'avila', 'badajoz', 'baleares', 'barcelona', 'burgos',
            'caceres', 'cadiz', 'cantabria', 'canarias', 'castellon',
            'castilla_la_mancha', 'castilla_y_leon', 'catalunya', 'ceuta',
            'ciudad_real', 'cordoba', 'cuenca', 'extremadura', 'galicia',
            'girona', 'granada', 'guadalajara', 'guipuzcoa', 'huelva',
            'huesca', 'jaen', 'la_coruna', 'la_rioja', 'las_palmas', 'leon',
            'lleida', 'lugo', 'madrid', 'malaga', 'melilla', 'murcia', 'navarra',
            'ourense', 'pais_vasco', 'palencia', 'pontevedra', 'salamanca',
            'segovia', 'sevilla', 'soria', 'tarragona', 'tenerife', 'teruel',
            'toledo', 'valencia', 'comunidad_valenciana', 'valladolid', 'vizcaya',
            'zamora', 'zaragoza'
        ]

    @staticmethod
    def _offer_demand_parser(offer, demand):
        """Internal function filter for offer/demand parameters"""
        demand_param = None
        if not (offer and demand) and not (not offer and not demand):
            if offer:
                demand_param = "n"
            else:
                demand_param = "s"
        return demand_param

    def __call__(self, url, parser_fn, clean=False):
        """Main internal function to call all the requests of the scraper

        Args:
            url (str): Endpoint to use in the method
            parser_fn (function): Parser callback to obtain neccesary
                data from the page. The callback return a string
                with the whole page html.
            clean (bool, optional): Kill process opened by request
                As default, False.

        Returns (function):
             parser_fn(soup)
        """
        # pyvirtualdisplay magic happens here
        display = Display(visible=0, size=(1024, 768))
        display.start()
        self.browser.get(url)
        time.sleep(self.time_loading)
        soup = BeautifulSoup(self.browser.page_source, "html.parser")
        response = parser_fn(soup)
        if clean:
            self.clean()
        return response

    @property
    def categories(self):
        """Obtains all main categories from home page

        Returns: list"""
        def parser(soup):
            """Categories parser"""
            response = {}
            categorias = soup.find_all(class_="catIcono")
            for categoria in categorias:
                categoria = categoria.find("a")
                response[categoria["title"].lower()] = self.main_url + categoria["href"]
            try:
                self.cache["categories"]
            except KeyError:
                self.cache["categories"] = response
            finally:
                return list(response.keys())

        try:
            return self.cache["categories"]
        except KeyError:
            return self.__call__(self.main_url, parser, clean=True)

    def subcategories(self, category):
        """Obtain all subcategories (and sub-subcategories recursively)
        from a given main category

        Args:
            category (str): Category for obtain all nested subcategories

        Returns: list
        """
        def parser(soup):
            """Subcategories parser"""
            response = {}
            classes = ["smoMainCat", "smoL2Cat", "smoL3Cat", "smoL4Cat", "smoL5Cat"]
            for cls in classes:
                subcategories = soup.find_all(class_=cls)
                for subcategory in subcategories:
                    name = subcategory.string.lower()
                    if name[-1] == " ":
                        name = name[:-1]
                    href = subcategory.find("a")["href"]
                    response[name] = href
                    try:
                        self.cache["subcategories"][name] = self.main_url + href
                    except KeyError:
                        self.cache["subcategories"] = {}
                        self.cache["subcategories"][name] = self.main_url + href
            return list(response.keys())

        try:
            self.cache["categories"]
        except KeyError:
            self.categories

        try:
            url = self.cache["categories"][category]
        except KeyError:
            raise ValueError("Category %s not found in milanuncios.com" % (category))
        else:
            return self.__call__(url, parser, clean=True)

    def _ads_parser(self, soup):
        """Internal parser function for get all ads in every page"""
        response = []
        for anuncio in soup.find_all(class_="aditem-detail"):
            _title = anuncio.find(class_="aditem-detail-title")
            title = _title.string
            href = self.main_url + _title["href"]
            desc = re.sub(r"<.*?>", "", repr(anuncio.find(class_="tx")))
            try:
                price = anuncio.find(class_="aditem-price").next_element
            except AttributeError:
                price = None
            response.append({"title": title, "desc": desc,
                             "price": price, "href": href})
        return response

    def search(self, query, pages=1, region=None, offer=True, demand=True):
        """Search by query

        Args:
            query (str): String to search in milanuncios
            pages: (int): Number of pages retieved in the search

        Returns:
            pandas.DataFrame
        """
        query = query.replace(" ", "-")
        response = []
        endpoint = "/anuncios"

        # Region filter
        if region:
            region = region.replace(" ", "_").lower()
            if region in self.regions:
                endpoint += "-en-%s/" % region
            else:
                raise ValueError("Region %s is not a valid region, see self.regions" % region)

        demand_param = self._offer_demand_parser(offer, demand)

        for page in tqdm(range(1, pages + 1)):
            url = self.main_url + "%s" % endpoint
            if query != "":
                url += "%s.htm" % query
            url += "?pagina=%d&" % page
            if demand_param:
                url += "demanda=%s&" % demand_param
            new_ads = self.__call__(url, self._ads_parser)
            response += new_ads
            if not new_ads:
                self.logger.info("Only %d pages found", (page - 1))
                break

        self.clean()
        if response:
            return pd.DataFrame(response, columns=response[0].keys())
        else:
            return []

    def search_category(self, category, subcategory=None, pages=1,
                        region=None, offer=True, demand=True):
        """Search by category (and optional subcategory)

        Args:
            category (str): Category to search.
            subcategory (str, optional): You can select an optional
                subcategory for a more precise search. As default None.
            pages (int, optional): Maximun number of pages to retrieve.
                As default 1.

        Returns:
            pandas.DataFrame
        """
        if subcategory:
            try:
                endpoint = self.cache["subcategories"][subcategory.lower()]
            except KeyError:  # If fails, get subcategories from parent
                self.subcategories(category)
                endpoint = self.cache["subcategories"][subcategory.lower()]
        else:
            try:
                endpoint = self.cache["categories"][category.lower()]
            except KeyError:  # If fails, reload categories
                self.categories
                endpoint = self.cache["categories"][category.lower()]

        if region:
            region = region.replace(" ", "_").lower()
            if region in self.regions:
                endpoint = endpoint[:-1] + "-en-%s" % region

        demand_param = self._offer_demand_parser(offer, demand)

        response = []
        for page in tqdm(range(1, pages + 1)):
            _url = endpoint + "/?pagina=%d&" % page
            if demand_param:
                _url += "demanda=%s&" % demand_param
            new_ads = self.__call__(_url, self._ads_parser)
            response += new_ads
            if not new_ads:
                self.logger.info("Only %d pages found", (page - 1))
                break

        self.clean()
        if response:
            return pd.DataFrame(response, columns=response[0].keys())
        else:
            return []

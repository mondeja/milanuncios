#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Core module"""

# Standard libraries
import os
import signal
import time
import re
import random
import logging
import datetime
from uuid import uuid4
from subprocess import Popen, PIPE

# External libraries
from pyvirtualdisplay import Display
from cachetools import Cache
from pandas import DataFrame
from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

# Internal modules
from milanuncios.utils import (create_logger,
                               parse_string_to_timedelta)

class MilAnunciosLoginError(RuntimeError):
    """Exception raised if login fails"""
    pass

class MilAnuncios:
    """Main Scraper class

    Args:
        delay (float, optional): Time to wait until the page is loaded
            before scrap it (in seconds). As default, 1.5
        timeout (float, optional): Timeout for requests. As default 15
        executable_path (str, optional): Geckodriver executable path.
            As default, "geckodriver" (needs to be in sys.path)
        log_path (str, optional): Geckodriver log path. As default,
            "geckodriver.log"
    """
    def __init__(self, delay=1.5, timeout=15, init_cache=False,
                 executable_path="geckodriver", log_path="geckodriver.log",
                 cache=Cache(24), logger=create_logger("milanuncios"),
                 debug=False):
        self.main_url = "https://www.milanuncios.com"

        self.timeout = timeout
        self.delay = delay
        self.debug = debug
        self.init_cache = init_cache

        self.logger = logger
        self.cache = cache

        self._executable_path = executable_path
        self._log_path = log_path

        # Attributes defined on __enter__
        self.session = None
        self.firefox_user_processes = None
        self.browser = None
        self.browser_pid = None

        # Account methods
        self.logged = False
        self._logged_soup = None

    def __enter__(self):
        self._start_session()
        if self.init_cache:
            self._initialize_cache()
        return self

    def __exit__(self, *excs):
        if excs:   # We are calling like...? ->  MilAnuncios().__exit__()
            if None not in excs:
                self.logger.error(excs[2], exc_info=True)
        if not self.debug:
            self._end_session()
        return False

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
            if pid not in self.firefox_user_processes:
                killone = True
                os.kill(int(pid), signal.SIGKILL)
            if killone and not informed:
                msg = "Killing Firefox processes for avoid to overload memory... "
                self.logger.debug(msg)
                informed = True
        return True

    def _start_session(self):
        """Internal function to start a virtual session"""
        self.session = uuid4()

        # Obtain user processes
        self.firefox_user_processes = self._get_firefox_processes()

        # pyvirtualdisplay magic happens here
        display = Display(visible=0, size=(1024, 768))
        if not self.debug:
            display.start()
        else:
            self.logger.setLevel(logging.DEBUG)

        # selenium browser
        self.browser = webdriver.Firefox(executable_path=self._executable_path,
                                         log_path=self._log_path)
        self.browser.set_script_timeout(self.timeout)
        self.browser.set_page_load_timeout(self.timeout)

        # Save new process
        for pid in self._get_firefox_processes():
            if pid not in self.firefox_user_processes:
                self.browser_pid = int(pid)

    def _end_session(self):
        """End scraper session"""
        self.logged = False
        os.kill(self.browser_pid, signal.SIGKILL)

    def kill_firefox(self):
        """Function to kill all firefox processes. Util for development
        or if you experiments errors in requests."""
        for pid in self._get_firefox_processes():
            os.kill(int(pid), signal.SIGKILL)
        self._start_session()  # We need to restart session

    def clean(self):
        """Close browser and kill firefox processes opened by requests"""
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
        response = self.__call__(url, parser, clean=True)
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

    @property
    def current_soup(self):
        """Function to get current page source code displaying on browser"""
        return BeautifulSoup(self.browser.page_source, "html.parser")

    def __call__(self, url, callback, clean=False):
        """Main internal function to call all the requests of the scraper

        Args:
            url (str): Endpoint to use in the method
            callback (function): Callback that returns a string
                with the whole page html.
            clean (bool, optional): Kill process opened by request
                As default, False.

        Returns (function):
             callback(soup)
        """
        self.browser.get(url)
        time.sleep(self.delay)
        response = callback(self.current_soup)
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
            response = self.cache["categories"]
        except KeyError:
            response = self.__call__(self.main_url, parser, clean=True)
            return response

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
            raise ValueError("Category %s not found in milanuncios.com" % category)
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
        endpoint = "/anuncios/"

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

        if response:
            return DataFrame(response, columns=response[0].keys())
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

        if response:
            return DataFrame(response, columns=response[0].keys())
        else:
            return []

    def login(self, email, password, remember=False):
        """Internal function to login in milanuncios securely"""
        self.logger.info("Login in milanuncios.com... Email: %s", email)

        def _login():
            # Input fields
            email_input = self.browser.find_element_by_id("email")
            password_input = self.browser.find_element_by_id("contra")
            remember_input = self.browser.find_element_by_id("rememberme")
            # Perform actions
            email_input.send_keys(email)
            time.sleep(random.uniform(1., 1.8))
            password_input.send_keys(password)
            time.sleep(random.uniform(1.5, 1.8))
            selected = remember_input.is_selected()
            if selected != remember:
                remember_input.click()
            # Submit button
            submit = self.browser.find_element_by_class_name("submit")
            submit.click()
            return True

        def check_login():
            """Check if login passed"""
            soup = self.current_soup
            return (soup.find(class_="cat1") != None, soup)

        # Go to my ads page
        self.browser.get(self.main_url + "/mis-anuncios/")
        time.sleep(self.delay)

        # Check if we are logged
        self.logger.debug("Checking login...")
        logged, soup = check_login()
        self.logger.debug("Logged? -> %r", logged)

        # If we aren't logged, try to login 3 times
        login_attempts = 4
        login_passed = False
        while not logged and login_attempts > 0:
            time.sleep(self.delay)
            try:
                login_passed = _login()
            except NoSuchElementException:  # Hey! We are logging in
                login_passed = True
            if login_passed:
                logged, soup = check_login()
                self.logger.debug("Logged? -> %r", logged)
            else:  # This is not secure yet?
                msg = "Login error, if persists send a mail to mondejar1994@gmail.com"
                self.logger.warning(msg)
            if logged:
                break
            login_attempts -= 1

        if login_attempts == 0:  # If all attempts fails
            msg = "Login not posible after %d attemps. Please, check your credentials."
            self.logger.error(msg)
            raise MilAnunciosLoginError(msg)

        self.logger.info("Login successfully.")
        self.logged = True
        self._logged_soup = soup
        return True

    def my_ads(self, *args, dataframe=True, _container=False, **kwargs):
        """Get your adverts

        Args:
            email (str): Email of your milanuncios account
            password (str): Password of your milanuncios account
            remember (bool, optional): Do you want to be remembered
                in login? False as default
            dataframe (bool, optional): If True, returns a pandas.DataFrame,
                otherwise returns a list of dictionaries. As default True

        Returns: pandas.DataFrame / list
        """
        if not self.logged:
            self.login(args[0], args[1], **kwargs)
        soup = self._logged_soup

        def get_ad_info(container):
            """Get advert info"""
            response = {"renovable": False}

            content = container.find(class_="aditem-detail")

            # Get title
            title_link = content.find(class_="aditem-detail-title")
            response["title"] = title_link.string

            # Get description and time to expire
            desc_expire = re.sub(r"<.*?>", "",
                                 repr(content.find(class_="tx")))
            desc, expire_string = desc_expire.split("Caduca en ")
            response["desc"] = desc

            response["href"] = self.main_url + title_link["href"]

            # Get ad's expire time
            expire = parse_string_to_timedelta(expire_string)
            response["expire"] = expire

            # Last renew
            last_renew_string = container.find(class_="x6").string
            last_renew = parse_string_to_timedelta(last_renew_string)
            response["last_renew"] = last_renew

            # Has photos?
            view_photos_div = content.find(class_="vef")
            if view_photos_div:
                response["has_photos"] = True
            else:
                response["has_photos"] = False

            # If we are renewing ads we need the container
            if _container:
                response["container"] = container

            return response

        ads = []
        for container in soup.find_all(class_="aditem"):
            # Get ad info
            ads.append(get_ad_info(container))

        if ads:
            if dataframe:
                return DataFrame(ads, columns=ads[0].keys())
            return ads
        return []


    def renew_ads(self, *args, ads=None, number=None, **kwargs):
        """Renew ads

        Args:
            email (str): Email of your milanuncios account
            password (str): Password of your milanuncios account
            remember (bool, optional): Do you want to be remembered
                in login? False as default
            ads (list, optional): List with all ads title that you want to renew.
                If None, automatically will be renewed all of these
                wich can be renovated.
            number (int, optional): Number of ads maximun to renovate.
                If you specifies ad titles in ads param, this param
                will be ignored. As default None.

        Returns (int):
            Number of ads that were renewed
        """
        # Get all ads of my account
        if not self.logged:
            all_ads = self.my_ads(args[0], args[1], dataframe=False,
                                  _container=True, **kwargs)
        else:
            all_ads = self.my_ads(dataframe=False, _container=True, **kwargs)

        def renew(container):
            """Internal function to renew an ad"""
            footer = container.find(class_="aditem-footer").find("div")
            # Get renew button
            renew_button_href = footer.find(class_="icon-renew").parent["href"]
            renew_button = self.browser.find_element_by_xpath(
                '//a[@href="%s"]' % renew_button_href)
            renew_button.click()  # Click renew button
            time.sleep(self.delay)

            # Change to internal renew iframe
            iframe = self.browser.find_element_by_id("ifrw")
            self.browser.switch_to.frame(iframe)
            # Get confirm renew button
            confirm_renew_button = self.browser.find_element_by_id("lren")
            confirm_renew_button.click()
            time.sleep(random.uniform(.5, .8))
            return True

        minimun_time_between_renews = datetime.timedelta(hours=24)

        counter = 0
        for advert in all_ads:
            renovated = False
            # Is renovable?
            if advert["last_renew"] > minimun_time_between_renews:
                if ads:
                    if advert["title"] in ads or advert["title"].upper() in ads:
                        renovated = renew(advert["container"])
                else:
                    renovated = renew(advert["container"])
            if renovated:
                counter += 1
                if not ads:
                    if number:
                        if number <= counter:
                            break

        return counter

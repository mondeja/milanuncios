#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Core module"""

# Standard libraries
import os
import signal
import psutil
import time
import re
import random
import logging
import datetime
import platform
from uuid import uuid4
from subprocess import Popen, PIPE

# External libraries
from pyvirtualdisplay import Display
from cachetools import Cache
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
    """Main Scraper class, used as context

    Args:
        delay (float, optional): Time to wait until the page is loaded
            before scrap it (in seconds). As default, 1.5
        timeout (float, optional): Timeout for requests. As default 15
        executable_path (str, optional): Geckodriver executable path.
            As default, "geckodriver" (needs to be in sys.path)
        log_path (str, optional): Geckodriver log path. As default,
            "geckodriver.log"
        firefox_binary (str, optional): Firefox binary path (used if you
            are running on RaspberryPi). As default "/usr/bin/firefox"
        display (bool, optional): Display web browser navigation
            on real time, useful for debug (doesn't work on RaspberryPi).
            As default False
    """
    def __init__(self, delay=1.5, timeout=15, init_cache=False,
                 executable_path="geckodriver", log_path="geckodriver.log",
                 cache=Cache(24), logger=create_logger("milanuncios"),
                 debug=False, firefox_binary="/usr/bin/firefox",
                 display=False):
        self.main_url = "https://www.milanuncios.com"

        self.timeout = timeout
        self.delay = delay
        self.debug = debug
        self.init_cache = init_cache

        self.logger = logger
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        self.cache = cache

        self._executable_path = executable_path
        self._log_path = log_path
        self._firefox_binary = firefox_binary

        # Attributes defined on __enter__
        self.session = None
        self.firefox_user_processes = None
        self.browser = None
        self.browser_pid = None

        self.display = display

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
        response = []
        for proc in psutil.process_iter():
            if "firefox" in proc.name():
                response.append(int(proc._pid))
        return response

    def _start_in_raspberry(self):
        """Internal function to start session if we are running
        on RaspberryPi. You need to install iceweasel and download
        geckodriver version 0.16.0"""
        msg = "Initializing driver for RaspberryPi. Firefox binary path: %s"
        self.logger.debug(msg, self._firefox_binary)
        caps = webdriver.DesiredCapabilities().FIREFOX
        caps["marionette"] = False
        binary = webdriver.firefox.firefox_binary.FirefoxBinary(self._firefox_binary)
        return webdriver.Firefox(firefox_binary=binary)

    def _start_session(self):
        """Internal function to start a virtual session"""
        self.session = uuid4()
        self.logger.debug("Starting session %s...", self.session)

        # Obtain user processes
        self.firefox_user_processes = self._get_firefox_processes()

        # pyvirtualdisplay magic happens here
        visible = 1 if self.display == True and platform.node() != "raspberrypi" else 0
        display = Display(visible=visible, size=(1024, 768))
        display.start()

        # selenium browser
        if platform.node() == "raspberrypi":
            self.browser = self._start_in_raspberry()
        else:
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

    def __call__(self, url, callback):
        """Main internal function to call all the requests of the scraper

        Args:
            url (str): Endpoint to use in the method
            callback (function): Callback that returns a string
                with the whole page html.

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
        self.logger.debug("Obtaining main categories...")
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
            response = self.__call__(self.main_url, parser)
            return response

    def subcategories(self, category):
        """Obtain all subcategories (and sub-subcategories recursively)
        from a given main category

        Args:
            category (str): Category for obtain all nested subcategories

        Returns: list
        """
        self.logger.debug("Obtaining subcategories for %s category", category)
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
            return self.__call__(url, parser)

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
        from pandas import DataFrame
        self.logger.info("Searching all adverts that contain %s", query)

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
                self.logger.info("%d pages found", (page - 1))
                break

        if response:
            return DataFrame(response, columns=response[0].keys())
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
        from pandas import DataFrame
        self.logger.info("Searching by category: %s", category)

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
                self.logger.info("%d pages found", (page - 1))
                break

        if response:
            return DataFrame(response, columns=response[0].keys())
        return []

    def login(self, email, password, remember=False, attempts=5):
        """Login in milanuncios to perform actions on your account


        """
        self.logger.info("Trying to login in milanuncios.com... Email: %s", email)

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

        # If we aren't logged, try to login X times (attempts param)
        login_passed = False
        while not logged and attempts > 0:
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
            attempts -= 1

        if attempts == 0:  # If all attempts fails
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
        if dataframe:
            from pandas import DataFrame
        if not self.logged:
            self.login(args[0], args[1], **kwargs)
        soup = self._logged_soup

        self.logger.info("Retrieving your ads")

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

        self.logger.debug("%d ads published in your account", len(ads))

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

        if not all_ads:
            self.logger.warning("0 ads found. Maybe yo don't have ads pusblished?")
            return

        if ads:
            self.logger.debug("Renewing %d ads: %s" % (len(ads), str(ads)))
        else:
            self.logger.debug("Renewing all ads (%d)", len(all_ads))

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
            confirm_renew_button.click()  # Click renew
            time.sleep(1)  # Go to my ads page again
            return True

        def count_new_ad(stats):
            stats["ads_found"]["n"] += 1
            stats["ads_found"]["ads"].append(advert["title"])
            return True

        minimun_time_between_renews = datetime.timedelta(hours=24)

        stats = {
            "n_renews": 0,
            "ads_to_renew": {
                "n": len(all_ads) if not ads else len(ads),
                "ads": all_ads if not ads else ads,
            },
            "ads_found": {  # Check if there are title errors in ads param
                "n": 0,
                "ads": []
            }
        }

        for advert in all_ads:
            to_renew, renovated = (False, False)
            if ads:
                if advert["title"] in ads or advert["title"].upper() in ads:
                    to_renew = count_new_ad(stats)
                    stats["ads_found"]["n"] += 1
                    stats["ads_found"]["ads"].append(advert["title"])
            else:
                to_renew = count_new_ad(stats)

            if to_renew and advert["last_renew"] > minimun_time_between_renews:
                renovated = renew(advert["container"])
            if renovated:
                stats["n_renews"] += 1

        self.logger.info("%d adverts renovated",  stats["n_renews"])

        if ads:
            # Check if all titles on ads list param were found
            if stats["ads_found"]["n"] < stats["ads_to_renew"]["n"]:
                self.logger.warning("%d ads not found:",
                    stats["ads_to_renew"]["n"] - stats["ads_found"]["n"])
                for ad in ads:
                    if ad not in stats["ads_found"]["ads"]:
                        self.logger.warning(ad)

        # Check number of ads not renewed (only for debug)
        if stats["n_renews"] < stats["ads_to_renew"]["n"]:
            self.logger.debug("%d adverts were not renovated",
                               stats["ads_to_renew"]["n"] - stats["n_renews"])

        return stats["n_renews"]

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test milanuncios web scraper and adverts renewer"""

# To disable warnings: python3 -W ignore test.py

# Standard libraries
import unittest

# External libraries
from pandas import DataFrame

# Internal modules
from milanuncios import MilAnuncios

# If you want to test renewer you need to config email and password
config = {
    "email": None,
    "password": None,
    "ad_titles": None,  # Used to renew ads by title name (list)
    "ads_number": 1, # Used to renew ads by number of them (int)

    "debug": False,
    "delay": 3,
    "timeout": 15,
    # Selenium drivers
    "executable_path": "geckodriver",
    "log_path": "geckodriver.log",

    # Test end to end
    "full": False
}

params = ["debug", "delay", "timeout",
              "executable_path", "log_path"]
options = {param: config[param] for param in params}

class TestWebScraper(unittest.TestCase):
    """MilAnuncios web scraper tests"""

    def setUp(self):
        self.ma = MilAnuncios(**options)
        self.ma.__enter__()

    def tearDown(self):
        self.ma.__exit__()
        if self.ma.debug:
            self.ma.logger.debug("Firefox processes opened: %r",
                                 self.ma.firefox_user_processes)

    # ===   INFO TESTS   ===
    def test_regions(self):
        collect_regions = self.ma._get_regions()
        hardcoded_regions = self.ma.regions
        self.assertEqual(collect_regions, hardcoded_regions)

    def test_categories(self):
        categories = self.ma.categories
        self.assertIs(type(categories), list)
        self.assertGreater(len(categories), 10)

    def test_subcategories(self):
        subcategories = self.ma.subcategories("motor")
        self.assertIs(type(subcategories), list)
        self.assertGreater(len(subcategories), 5)

    # ===   SEARCH TESTS   ===
    def test_search(self):
        # Query basic search
        response = self.ma.search("sofa")
        self.assertIn(type(response), (DataFrame, list))

    def test_search_category(self):
        # Query basic search by category
        response = self.ma.search_category("motor")
        self.assertIs(type(response), DataFrame)
        self.assertEqual(response.empty, False)


@unittest.skipIf(not config["full"],
    'Cache testing only posible if config["full"] == True')
class TestWebScraperCache(unittest.TestCase):
    """MilAnuncios cache tests"""
    def setUp(self):
        options["init_cache"] = True
        self.ma = MilAnuncios(**options)
        del options["init_cache"]
        self.ma.__enter__()

    def tearDown(self):
        self.ma.__exit__()

    def assert_cached(self, dictionary):
        self.assertIs(type(dictionary), dict)
        self.assertGreater(dictionary, 10)

    def test_categories_cache(self):
        self.assert_cached(self.ma.cache["categories"])

    def test_subcategories_cache(self):
        self.assert_cached(self.ma.cache["subcategories"])


@unittest.skipIf(not config["email"] or not config["password"],
    "For account methods testing you must provide email and password in config")
class TestAccount(unittest.TestCase):
    """MilAnuncios account tests"""
    def setUp(self):
        self.ma = MilAnuncios(**options)
        self.ma.__enter__()

    def tearDown(self):
        self.ma.__exit__()

    def test_login(self):
        self.ma.login(config["email"],
                      config["password"])
        self.assertEqual(self.ma.logged, True)

    def test_my_ads(self):
        # Test my ads with login
        ads = self.ma.my_ads(config["email"],
                             config["password"])
        self.assertIs(type(ads), DataFrame)

    def test_login_my_ads(self):
        # First login, then get my_ads
        if self.ma.login(config["email"],
                         config["password"]):
            ads = self.ma.my_ads()
            self.assertIs(type(ads), DataFrame)

    def test_renew_ads(self):
        # If we are renewing by name
        if config["ad_titles"]:
            if self.ma.login(config["email"],
                             config["password"]):
                renewed = self.ma.renew_ads(ads=config["ad_titles"])
        else:
            if config["ads_number"]:
                # If we are renewing by number
                if self.ma.login(config["email"],
                                 config["password"]):
                    renewed = self.ma.renew_ads(number=config["ads_number"])
            else:
                if self.ma.login(config["email"],
                                 config["password"]):
                    renewed = self.ma.renew_ads()
        self.assertGreater(renewed, 0)

if __name__ == "__main__":
    unittest.main()
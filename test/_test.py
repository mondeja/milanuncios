from milanuncios import MilAnuncios
from selenium import webdriver

caps = webdriver.DesiredCapabilities().FIREFOX
caps["marionette"] = False
binary = webdriver.firefox.firefox_binary.FirefoxBinary("/usr/bin/firefox")

ma = MilAnuncios(driver=webdriver.Firefox(firefox_binary=binary))
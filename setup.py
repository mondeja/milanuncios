#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from distutils.core import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name = 'milanuncios',
    version = '0.9.11',
    url = 'https://github.com/mondeja/milanuncios',
    download_url = 'https://github.com/mondeja/milanuncios/archive/master.zip',
    author = 'Alvaro Mondejar <mondejar1994@gmail.com>',
    author_email = 'mondejar1994@gmail.com',
    license = 'BSD License',
    packages = ['milanuncios'],
    description = 'Python3 web scraper for milanuncios.com.',
    long_description = open('README.md','r').read(),
    keywords = ['milanuncios', 'anuncios', 'segunda mano', 'scraper', 'dinamic scraping', 'python', 'big data'],
    install_requires = requirements
)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from distutils.core import setup

BASEDIR = os.path.dirname(__file__)

with open(os.path.join(BASEDIR, 'requirements.txt')) as f:
    requirements = f.readlines()

with open(os.path.join(BASEDIR, 'README.md')) as f:
    readme = f.read()

setup(
    name = 'milanuncios',
    version = '0.9.13',
    url = 'https://github.com/mondeja/milanuncios',
    download_url = 'https://github.com/mondeja/milanuncios/archive/master.zip',
    author = 'Alvaro Mondejar <mondejar1994@gmail.com>',
    author_email = 'mondejar1994@gmail.com',
    license = 'BSD License',
    packages = ['milanuncios'],
    description = 'Python3 web scraper for milanuncios.com.',
    long_description = readme,
    keywords = ['milanuncios', 'anuncios', 'segunda mano', 'scraper', 'dinamic scraping', 'python', 'big data'],
    install_requires = requirements
)

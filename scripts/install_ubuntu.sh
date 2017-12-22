#!/bin/bash

wget https://github.com/mozilla/geckodriver/releases/download/v0.19.1/geckodriver-v0.19.1-linux64.tar.gz
tar -xvzf geckodriver-v0.19.1-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/geckodriver
git clone https://github.com/mondeja/milanuncios.git
cd milanuncios
python3 setup.py install

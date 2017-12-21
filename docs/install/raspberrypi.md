## Install on RaspberryPi
```
wget https://github.com/mozilla/geckodriver/releases/download/v0.16.0/geckodriver-v0.16.0-arm7hf.tar.gz
tar -xvzf geckodriver-v0.16.0-arm7hf.tar.gz
sudo mv geckodriver /usr/local/bin/geckodriver
sudo apt-get install iceweasel xvfb
pip3 install bs4 cachetools pyvirtualdisplay selenium==3.3.2 tqdm psutil
git clone https://github.com/mondeja/milanuncios.git
cd milanuncios
python3 setup.py install
```

If you want to recopile info, you need to install `pandas` also, but for autorenovate ads it's unnecesary.

### Usage tip
RaspberryPi has little RAM memory, so you need to set a big delay between commands (10 seconds must be enough):
```
from milanuncios import MilAnuncios
with MilAnuncios(delay=10) as ma:
   ...
```
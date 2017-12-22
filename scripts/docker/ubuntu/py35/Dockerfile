FROM ubuntu:latest

RUN apt-get update
RUN apt-get install -y python3-pip python3-dev
RUN pip3 install --upgrade pip
RUN apt install wget git -y
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.19.1/geckodriver-v0.19.1-linux64.tar.gz
RUN tar -xvzf geckodriver-v0.19.1-linux64.tar.gz
RUN mv geckodriver /usr/local/bin/geckodriver
RUN pip3 install https://github.com/mondeja/milanuncios/archive/staging.zip

ENTRYPOINT ["/bin/bash"]
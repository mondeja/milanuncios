FROM ubuntu:latest

RUN apt-get clean && apt-get update && apt-get install -y locales
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN apt-get update
RUN apt-get install -y python3-pip python3-dev
RUN pip3 install --upgrade pip
RUN apt-get install wget git xvfb -y
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.19.1/geckodriver-v0.19.1-linux64.tar.gz
RUN tar -xvzf geckodriver-v0.19.1-linux64.tar.gz
RUN mv geckodriver /usr/local/bin/geckodriver
RUN git clone -b staging https://github.com/mondeja/milanuncios.git && cd milanuncios
RUN echo "Directorio actual:"
RUN echo $PWD
RUN pip3 install -r /milanuncios/requirements.txt
RUN python3 /milanuncios/setup.py install
RUN python3 /milanuncios/test/test.py


ENTRYPOINT ["/bin/bash"]
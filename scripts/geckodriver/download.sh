#!/bin/bash

# Script to get neccesary version of geckodriver
# across multiples OS. Need wget installed yet

travis=1
if [ -z $1 ]  # travis is not first command?
then
  travis=0
fi


# =======   URLs by OS and architecture   =======
Linux86_64=https://github.com/mozilla/geckodriver/releases/download/v0.19.1/geckodriver-v0.19.1-linux64.tar.gz
# ===============================================

# Get OS
case "$OSTYPE" in
  linux*)   OS="linux" ;;
  darwin*)  OS="mac" ;;
  msys*)    OS="windows" ;;
  solaris*) OS="solaris" ;;
  bsd*)     OS="bsd" ;;
  *)        OS="unknown" ;;
esac



# Linux environments
if [ $OS == "linux" ]
then

  # Install wget?
  if [ $travis -eq 0 ]  # If we are not in travis, try it
  then
    sudo apt-get install wget
  fi

  # 64bit architecture?
  if [ `uname -m` == "x86_64" ]
  then
    wget -N $Linux86_64 P ~/  # Download driver and store at home
    tar -xvf ~/geckodriver-v0.19.1-linux64.tar.gz
    rm ~/geckodriver-v0.19.1-linux64.tar.gz
    ls ~/
  fi

fi

# If we are in TravisCI, geckodriver needs to be in path
if [ $travis -eq 1 ]
then
  sudo mv -f ~/geckodriver /usr/local/share/geckodriver
  sudo chmod +x /usr/local/share/geckodriver
  sudo ln -s /usr/local/share/geckodriver /usr/local/bin/geckodriver
fi

echo "Where is geckodriver?"
whereis geckodriver


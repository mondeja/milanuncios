#!/bin/bash

# Script to get neccesary version of geckodriver
# across multiples OS. Need wget installed yet

# URLs by OS and architecture
Linux86_64=https://github.com/mozilla/geckodriver/releases/download/v0.19.1/geckodriver-v0.19.1-linux64.tar.gz


case "$OSTYPE" in
  linux*)   OS="linux" ;;
  darwin*)  OS="mac" ;;
  msys*)    OS="windows" ;;
  solaris*) OS="solaris" ;;
  bsd*)     OS="bsd" ;;
  *)        OS="unknown" ;;
esac


echo $OS

# Linux environments
if [ $OS == "linux" ]
then
  # Install wget
  sudo apt-get install wget
  # 64bit architecture
  if [ `uname -m` == "x86_64" ]
  then
    wget $Linux86_64
  fi
fi

ls




#if [[ $("uname -m") == "x86_64" ]]; then wget $linux64

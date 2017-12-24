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
    wget $Linux86_64
    tar -xvf geckodriver-v0.19.1-linux64.tar.gz
  fi

fi


ls


#if [[ $("uname -m") == "x86_64" ]]; then wget $linux64

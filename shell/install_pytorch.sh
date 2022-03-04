#!/bin/bash

# install the dependencies (if not already onboard)
sudo apt-get install python3-pip libopenblas-dev libopenmpi-dev libomp-dev
sudo -H pip3 install future
# upgrade setuptools 47.1.1 -> 57.1.0
sudo -H pip3 install --upgrade setuptools
sudo -H pip3 install Cython
# install gdown to download from Google drive
sudo -H pip3 install gdown
# copy binairy
sudo cp ~/.local/bin/gdown /usr/local/bin/gdown
# download the wheel
gdown https://drive.google.com/uc?id=1XL6k3wfWTJVKXHvCbZSfIVdz6IDJUAkt
# install PyTorch 1.8.1
sudo -H pip3 install torch-1.8.1a0+56b43f4-cp36-cp36m-linux_aarch64.whl
# clean up
rm torch-1.8.1a0+56b43f4-cp36-cp36m-linux_aarch64.whl
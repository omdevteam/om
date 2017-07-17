#!/usr/bin/env bash

export PATH=/home/p11user/CfelSoft/anaconda/bin:$PATH
export ONDA_INSTALLATION_DIR=/home/p11user/CfelSoft/onda

export PYTHONPATH=${ONDA_INSTALLATION_DIR}:${PYTHONPATH}
export PATH=${ONDA_INSTALLATION_DIR}:${ONDA_INSTALLATION_DIR}/GUI/:${ONDA_INSTALLATION_DIR}/tools/:${PATH}

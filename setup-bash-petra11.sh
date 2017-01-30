#!/usr/bin/env bash

export ONDA_CHEETAH_LIBRARY_DIR=/home/p11user/CfelSoft/cheetah/installation/lib/
export ONDA_CHEETAH_INCLUDE_DIR=/home/p11user/CfelSoft/cheetah/source/libcheetah/include
export ONDA_INSTALLATION_DIR=/home/p11user/CfelSoft/onda

export LD_LIBRARY_PATH=${ONDA_CHEETAH_LIBRARY_DIR}:${ONDA_INSTALLATION_DIR}/python_extensions/:${LD_LIBRARY_PATH}
export PYTHONPATH=${ONDA_INSTALLATION_DIR}:${PYTHONPATH}
export PATH=${ONDA_INSTALLATION_DIR}:${ONDA_INSTALLATION_DIR}/GUI/:${ONDA_INSTALLATION_DIR}/tools/:${PATH}

#!/usr/bin/env bash

export ONDA_INSTALLATION_DIR=/reg/g/cfel/onda/onda-20170716
source /reg/g/psdm/etc/psconda.sh

export PYTHONPATH=${ONDA_INSTALLATION_DIR}:${ONDA_HIDRA_API_DIR}:${PYTHONPATH}
export PATH=${ONDA_INSTALLATION_DIR}:${ONDA_INSTALLATION_DIR}/GUI/:${ONDA_INSTALLATION_DIR}/tools/:${PATH}

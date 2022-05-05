# In the last lines, replace X with the number of OM nodes
# to run on each machine and Y with a comma-separated list
# of hostnames for machines on which OM should be launched.
source /cds/sw/ds/ana/conda1/manage/bin/psconda.sh -py3
echo Creating and Running $(pwd)/monitor_wrapper.sh
echo '#!/bin/bash' > $(pwd)/monitor_wrapper.sh
echo '# File automatically created by the' >> $(pwd)/monitor_wrapper.sh
echo '# run_om.sh script, please do not' >> $(pwd)/monitor_wrapper.sh
echo '# edit directly.' >> $(pwd)/monitor_wrapper.sh
echo 'source /cds/sw/package/om/dev/setup.sh' >> $(pwd)/monitor_wrapper.sh
echo "om_monitor.py 'shmem=psana.0:stop=no'" >> $(pwd)/monitor_wrapper.sh
chmod +x $(pwd)/monitor_wrapper.sh
$(which mpirun) --mca oob_tcp_if_exclude enp193s0  --oversubscribe --map-by ppr:8:node \
     --host daq-mfx-mon02,daq-mfx-mon03,daq-mfx-mon04,daq-mfx-mon05 $(pwd)/monitor_wrapper.sh 

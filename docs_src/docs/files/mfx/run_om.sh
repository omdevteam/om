# In the last line, replace **X** with the number of OM nodes to run on each
# machine and **Y** with a comma-separated list of hostnames corresponding to the
# machines on which OnDA should run.
source /cds/sw/ds/ana/conda1/manage/bin/psconda.sh -py3
export PATH=$HOME/.local/bin:$PATH
echo Creating and Running $(pwd)/monitor_wrapper.sh
echo '#!/bin/bash' > $(pwd)/monitor_wrapper.sh
echo '# File automatically created by the'  >> $(pwd)/monitor_wrapper.sh
echo '# run_om.sh script, please do not edit directly' >> $(pwd)/monitor_wrapper.sh
echo 'source /cds/sw/ds/ana/conda1/manage/bin/psconda.sh -py3' >> $(pwd)/monitor_wrapper.sh
echo 'source <OM>' >> $(pwd)/monitor_wrapper.sh
echo "om_monitor.py 'shmem=psana.0:stop=no'" >> $(pwd)/monitor_wrapper.sh
 chmod +x $(pwd)/monitor_wrapper.sh
$(which mpirun) --oversubscribe --map-by ppr:4:node \
                --host daq-mfx-mon02,daq-mfx-mon03,daq-mfx-mon04,daq-mfx-mon05 $(pwd)/monitor_wrapper.sh

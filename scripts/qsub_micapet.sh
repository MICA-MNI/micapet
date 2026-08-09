#!/bin/bash
# qsub submitter for MICA-PET using the Singularity image on a single subject/session
# MICA-PET v.beta.0.1
# NB. remember to fill in the paths in run_micapet_singularity.sh before running this script
# usage: ./qsub_micapet.sh <subject_id>

subject=$1
RUN_SCRIPT=                           # to fill; path to the run script (eg. /path/to/run_micapet_singularity.sh)
QUEUE=                                # to fill; name of the queue to submit to (eg. mica.q)
RESOURCE_LIST=                        # to fill; resource list for qsub (eg. h_vmem=30G etc.)
JOB_NAME= "${subject}_micapet"        # modify as needed; job name for qsub
STD_OUT_LOG=                          # to fill; path to standard output log file (eg. /path/to/logs/${subject}_micapet_out.txt)
STD_ERR_LOG=                          # to fill; path to standard error log file (eg. /path/to/logs/${subject}_micapet_error.txt)

qsub -q ${QUEUE} \
-l ${RESOURCE_LIST} \
-N ${JOB_NAME} \
-o ${STD_OUT_LOG} \
-e ${STD_ERR_LOG} \
${RUN_SCRIPT} ${subject} 

sleep 45 # recommended so that the qsub command doesn't overwhelm the scheduler if submitting many jobs in a loop
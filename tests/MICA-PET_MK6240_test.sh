#!/bin/sh

# FDG test for MICA-PET pipeline
# This script is intended to be run inside the MICA-PET Singularity container.
# It performs a basic test of the MICA-PET pipeline using a small subset of data.

# Set variables for test subject, session, and tracer
MICA_PET_VERSION="v.alpha.0.5.1"
test_subject="PX002"
test_session="01"
BIDS_DIR="/host/verges/tank/data/jack/MK6240/BIDS_test_MK6240"
OUTPUT_DIR="/host/verges/tank/data/jack/MK6240/BIDS_test_MK6240/derivatives"
CORES=32
psf=2.4
ref_region="cerebellarGM"
pvc_method="IY"

# remove old outputs
rm -rf ${OUTPUT_DIR}/MICA-PET_${MICA_PET_VERSION}/sub-${test_subject}

# Run the MICA-PET pipeline on the test data

singularity run --cleanenv --env FS_LICENSE="/jack/license.txt" \
-B /host:/host -B ${BIDS_DIR}:/bids \
-B /host/verges/tank/data/jack:/jack \
/host/fladgate/local_raid/jack/FDG/MICA-PET/scripts/micapet_${MICA_PET_VERSION}.sif \
--fastsurfer_img /jack/fastsurfer-cpu-v2.4.2.sif \
--hippunfold_img /jack/hippunfold_v1.4.1.sif \
--fs_license /jack/license.txt \
--psf ${psf} \
--ref_region ${ref_region} \
--smoothing 5 10 \
--pvc-method ${pvc_method} \
/bids /bids/derivatives participant \
--cores ${CORES} \
--participant-label ${test_subject} 

#!/bin/sh

# FDG test for MICA-PET pipeline
# This script is intended to be run inside the MICA-PET Singularity container.
# It performs a basic test of the MICA-PET pipeline using a small subset of data.

# Set variables for test subject, session, and tracer
MICA_PET_VERSION="v.alpha.0.5"
test_subject="PX003"
test_session="pre"
BIDS_DIR="/host/verges/tank/data/jack/FDG/BIDS_Beijing_FCD_test"
OUTPUT_DIR="/host/verges/tank/data/jack/FDG/BIDS_Beijing_FCD_test/derivatives"
CORES=32
psf=3.3
ref_region="pons"
pvc_method="IY"

# remove old outputs
# rm -rf ${OUTPUT_DIR}/MICA-PET_${MICA_PET_VERSION}/sub-${test_subject}

# Run the MICA-PET pipeline on the test data

# singularity run --cleanenv --env FS_LICENSE="/jack/license.txt" \
# -B /host:/host -B ${BIDS_DIR}:/bids \
# -B /host/verges/tank/data/jack:/jack \
# /host/fladgate/local_raid/jack/FDG/MICA-PET/scripts/micapet_${MICA_PET_VERSION}.sif \
# --fastsurfer_img /jack/fastsurfer-cpu-v2.4.2.sif \
# --hippunfold_img /jack/hippunfold_v1.4.1.sif \
# --fs_license /jack/license.txt \
# --psf ${psf} \
# --ref_region ${ref_region} \
# --smoothing 5 10 \
# --pvc-method ${pvc_method} \
# /bids /bids/derivatives participant \
# --cores ${CORES} \
# --participant-label ${test_subject} 

conda run -n mica-pet python /host/fladgate/local_raid/jack/FDG/MICA-PET/scripts/run.py \
--fs_license /host/verges/tank/data/jack/license.txt \
--psf ${psf} \
--ref_region ${ref_region} \
--pvc-method ${pvc_method} \
--existing-freesurfer-dir /host/verges/tank/data/BIDS_Beijing_FCD/derivatives/fastsurfer \
--skip-hippunfold \
--pvc-n_iter 20 \
${BIDS_DIR} ${OUTPUT_DIR} participant \
--cores ${CORES} \
--participant-label ${test_subject} 

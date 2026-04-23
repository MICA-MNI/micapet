#!/bin/sh

# FDG test for MICA-PET pipeline
# This script is intended to be run inside the MICA-PET Singularity container.
# It performs a basic test of the MICA-PET pipeline using a small subset of data.

# for subj in PX005; do qsub -q mica.q -l h_vmem=30G -N sub-${subj}_MICA-PET_MICs -e /host/fladgate/local_raid/jack/scratch/logs/${subj}_MICA-PET_MICs.txt -o /host/fladgate/local_raid/jack/scratch/logs/${subj}_MICA-PET_MICs.txt /host/fladgate/local_raid/jack/FDG/MICA-PET/scripts/tests/MICA-PET_FDG_test.sh ${subj}; done

# Set variables for test subject, session, and tracer
MICA_PET_VERSION="v.alpha.0.5.7"
test_subject=$1
test_session="01"
BIDS_DIR="/host/verges/tank/data/jack/FDG/BIDS_MICs_FDG"
OUTPUT_DIR="${BIDS_DIR}/derivatives"
CORES=32
psf=3.3
ref_region="pons"
pvc_method="RBV-FS"
existing_freesurfer_dir="/host/verges/tank/data/jack/tmpdir/freesurfer"
existing_hippunfold_dir="/host/verges/tank/data/jack/tmpdir/hippunfold_v1.3.0"

# remove old outputs
# rm -rf ${OUTPUT_DIR}/MICA-PET_${MICA_PET_VERSION}/sub-${test_subject}

# Run the MICA-PET pipeline on the test data

singularity run --cleanenv --env FS_LICENSE="/jack/license.txt" \
-B /host:/host -B ${BIDS_DIR}:/bids -B /data_:/data_ \
-B /host/verges/tank/data/jack:/jack \
/host/fladgate/local_raid/jack/FDG/MICA-PET/scripts/micapet_${MICA_PET_VERSION}.sif \
--fastsurfer_img /jack/fastsurfer-cpu-v2.4.2.sif \
--hippunfold_img /jack/hippunfold_v1.4.1.sif \
--fs_license /jack/license.txt \
--psf ${psf} \
--ref_region ${ref_region} \
--smoothing 5 10 \
--pvc-method ${pvc_method} \
--existing-freesurfer-dir ${existing_freesurfer_dir} \
--existing-hippunfold-dir ${existing_hippunfold_dir} \
/bids /bids/derivatives participant \
--cores ${CORES} \
--participant-label ${test_subject} 

# conda run -n mica-pet python /host/fladgate/local_raid/jack/FDG/MICA-PET/scripts/run.py \
# --fs_license /host/verges/tank/data/jack/license.txt \
# --psf ${psf} \
# --ref_region ${ref_region} \
# --smoothing 5 10 \
# --pvc-method ${pvc_method} \
# --existing-hippunfold-dir ${existing_hippunfold_dir} \
# --existing-freesurfer-dir ${existing_freesurfer_dir} \
# ${BIDS_DIR} ${OUTPUT_DIR} participant \
# --cores ${CORES} \
# --participant-label ${test_subject} 
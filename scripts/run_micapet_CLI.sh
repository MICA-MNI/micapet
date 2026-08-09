#!/bin/bash
# Helper script to run MICA-PET using the CLI on a single subject/session
# MICA-PET v.beta.0.1
# Usage: ./run_micapet_CLI.sh <subject_id>

subject=$1
RUN_path=            #to fill; /path/to/micapet/run.py
BIDS_DIR=            #to fill; /path/to/bids
DERIVATIVES_DIR=     #to fill; /path/to/bids/derivatives
FS_LICENSE=          #to fill; /path/to/license.txt

FS_IMG=              #to fill; /path/to/fastsurfer-cpu-v2.4.2.sif
FS_DIR=              #to fill; /path/to/freesurfer
HIPPUNFOLD_IMG=      #to fill; /path/to/hippunfold_v1.4.1.sif
CORES=               #to fill; number of cores to use (eg. 16, 32, all, etc.)
psf=                 #to fill; point spread function (PSF) in mm (eg. 3, 6, etc.)
ref_region=          #to fill; reference region for SUVR calculation 
                     # (eg. "pons", "cerebellarGM", "cerebellum", "composite", "cerebellum", "WM", "GM", etc.)
pvc_method=          #to fill; partial volume correction method (eg. "RBV-FS","MG","IY")
EXISTING_FS_DIR=      #to fill; if previoulsy run, path to existing FreeSurfer/FastSurfer subject derivatives 
                     # (eg. /path/to/bids/derivatives/fastsurfer/sub-<subject_id>_ses-<session_id>). Otherwise remove this line and the --existing-freesurfer-dir argument from the singularity command below.
EXISTING_HIPPUNFOLD_DIR= #to fill; if previously run, path to existing HippoUnfold derivatives 
                     # (eg. /path/to/bids/derivatives/hippunfold_v1.4.1/hippunfold/sub-<subject_id>/ses-<session_id>). Otherwise remove this line and the --existing-hippunfold-dir argument from the singularity command below.

${RUN_path} \
--fastsurfer_img ${FS_IMG} \
--hippunfold_img ${HIPPUNFOLD_IMG} \
--fs_license ${FS_LICENSE} \
--psf ${psf} \
--ref_region ${ref_region} \
--smoothing 5 10 \
--pvc-method ${pvc_method} \
--existing-freesurfer-dir ${EXISTING_FS_DIR} \
--existing-hippunfold-dir ${EXISTING_HIPPUNFOLD_DIR} \
${BIDS_DIR} ${DERIVATIVES_DIR} participant \
--cores ${CORES} \
--participant-label ${subject}

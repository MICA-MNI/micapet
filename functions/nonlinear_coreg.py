#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for linear co-registration of PET to MRI.
The script requires the following arguments:
    -trc        : Tracer (eg. FDG, MK6240)
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -subj_dir : Specify path to FreeSurfer/FastSurfer subjects directory. (Default fastsurfer subdirectory in BIDS derivatives directory.)
    -pvc_method : PVC method used for PET image. Options: 'RBV-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'. Default: 'RBV-FS'.
    -pet        : (Optional) Specify path to PET nifti file. Default: sub-<sub>_ses-<ses>_trc-<trc>_pet.nii.gz in pet BIDS directory.
    -ref_region : Reference regions to use. eg. ['pons','cerebellarGM','composite']. Default: ['pons'].
    -out        : (Optional) Output directory. Default: BIDS directory.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import glob
import os
import shutil
import sys
from datetime import datetime
from nipype.interfaces.freesurfer import MRIConvert
from nipype.interfaces.ants import RegistrationSynQuick, ApplyTransforms

# Load utilities functions from utils.py
import utils

# Set the working directory to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)

# Argument Parsing
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("-trc", type=str, dest='trc', default='FDG',help="(Str) Select tracer for analysis ('FDG','MK6240'). (Default 'FDG').")
parser.add_argument("-pvc_method", dest="pvc_method", type=str, default='RBV-FS', choices=['RBV-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'], help="(Str) PVC method used for PET image. Options: 'RBV-FS', 'MG','IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL' etc. Default: 'RBV-FS'.")
parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
parser.add_argument("-subj_dir", dest="subj_dir", type=str, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-pet", dest="pet", type=str, help="(Str) Path to PET nifti file. Default: sub-<sub>_ses-<ses>_trc-<trc>_pet.nii.gz in pet BIDS directory.")
parser.add_argument("-ref_region",dest="ref_region", type=str, choices=['pons','cerebellarGM','composite'], default='pons',help="Specify reference region. Default: pons.")
parser.add_argument("-output_dir", dest="output_dir", type=str, help="(Str) Specify output directory for MICA-PET derivatives. Default: {bids_dir}/derivatives/MICA-PET_{version}")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
    sys.exit(1)
    
# Normalize paths and variables
trc = args.trc
pvc_method = args.pvc_method
session = f"{args.ses.replace('ses-', '')}"
subject = f"{args.sub.replace('sub-', '')}"
bids_dir = os.path.realpath(args.bids_dir)
ref_region = args.ref_region
if args.subj_dir is None: #check if user inputted subj_dir
    subj_dir = f"{bids_dir}/derivatives/fastsurfer"
    print(f"FreeSurfer/FastSurfer directory not provided. Using default: {subj_dir}")
    if not os.path.exists(subj_dir):
        print("ERROR: FastSurfer directory does not exist. Please enter a valid -subj_dir.")
        sys.exit(1)
else:
    subj_dir = os.path.realpath(args.subj_dir)
    if not os.path.exists(subj_dir):
        print("ERROR: FreeSurfer/FastSurfer directory does not exist. Please enter a valid -subj_dir.")
        sys.exit(1)

mica_pet_version = os.environ['MICA_PET_VERSION']
# Support custom output_dir or default to bids_dir/derivatives
if args.output_dir is not None:
    mica_pet_derivatives = os.path.join(os.path.realpath(args.output_dir), f"MICA-PET_{mica_pet_version}")
else:
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"
    
mni_aparc_aseg = f"{repo_dir}/surfaces/mni_icbm152_t1_tal_nlin_sym_09a_aparc.DKTatlas+aseg.nii.gz"
subj_aparc_aseg = f"{subj_dir}/sub-{subject}_ses-{session}/mri/aparc.DKTatlas+aseg.nii.gz"

#convert mgz to nii.gz
if not os.path.exists(f"{subj_dir}/sub-{subject}_ses-{session}/mri/aparc.DKTatlas+aseg.nii.gz"):
    mc = MRIConvert()
    mc.inputs.in_file = f"{subj_dir}/sub-{subject}_ses-{session}/mri/aparc.DKTatlas+aseg.mgz"
    mc.inputs.out_file = subj_aparc_aseg
    mc.inputs.out_type = 'niigz'
    mc.run()
    
# register subject aparc+aseg to MNI aparc+aseg using antsRegistrationSyNQuick
reg = RegistrationSynQuick()
reg.inputs.dimension = 3
reg.inputs.fixed_image = mni_aparc_aseg
reg.inputs.moving_image = subj_aparc_aseg
reg.inputs.output_prefix = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wFS_to-MNI_"
reg.inputs.transform_type = 's'
reg.inputs.precision_type = 'double'
reg.run()

# apply transforms

for ref in ['none',ref_region]:
    for pvc in ['none',pvc_method]:
        at = ApplyTransforms()
        at.inputs.dimension = 3
        at.inputs.input_image = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.nii.gz"
        at.inputs.reference_image = mni_aparc_aseg
        at.inputs.transforms = [f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wFS_to-MNI_1Warp.nii.gz", f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wFS_to-MNI_0GenericAffine.mat"]
        at.inputs.output_image = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-MNI_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.nii.gz"
        at.inputs.float = True
        at.run()
        

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] PET to MNI nonlinear co-registration completed.")

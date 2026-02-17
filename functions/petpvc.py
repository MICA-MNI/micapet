#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for partial volume correction (PVC) using PETPVC.

The script requires the following arguments:
    -trc        : Tracer (eg. FDG, MK6240)
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -psf        : Scanner PSF FWHM in mm (eg. 4.5)
    -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory.
    -pvc_dir    : (Optional) Specify PVC output directory. (Default {subj_dir}/sub-{subject}_ses-{session}/gtmpvc.output).
    -force      : (Optional) Force PVC even if output exists.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import sys
from datetime import datetime
from nipype.interfaces import freesurfer
from nipype.interfaces.freesurfer import FSCommand, ApplyVolTransform
import nipype.interfaces.petpvc as PETPVC
import nibabel as nib
import numpy as np
import shutil

# Load utilities functions from utils.py
import utils

# Set the working directory to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)

# Argument Parsing
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("-trc", type=str, dest='trc', default='FDG',choices=['FDG','MK6240'],help="(Str) Select tracer for analysis ('FDG','MK6240'). (Default 'FDG').")
parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
parser.add_argument("-psf", dest="psf", type=float, required=True, help="Scanner PSF in mm. Ask your PET physicist if unknown.", default=4.5)
parser.add_argument("-subj_dir", dest="subj_dir", type=str, required=True, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-pvc_dir", dest="pvc_dir", type=str, help="(Str) Specify PVC output directory. (Default {subj_dir}/sub-{subject}_ses-{session}/gtmpvc.output)")
parser.add_argument("-force", action='store_true', help="Force PVC even if output exists.")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir, args.subj_dir, args.psf]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
    sys.exit(1)
    
# Normalize paths and variables
trc = args.trc
session = f"{args.ses.replace('ses-', '')}"
subject = f"{args.sub.replace('sub-', '')}"
bids_dir = os.path.realpath(args.bids_dir)
psf = args.psf
f_surf_dir = f"{os.path.realpath(args.subj_dir)}/sub-{subject}_ses-{session}"
FSCommand.set_default_subjects_dir(args.subj_dir)

mica_pet_version = os.environ['MICA_PET_VERSION']
mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"

force = args.force

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS rawdata directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS derivatives directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting GTMPVC for subject: {subject}, session: {session}.")

# make GM/WM mask
print("Creating GM/WM mask for PVC...")
aseg = nib.load(f"{f_surf_dir}/mri/aseg.mgz")
aseg_data = aseg.get_fdata()
# gm_mask = ((aseg_data == 3)) | ((aseg_data == 42))

gm_mask = ((aseg_data != 2)) & ((aseg_data != 41)) & ((aseg_data != 4)) & ((aseg_data != 43)) & ((aseg_data != 14)) & ((aseg_data != 5)) & ((aseg_data != 44)) & ((aseg_data != 251)) & ((aseg_data != 252)) & ((aseg_data != 253)) & ((aseg_data != 254)) & ((aseg_data != 255)) & ((aseg_data != 15)) & ((aseg_data != 0)) & ((aseg_data != 31)) & ((aseg_data != 63)) & ((aseg_data != 77)) & ((aseg_data != 16)) & ((aseg_data != 7)) & ((aseg_data != 46))

wm_mask = ((aseg_data == 2)) | ((aseg_data == 41)) |((aseg_data == 251)) | ((aseg_data == 252)) | ((aseg_data == 253)) | ((aseg_data == 254)) | ((aseg_data == 255)) | ((aseg_data == 16)) | ((aseg_data == 7)) | ((aseg_data == 46))
gm_wm_mask = np.stack([gm_mask,wm_mask],axis=-1)
nib.save(nib.Nifti1Image(gm_wm_mask,aseg.affine,aseg.header),f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-GMWMmask.nii.gz")

# Run PVC
print("Running PVC...")
pvc = PETPVC.PETPVC()
pvc.inputs.in_file = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-none_ref-none_trc-{trc}_pet.nii.gz'
pvc.inputs.mask_file = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-GMWMmask.nii.gz"
pvc.inputs.out_file = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-MG_ref-none_trc-{trc}_pet.nii.gz"
pvc.inputs.pvc = 'MG'
pvc.inputs.fwhm_x = psf
pvc.inputs.fwhm_y = psf
pvc.inputs.fwhm_z = psf
outs = pvc.run()


##############
# Resample to T1w/nativepro space
def resample_PET(pet,mri,mica_pet_derivatives,subject,session,space):
    print(f"Resampling PET to {space} space...")
    applyreg = ApplyVolTransform()
    applyreg.inputs.source_file= pet
    applyreg.inputs.reg_header=True
    applyreg.inputs.target_file= mri
    applyreg.inputs.transformed_file=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-MG_ref-none_trc-{trc}_pet.nii.gz"
    applyreg.run()

for space in ['T1wNative']:
    pet = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-MG_ref-none_trc-{trc}_pet.nii.gz"
    mri = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
    
    resample_PET(pet,mri,mica_pet_derivatives,subject,session,space)

# Resample aseg to T1w/nativepro space
def resample_aseg(aseg,mri,space):
    print(f"Resampling aseg to {space} space...")
    applyreg = ApplyVolTransform()
    applyreg.inputs.source_file= aseg
    applyreg.inputs.reg_header=True
    applyreg.inputs.interp = 'nearest'
    applyreg.inputs.target_file= mri
    applyreg.inputs.transformed_file=f'{f_surf_dir}/mri/aseg_space-{space}.nii.gz'
    applyreg.run()
    
aseg = f'{f_surf_dir}/mri/aseg.mgz'

for space in ['T1wFS','T1wNative']:
    if space == 'T1wFS':
        mri = f"{f_surf_dir}/mri/orig.mgz"
    else: 
        mri = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
    resample_aseg(aseg,mri,space)


resample_aseg(aseg,mri,'T1w')
# need to run T1w even if space is nativepro, for hippunfold compatibility

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Partial volume correction completed.")

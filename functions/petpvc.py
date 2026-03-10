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
    -pvc_method : PVC method used for PET image. Options: 'rbv', 'MG', 'IY'. Default: 'rbv'.
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
parser.add_argument("-pvc_method", dest="pvc_method", type=str, default='rbv', choices=['rbv', 'MG', 'IY'], help="(Str) PVC method used for PET image. Options: 'rbv', 'MG','IY'. Default: 'rbv'.")
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
pvc_method = args.pvc_method

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
print("Creating mask for PETPVC...")
gtmseg = nib.load(f"{f_surf_dir}/mri/gtmseg_space-T1wFS.nii.gz")
gtmseg_data = gtmseg.get_fdata()

GM_idx = [8, 10, 11, 12, 13,17,18,26,28,47,49,50,51,52,53,54,58,60,172,1002,1003,1005,1006,1007,1008,1009,1010,1011,1012,1013,1014,1015,1016,1017,1018,1019,1020,1021,1022,1023,1024,1025,1026,1027,1028,1029,1030,1031,1034,1035,2002,2003,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2034,2035]
CSF_idx = [4,5,14,15,24,31,43,44,63,257]
WM_idx = [2,7,16,41,46,85,174]
background_idx = [0,130,165,258]

GM_mask = np.isin(gtmseg_data, GM_idx).astype(int)
CSF_mask = np.isin(gtmseg_data, CSF_idx).astype(int)
WM_mask = np.isin(gtmseg_data, WM_idx).astype(int)
background_mask = np.isin(gtmseg_data, background_idx).astype(int)

if pvc_method == 'MG':
    gm_wm_mask = np.stack([GM_mask,WM_mask],axis=-1)
elif pvc_method == 'IY':
    gm_wm_mask = np.stack([GM_mask,WM_mask,CSF_mask,background_mask],axis=-1)
    
nib.save(nib.Nifti1Image(gm_wm_mask,aseg.affine,aseg.header),f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz")

# Run PVC
print("Running PVC...")
pvc = PETPVC.PETPVC()
pvc.inputs.in_file = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-none_ref-none_trc-{trc}_pet.nii.gz'
pvc.inputs.mask_file = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz"
pvc.inputs.out_file = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-{pvc_method}_ref-none_trc-{trc}_pet.nii.gz"
pvc.inputs.pvc = pvc_method
pvc.inputs.fwhm_x = psf
pvc.inputs.fwhm_y = psf
pvc.inputs.fwhm_z = psf
outs = pvc.run()


##############
# Resample to T1w/nativepro space
def resample_PET(pet,mri,mica_pet_derivatives,subject,session,space,pvc_method,trc):
    print(f"Resampling PET to {space} space...")
    applyreg = ApplyVolTransform()
    applyreg.inputs.source_file= pet
    applyreg.inputs.reg_header=True
    applyreg.inputs.target_file= mri
    applyreg.inputs.transformed_file=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc_method}_ref-none_trc-{trc}_pet.nii.gz"
    applyreg.run()

for space in ['T1wNativepro']:
    pet = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-{pvc_method}_ref-none_trc-{trc}_pet.nii.gz"
    mri = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
    
    resample_PET(pet,mri,mica_pet_derivatives,subject,session,space,pvc_method,trc)

# # Resample aseg to T1w/nativepro space
# def resample_aseg(aseg,mri,space):
#     print(f"Resampling aseg to {space} space...")
#     applyreg = ApplyVolTransform()
#     applyreg.inputs.source_file= aseg
#     applyreg.inputs.reg_header=True
#     applyreg.inputs.interp = 'nearest'
#     applyreg.inputs.target_file= mri
#     applyreg.inputs.transformed_file=f'{f_surf_dir}/mri/aseg_space-{space}.nii.gz'
#     applyreg.run()
    
# aseg = f'{f_surf_dir}/mri/aseg.mgz'

# for space in ['T1wFS','T1wNativepro']:
#     if space == 'T1wFS':
#         mri = f"{f_surf_dir}/mri/orig.mgz"
#     else: 
#         mri = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
#     resample_aseg(aseg,mri,space)


# resample_aseg(aseg,mri,'T1w')
# # need to run T1w even if space is nativepro, for hippunfold compatibility

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Partial volume correction completed.")

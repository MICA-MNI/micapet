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
    -pvc_method : PVC method used for PET image. Options: 'RBV-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'. Default: 'RBV-FS'.
    -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory.
    -pvc_dir    : (Optional) Specify PVC output directory. (Default {subj_dir}/sub-{subject}_ses-{session}/gtmpvc.output).
    -pvc_mask   : (Optional) Custom mask to use for PETPVC. Must be a 4D NIfTI with one ROI per frame. Sum across timeframes must be 1 at each voxel. Must be in FreeSurfer/FastSurfer space (eg. orig.mgz). If not provided, a two tissue mask will be generated for MG PVC and a GM+WM+CSF+background mask will be generated for all others.
    -pvc_n_iter : (Optional) Number of iterations for iterative PVC methods (IY). Default: 10.
    -pvc_n_deconv : (Optional) Number of iterations for deconvolution PVC methods (RL, VC). Default: 10.
    -output_dir : (Optional) Specify output directory for MICA-PET derivatives. Default: {bids_dir}/derivatives/MICA-PET_{version}.

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
parser.add_argument("-trc", type=str, dest='trc', default='FDG',help="(Str) Select tracer for analysis (eg. 'FDG','MK6240'). (Default 'FDG').")
parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
parser.add_argument("-psf", dest="psf", type=float, required=True, help="Scanner PSF in mm. Ask your PET physicist if unknown.", default=4.5)
parser.add_argument("-pvc_method", dest="pvc_method", type=str, default='RBV-FS', choices=['RBV-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'], help="(Str) PVC method used for PET image. Options: 'RBV-FS', 'MG','IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL' etc. Default: 'RBV-FS'.")
parser.add_argument("-pvc_mask", dest="pvc_mask", type=str, help="(Str) Optional custom mask to use for PETPVC. Must be a 4D NIfTI with one ROI per frame. Sum across timeframes must be 1 at each voxel. Must be in FreeSurfer/FastSurfer space (eg. orig.mgz).If not provided, a two tissue mask will be generated for MG PVC and a GM+WM+CSF+background mask will be generated for all others.")
parser.add_argument("-subj_dir", dest="subj_dir", type=str, required=True, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-pvc_dir", dest="pvc_dir", type=str, help="(Str) Specify PVC output directory. (Default {subj_dir}/sub-{subject}_ses-{session}/gtmpvc.output)")
parser.add_argument("-pvc_n_iter", dest="pvc_n_iter", type=int, default=10, help="(Int) Number of iterations for iterative PVC methods (IY). Default: 10.")
parser.add_argument("-pvc_n_deconv", dest="pvc_n_deconv", type=int, default=10, help="(Int) Number of iterations for deconvolution PVC methods (RL, VC). Default: 10.")
parser.add_argument("-output_dir", dest="output_dir", type=str, help="(Str) Specify output directory for MICA-PET derivatives. Default: {bids_dir}/derivatives/MICA-PET_{version}")


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
pvc_mask = args.pvc_mask

f_surf_dir = f"{os.path.realpath(args.subj_dir)}/sub-{subject}_ses-{session}"
FSCommand.set_default_subjects_dir(args.subj_dir)

mica_pet_version = os.environ['MICA_PET_VERSION']
# Support custom output_dir or default to bids_dir/derivatives
if args.output_dir is not None:
    mica_pet_derivatives = os.path.join(os.path.realpath(args.output_dir), f"MICA-PET_{mica_pet_version}")
else:
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS rawdata directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS derivatives directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting GTMPVC for subject: {subject}, session: {session}, PVC method: {pvc_method}.")

if pvc_mask is None:
    print("No custom PVC mask provided. Generating default mask.")
    # make GM/WM mask
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
    else:
        gm_wm_mask = np.stack([GM_mask,WM_mask,CSF_mask,background_mask],axis=-1)
        
    nib.save(nib.Nifti1Image(gm_wm_mask,gtmseg.affine,gtmseg.header),f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz")
else:
    print(f"Using custom PVC mask provided at {pvc_mask}.")
    # if mask provided is not f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz", copy it there
    if pvc_mask != f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz":
        print(f"Copying custom PVC mask to {mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz")
        shutil.copy(pvc_mask, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz")

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
if pvc_method == 'IY':
    pvc.inputs.n_iter = args.pvc_n_iter
if pvc_method in ['RL', 'VC']:
    pvc.inputs.n_deconv = args.pvc_n_deconv
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
    mri = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
    
    resample_PET(pet,mri,mica_pet_derivatives,subject,session,space,pvc_method,trc)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Partial volume correction completed.")

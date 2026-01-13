#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for standard uptake value ratio (SUVR) calculation.
GTMseg and partial volume correction must have been run first.

The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory.
    -ref_region : Options: 'pons', 'cerebellarGM', 'composite' (supratentorial white matter, cerebellum, brainstem)

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import sys
from datetime import datetime
import glob
from nipype.interfaces.freesurfer import FSCommand, ApplyVolTransform
import nibabel as nib
import numpy as np
from scipy.ndimage import binary_erosion
import shutil

# Load utilities functions from utils.py
import utils

# Set the working directory to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)

# Argument Parsing
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
parser.add_argument("-subj_dir", dest="subj_dir", type=str, required=True, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-output_dir", dest="output_dir", type=str, help="(Str) Specify output directory for MICA-PET derivatives. Default: {bids_dir}/derivatives/MICA-PET_{version}")
parser.add_argument("-ref_region",dest="ref_region", type=str, action='store',nargs='*', default=['pons'],help="Specify reference region(s). eg: '-ref_region pons cerebellarGM composite'. Default: pons.")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir, args.subj_dir]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
    sys.exit(1)
    
if not any(region in ['pons', 'cerebellarGM', 'composite'] for region in args.ref_region):
    print("Error: None of the reference regions are valid ('pons', 'cerebellarGM', or 'composite').")
    sys.exit(1)
    
# Normalize paths and variables
session = f"{args.ses.replace('ses-', '')}"
subject = f"{args.sub.replace('sub-', '')}"
bids_dir = os.path.realpath(args.bids_dir)
f_surf_dir = f"{os.path.realpath(args.subj_dir)}/sub-{subject}_ses-{session}"
ref_region = args.ref_region

# Support custom output_dir or default to bids_dir/derivatives
mica_pet_version = os.environ['MICA_PET_VERSION']
if args.output_dir is not None:
    mica_pet_derivatives = os.path.join(os.path.realpath(args.output_dir), f"MICA-PET_{mica_pet_version}")
else:
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"

FSCommand.set_default_subjects_dir(args.subj_dir)

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS rawdata directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS derivatives directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)

# Check if gtmseg.mgz exists
if not os.path.exists(f"{f_surf_dir}/mri/gtmseg.mgz"):
    print(f"Error: gtmseg.mgz for subject {subject}, session {session} does not exist. Please run gtm_seg.py first.")
    sys.exit(1)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting reference region creation and SUVR calculation for subject: {subject}, session: {session}.")

def ROImaker(roi,f_surf_dir,mica_pet_derivatives,subject,session,space, erode=False):
    print(f"Creating ROI mask for ROI {roi}...")

    in_file = nib.load(f"{f_surf_dir}/mri/gtmseg_space-{space}.nii.gz")
    in_data = in_file.get_fdata()
    roi_data = np.zeros(in_data.shape)
    # Set values in roi_data to 1 where in_data equals roi
    roi_data[in_data == roi] = 1
    if erode:
        roi_data = binary_erosion(roi_data, iterations=2)
    out_file = nib.Nifti1Image(roi_data, in_file.affine, in_file.header)
    nib.save(out_file, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/tmp_sub-{subject}_ses-{session}_space-{space}_desc-roi{roi}_mask.nii.gz")
    
def combineROIs(ref,mica_pet_derivatives,subject,session,space):
    print(f"Combining ROI masks for reference region: {ref}...")
    mask_files = sorted(glob.glob(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/tmp_sub-{subject}_ses-{session}_space-{space}_desc-roi*_mask.nii.gz"))
    if len(mask_files) == 0:    
        print("Error: No ROI mask files found to combine.")
        sys.exit(1)
    
    # Combine masks using nibabel
    add_mask = nib.load(mask_files[0])
    add_mask_data = add_mask.get_fdata()
    for mask in mask_files[1:]:
        tmp = nib.load(mask)
        tmp_data = tmp.get_fdata()
        add_mask_data += tmp_data
    # Binarize
    add_mask_data[add_mask_data > 0] = 1
    out_file = nib.Nifti1Image(add_mask_data, add_mask.affine, add_mask.header)
    nib.save(out_file, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-{ref}_mask.nii.gz")
    
    # # move mask into same space as PET
    # applyreg = ApplyVolTransform()
    # applyreg.inputs.source_file= f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-{ref}_mask.nii.gz"
    # applyreg.inputs.reg_header=True
    # applyreg.inputs.target_file=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-none_trc-FDG_pet.nii.gz"
    # applyreg.inputs.transformed_file=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_desc-{ref}_mask.nii.gz"
    # applyreg.run()
    
    # delete temporary files
    for mask in mask_files:
        os.remove(mask)
        
## Create ROIs and calculate SUVR       
for space in ['T1wFS','T1wNative']:
    for ref in ref_region:
        print(f"Processing reference region: {ref}...")
        if ref == 'pons':
            for roi in [174]:
                ROImaker(roi,f_surf_dir,mica_pet_derivatives,subject,session,space, erode=True)
        elif ref == 'cerebellarGM':
            for roi in [8,47]:
                ROImaker(roi,f_surf_dir,mica_pet_derivatives,subject,session,space, erode=False)
        elif ref == 'composite':
            for roi in [7,8,16,46,47,174]: # L cerebellar WM, L cerebellar GM, brainstem, R cerebellar WM, R cerebellar GM, pons
                ROImaker(roi,f_surf_dir,mica_pet_derivatives,subject,session,space, erode=False)
            for roi in [2,41]: # L & R WM. To be eroded
                ROImaker(roi,f_surf_dir,mica_pet_derivatives,subject,session,space, erode=True)
        combineROIs(ref,mica_pet_derivatives,subject,session,space)
        
        for pvc in ['none','rbv']:
            # Calculate avg in reference region
            print(f"Calculating average uptake in reference region: {ref}, PVC: {pvc}, space: {space}...")
            
            in_file = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-none_trc-FDG_pet.nii.gz")
            in_data = in_file.get_fdata()
            mask_file = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-{ref}_mask.nii.gz")
            mask_data = mask_file.get_fdata()
            masked_data = in_data[mask_data > 0]
            ref_region_avg = np.mean(masked_data)

            print(f"Reference region {ref}, pvc {pvc}, space {space} average uptake: {ref_region_avg}")

            # Calculate SUVR
            print("Calculating SUVR image...")
            in_file = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-none_trc-FDG_pet.nii.gz")
            in_data = in_file.get_fdata()
            suvr_data = in_data / float(ref_region_avg)
            out_file = nib.Nifti1Image(suvr_data, in_file.affine, in_file.header)
            nib.save(out_file, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-{ref}_trc-FDG_pet.nii.gz")

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SUVR calculation completed.")

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
# from nipype.interfaces.fsl.maths import MathsCommand, BinaryMaths
# from nipype.interfaces.fsl import ImageStats
from nipype.interfaces.freesurfer import FSCommand, ApplyVolTransform
import nibabel as nib
import numpy as np
from scipy.ndimage import morphology
import shutil

# Load utilities functions from utils.py
# from utils import *

# Set the working directory to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)

# Argument Parsing
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
parser.add_argument("-subj_dir", dest="subj_dir", type=str, required=True, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
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
FSCommand.set_default_subjects_dir(args.subj_dir)

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS rawdata directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
if not os.path.exists(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS derivatives directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)

# Check if gtmseg.mgz exists
if not os.path.exists(f"{f_surf_dir}/mri/gtmseg.nii.gz"):
    print(f"Error: gtmseg.nii.gz for subject {subject}, session {session} does not exist. Please run gtm_seg.py first.")
    sys.exit(1)

print(f"Starting reference region creation and SUVR calculation for subject: {subject}, session: {session}")

def ROImaker(roi,f_surf_dir,bids_dir,subject,session, erode=False):
    print(f"Creating ROI mask for ROI {roi}...")
    # make mask for specified index
    # fslmaths = MathsCommand()
    # fslmaths.inputs.in_file = f"{f_surf_dir}/mri/gtmseg.nii.gz"
    # fslmaths.inputs.args = f'-uthr {roi} -thr {roi} -bin'
    # if erode:
    #     print(f"Eroding ROI {roi} mask...")
    #     fslmaths.inputs.args += ' -ero -ero'
    # fslmaths.inputs.out_file = f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat/tmp_sub-{subject}_ses-{session}_space-T1w_desc-roi{roi}_mask.nii.gz"
    # fslmaths.run()
    
    in_file = nib.load(f"{f_surf_dir}/mri/gtmseg.nii.gz")
    in_data = in_file.get_fdata()
    roi_data = in_data.copy()
    # Set values in roi_data to 1 where in_data equals roi
    roi_data[in_data == roi] = 1
    if erode:
        roi_data = morphology.binary_erosion(roi_data, iterations=2)
    out_file = nib.Nifti1Image(roi_data, in_file.affine, in_file.header)
    nib.save(out_file, f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat/tmp_sub-{subject}_ses-{session}_space-T1w_desc-roi{roi}_mask.nii.gz")
    
def combineROIs(ref,bids_dir,subject,session):
    print(f"Combining ROI masks for reference region: {ref}...")
    mask_files = sorted(glob.glob(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat/tmp_sub-{subject}_ses-{session}_space-T1w_desc-roi*_mask.nii.gz"))
    if len(mask_files) == 0:    
        print("Error: No ROI mask files found to combine.")
        sys.exit(1)
        
    # add masks together
    # for mask in mask_files[1:]:
    #     addmask = BinaryMaths()
    #     addmask.inputs.in_file = mask_files[0]
    #     addmask.inputs.operand_file = mask
    #     addmask.inputs.operation = 'add'  # logical OR will be done after binarization
    #     addmask.inputs.out_file = mask_files[0]
    #     addmask.run()
    
    # # binarize combined mask
    # binarize = MathsCommand()
    # binarize.inputs.in_file = mask_files[0]
    # binarize.inputs.out_file = f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1w_desc-{ref}_mask.nii.gz"
    # binarize.inputs.args = '-bin'
    # binarize.run()
    
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
    nib.save(out_file, f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1w_desc-{ref}_mask.nii.gz")
    
    # move mask into same space as PET
    applyreg = ApplyVolTransform()
    applyreg.inputs.source_file= f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1w_desc-{ref}_mask.nii.gz"
    applyreg.inputs.reg_header=True
    applyreg.inputs.target_file=f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-rbv_ref-none_trc-FDG_pet.nii.gz"
    applyreg.inputs.transformed_file=f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1w_desc-{ref}_mask.nii.gz"
    applyreg.run()
    
    # delete temporary files
    for mask in mask_files:
        os.remove(mask)
  
for ref in ref_region: 
    print(f"Processing reference region: {ref}...")
    if ref == 'pons':
        for roi in [174]:
            ROImaker(roi,f_surf_dir,bids_dir,subject,session, erode=True)
    elif ref == 'cerebellarGM':
        for roi in [8,47]:
            ROImaker(roi,f_surf_dir,bids_dir,subject,session, erode=False)
    elif ref == 'composite':
        for roi in [7,8,16,46,47,174]: # L cerebellar WM, L cerebellar GM, brainstem, R cerebellar WM, R cerebellar GM, pons
            ROImaker(roi,f_surf_dir,bids_dir,subject,session, erode=False)
        for roi in [2,41]: # L & R WM. To be eroded
            ROImaker(roi,f_surf_dir,bids_dir,subject,session, erode=True)
    combineROIs(ref,bids_dir,subject,session)

    # Calculate avg in reference region
    print(f"Calculating average uptake in reference region: {ref}...")
    # fslstats = ImageStats()
    # fslstats.inputs.in_file = f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-rbv_ref-none_trc-FDG_pet.nii.gz"
    # fslstats.inputs.op_string=f"-k {bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1w_desc-{ref}_mask.nii.gz -m"
    # fslstats.terminal_output = 'file_split'
    # ref_region_avg = fslstats.run().runtime.stdout
    
    in_file = nib.load(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-rbv_ref-none_trc-FDG_pet.nii.gz")
    in_data = in_file.get_fdata()
    mask_file = nib.load(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1w_desc-{ref}_mask.nii.gz")
    mask_data = mask_file.get_fdata()
    masked_data = in_data[mask_data > 0]
    ref_region_avg = np.mean(masked_data)

    print(f"Reference region ({ref}) average uptake: {ref_region_avg}")

    # Calculate SUVR
    print("Calculating SUVR image...")
    for pvc in ['none','rbv']:
        # fslmaths = MathsCommand()
        # fslmaths.inputs.in_file = f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-{pvc}_ref-none_trc-FDG_pet.nii.gz"
        # fslmaths.inputs.args = f'-div {ref_region_avg}'
        # fslmaths.inputs.out_file = f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-{pvc}_ref-{ref}_trc-FDG_pet.nii.gz"
        # fslmaths.run()
        in_file = nib.load(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-{pvc}_ref-none_trc-FDG_pet.nii.gz")
        in_data = in_file.get_fdata()
        suvr_data = in_data / float(ref_region_avg)
        out_file = nib.Nifti1Image(suvr_data, in_file.affine, in_file.header)
        nib.save(out_file, f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-{pvc}_ref-{ref}_trc-FDG_pet.nii.gz")

print("SUVR calculation completed.")

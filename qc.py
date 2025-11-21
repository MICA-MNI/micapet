#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for mapping FreeSurfer/FastSurfer cortical surfaces to HCP.
FreeSurfer/FastSurfer must have been run first.

The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory.
    -ref_region : Reference regions to use. eg. ['pons','cerebellarGM','composite']. Default: ['pons'].

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
from datetime import datetime
from nipype.interfaces.freesurfer import FSCommand, MRIConvert
from nipype.interfaces.fsl.maths import MathsCommand, BinaryMaths
import sys
import numpy as np
import nilearn
from nilearn import plotting
from brainstat.datasets import fetch_mask, fetch_template_surface
from brainspace.plotting import plot_hemispheres
import hippomaps as hm


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
parser.add_argument("-ref_region",dest="ref_region", type=str, choices=['pons','cerebellarGM','composite'], default='pons',help="Specify reference region. Default: pons.")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir, args.subj_dir]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
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
    
# Check if QC directory made    
qc_dir = f"{bids_dir}/qc/sub-{subject}/ses-{session}"
if not os.path.exists(qc_dir):
    os.mkdir(qc_dir)
    
print(f"Starting QC for subject: {subject}, session: {session}")
                             
# Create brainmasked PET
if not os.path.exists(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-none_ref-{ref_region}_trc-FDG_pet_desc-brainmask.nii.gz"):
    print("Creating brainmasked PET image...")
    mc = MRIConvert()
    mc.inputs.in_file = f'{f_surf_dir}/mri/apas+head.mgz'
    mc.inputs.out_file = f'{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/tmp.brainmask.nii.gz'
    mc.inputs.out_type = 'niigz'
    mc.run()
    
    # binarize
    binarize = MathsCommand()
    binarize.inputs.in_file = f'{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/tmp.brainmask.nii.gz'
    binarize.inputs.out_file = f'{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/tmp.brainmask_bin.nii.gz'
    binarize.inputs.args = '-bin'
    binarize.run()
    
    # multiply
    multiply = BinaryMaths()
    multiply.inputs.in_file = f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-none_ref-{ref_region}_trc-FDG_pet.nii.gz"
    multiply.inputs.operation = 'mul'
    multiply.inputs.operand_file = f'{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/tmp.brainmask_bin.nii.gz'
    multiply.inputs.out_file = f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-none_ref-{ref_region}_trc-FDG_pet_desc-brainmask.nii.gz"
    multiply.run()
    
    # remove temp files
    # os.remove(f'{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/tmp.brainmask.nii.gz')
    # os.remove(f'{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/tmp.brainmask_bin.nii.gz')
    
# make maps
pial_left, pial_right = fetch_template_surface("fslr32k",join=False)
mask = fetch_mask("fslr32k")

## Cortical surface
print("Generating cortical surface QC images...")
tmp_surf_L = nilearn.surface.load_surf_data(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-rbv_ref-pons_smooth-5mm_trc-FDG_pet.func.gii")
tmp_surf_R = nilearn.surface.load_surf_data(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-rbv_ref-pons_smooth-5mm_trc-FDG_pet.func.gii")

to_plot = np.hstack((tmp_surf_L,tmp_surf_R))
to_plot[~mask] = np.nan
plot_hemispheres(pial_left,pial_right,to_plot,color_bar=True, 
                 cmap="jet",color_range=(0,np.max(to_plot[mask])*1.5), embed_nb=True,transparent_bg=True,size=(900,200),nan_color=(0.7, 0.7, 0.7, 1),screenshot=True,filename=f"{qc_dir}/sub-{subject}_ses-{session}_cortical_surf_screenshot.png")

tmp_hcsurf_L = nilearn.surface.load_surf_data(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-rbv_ref-pons_trc-FDG_pet.func.gii")
tmp_hcsurf_R = nilearn.surface.load_surf_data(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-rbv_ref-pons_trc-FDG_pet.func.gii")

to_plot = np.hstack((np.expand_dims(tmp_hcsurf_L,axis=1),np.expand_dims(tmp_hcsurf_R,axis=1)))
hm.plotting.surfplot_canonical_foldunfold(to_plot,hemis=['L','R'],den='2mm',labels=['hipp'],embed_nb=True,transparent_bg=True,tighten_cwindow=True,screenshot=True,filename=f"{qc_dir}/sub-{subject}_ses-{session}_hippounfold_screenshot.png")

plotting.plot_roi(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-none_ref-{ref_region}_trc-FDG_pet_desc-brainmask.nii.gz",
                    bg_img=f"{f_surf_dir}/mri/orig.mgz",
                    display_mode='mosaic',
                    cut_coords=15,
                    alpha=0.6,
                    radiological=True,
                    title=f"Subject {subject} SUVR QC",
                    resampling_interpolation='continuous',
                    output_file=f"{qc_dir}/sub-{subject}_ses-{session}_SUVR_screenshot.png")

print("QC screenshots completed.")
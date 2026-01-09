#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for generating subcortical maps.
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
import sys
import nibabel as nib
import numpy as np
from nibabel.processing import resample_from_to
import csv
from datetime import datetime

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
parser.add_argument("-ref_region",dest="ref_region", type=str, choices=['pons','cerebellarGM','composite','none'], default='pons',help="Specify reference region. Default: pons.")

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
space='T1wFS'

mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{os.environ['MICA_PET_VERSION']}"   

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS derivatives directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
    
# Check if QC directory made    
qc_dir = f"{bids_dir}/qc/sub-{subject}/ses-{session}"
if not os.path.exists(qc_dir):
    os.makedirs(qc_dir, exist_ok=True)

# Begin processing
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting subcortical map generation for subject: {subject}, session: {session}.")

# dict of FS labels for subcortical regions
dict = {'Left-Accumbens-area': 26,
'Left-Amygdala': 18,
'Left-Caudate': 11,
'Left-Hippocampus': 17,
'Left-Pallidum': 13,
'Left-Putamen': 12,
'Left-Thalamus': 10,
'Right-Accumbens-area': 58,
'Right-Amygdala': 54,
'Right-Caudate': 50,
'Right-Hippocampus': 53,
'Right-Pallidum': 52,
'Right-Putamen': 51,
'Right-Thalamus': 49}

src = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-rbv_ref-pons_trc-FDG_pet.nii.gz")
pet_data = src.get_fdata()
tgt = nib.load(f"{f_surf_dir}/mri/aparc+aseg.mgz")
aseg_aparc_data = tgt.get_fdata()

# This uses the header affines by default — equivalent to regheader
resampled = resample_from_to(src, tgt,order=0)

# puts pet in same space as aparc+aseg
pet_resampled_data = resampled.get_fdata()

# Compute means for each region
regions = list(dict.keys())
means = [np.mean(pet_resampled_data[aseg_aparc_data == dict[region]]) for region in regions]

# Write to CSV
output_file = f"{bids_dir}/qc/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_subcortical_means_pvc-rbv_ref-{ref_region}_trc-FDG_pet.csv"
with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(regions)
    writer.writerow(means)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Subcortical map generation completed.")
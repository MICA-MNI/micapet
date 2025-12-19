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

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import sys
from datetime import datetime
from nipype.interfaces.freesurfer import FSCommand, MRIsConvert
from nipype.interfaces.workbench.base import WBCommand

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
mica_pet_version = os.environ['MICA_PET_VERSION']
mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"

FSCommand.set_default_subjects_dir(args.subj_dir)

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS rawdata directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS derivatives directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)

# Check if surface files exists
file_patterns = ["lh.pial", "lh.white", "lh.sphere.reg","rh.pial", "rh.white", "rh.sphere.reg"]
missing_files = [pattern for pattern in file_patterns if not os.path.exists(f"{f_surf_dir}/surf/{pattern}")]
if missing_files:
    print(f"Error: missing surface files for subject {subject}, session {session}. Please ensure FreeSurfer/FastSurfer have been run properly.")
    sys.exit(1)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting FreeSurfer/FastSurfer mapping to fsLR for subject: {subject}, session: {session}.")

        
def freesurfer_resample_prep(
    fs_white,
    fs_pial,
    current_fs_sphere,
    new_sphere,
    midthickness_current_out,
    midthickness_new_out,
    current_gifti_sphere_out):
    """
    Prepare FreeSurfer surfaces for resampling to another sphere (e.g., fs_LR).
    
    Equivalent to the Bash function freesurfer_resample_prep.
    
    Parameters
    ----------
    fs_white : str
        Path to FreeSurfer white surface (e.g., lh.white)
    fs_pial : str
        Path to FreeSurfer pial surface (e.g., lh.pial)
    current_fs_sphere : str
        Path to FreeSurfer spherical registration (e.g., lh.sphere.reg)
    new_sphere : str
        Path to target sphere (e.g., fs_LR sphere)
    midthickness_current_out : str
        Output GIFTI for midthickness on current mesh
    midthickness_new_out : str
        Output GIFTI for midthickness on new mesh
    current_gifti_sphere_out : str
        Output GIFTI for current sphere (must end in '.surf.gii')
    """

    # --- Validate inputs ---
    if not current_gifti_sphere_out.endswith(".surf.gii"):
        raise ValueError("<current_gifti_sphere_out> must end in '.surf.gii'")

    # Temporary file paths
    pid = os.getpid()
    temp_white = f"{midthickness_current_out}.temp{pid}.white.surf.gii"
    temp_pial = f"{midthickness_current_out}.temp{pid}.pial.surf.gii"

    # --- Step 1: Convert FreeSurfer surfaces to GIFTI ---
    MRIsConvert(in_file=fs_white, out_file=temp_white, to_scanner=True).run()
    MRIsConvert(in_file=fs_pial, out_file=temp_pial, to_scanner=True).run()
    MRIsConvert(in_file=current_fs_sphere, out_file=current_gifti_sphere_out).run()

    # --- Step 2: Generate midthickness surface (average of white and pial) ---
    WBCommand(f'wb_command -surface-average {midthickness_current_out} -surf {temp_white} -surf {temp_pial}').run()

    # Clean up temporary files
    for f in [temp_white, temp_pial]:
        if os.path.exists(f):
            os.remove(f)

    # --- Step 3: Resample midthickness surface to new sphere ---
    WBCommand(f'wb_command -surface-resample {midthickness_current_out} {current_gifti_sphere_out} {new_sphere} BARYCENTRIC {midthickness_new_out}').run() 
    
    print(f"✅ Created midthickness surfaces:\n  {midthickness_current_out}\n  {midthickness_new_out}")
    print(f"✅ Sphere (GIFTI): {current_gifti_sphere_out}")
    return {
        "midthickness_current": midthickness_current_out,
        "midthickness_new": midthickness_new_out,
        "sphere_gifti": current_gifti_sphere_out,
    }
    
space='T1wFS'
for hemi in ['lh','rh']:
    hemi_cap = 'L' if hemi=='lh' else 'R'
    for res in ['32k','5k']: 
        freesurfer_resample_prep(
            fs_white=f"{f_surf_dir}/surf/{hemi}.white",
            fs_pial=f"{f_surf_dir}/surf/{hemi}.pial",
            current_fs_sphere=f"{f_surf_dir}/surf/{hemi}.sphere.reg",
            new_sphere=f"{repo_dir}/surfaces/fsLR-{res}.{hemi_cap}.sphere.reg.surf.gii",
            # fs_LR-deformed_to-fsaverage.{hemi_cap}.sphere.{res}_fs_LR.surf.gii",
            midthickness_current_out=f"{f_surf_dir}/surf/sub-{subject}_ses-{session}_hemi-{hemi_cap}_surf-fsnative_label-midthickness.surf.gii",
            midthickness_new_out=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi_cap}_space-{space}_surf-fsLR-{res}_label-midthickness.surf.gii",
            current_gifti_sphere_out=f"{f_surf_dir}/surf/sub-{subject}_ses-{session}_hemi-{hemi_cap}_surf-fsnative_label-sphere.surf.gii"
        )
    
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mapping to fsLR completed.")
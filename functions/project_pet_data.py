#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for projecting PET data to the cortical and/or hippocampal surface.
FreeSurfer/FastSurfer must have been run first.

The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory.
    -hippunfold_dir : Specify path to HippUnfold output directory. (Default: hippunfold subdirectory in BIDS derivatives directory.)
    -ref_region : List of reference regions to use for projection. eg. ['pons','cerebellarGM','composite']. Default: ['pons'].
    -pvc        : Presence of flag will project partial volume corrected data + non-PVC data.
    -cortical   : Presence of flag will perform cortical surface projection.
    -hippocampal: Presence of flag will perform hippocampal surface projection.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import sys
from datetime import datetime
from nipype.interfaces.freesurfer import FSCommand
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
parser.add_argument("-hippunfold_dir", dest="hippunfold_dir", type=str, help="(Str) Specify path to HippUnfold output directory.")
parser.add_argument("-ref_region",dest="ref_region", type=str, action='store',nargs='*', default=['pons'],help="Specify reference region(s). eg: '-ref_region pons cerebellarGM composite'. Default: pons.")
parser.add_argument("-pvc", action='store_true', dest="pvc", help="(Flag) If present, project both partial volume corrected data and non-PVC data.")
parser.add_argument("-cortical", action='store_true', dest="cortical", help="(Flag) If present, perform cortical surface projection.")
parser.add_argument("-hippocampal", action='store_true', dest="hippocampal", help="(Flag) If present, perform hippocampal surface projection.")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir, args.subj_dir]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
    sys.exit(1)
if not (args.cortical or args.hippocampal):
    print("Error: At least one of the flags -cortical or -hippocampal must be specified.")
    parser.print_help()
    sys.exit(1)
if not any(region in ['pons', 'cerebellarGM', 'composite'] for region in args.ref_region):
    print(f"Error: Inputted: {args.ref_region}. None of the reference regions are valid ('pons', 'cerebellarGM', or 'composite').")
    sys.exit(1)
    
# Normalize paths and variables
session = f"{args.ses.replace('ses-', '')}"
subject = f"{args.sub.replace('sub-', '')}"
bids_dir = os.path.realpath(args.bids_dir)
f_surf_dir = f"{os.path.realpath(args.subj_dir)}/sub-{subject}_ses-{session}"

ref_region = args.ref_region
ref_region.append('none')
pvc_options = ['none', 'rbv'] if args.pvc else ['none']
cortical = args.cortical
hippocampal = args.hippocampal

mica_pet_version = os.environ['MICA_PET_VERSION']
mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"
space = os.environ['MICA_PET_SPACE']

FSCommand.set_default_subjects_dir(args.subj_dir)

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS rawdata directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS derivatives directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
    


# check if hippunfold_dir exists
if hippocampal:
    if args.hippunfold_dir is None: #check if user inputted hippunfold_dir
        hippunfold_dir = f"{bids_dir}/derivatives/hippunfold_v1.4.1" 
        if not os.path.exists(hippunfold_dir):
            print(f"Error: HippUnfold directory {hippunfold_dir} does not exist.")
            sys.exit(1)
    else:
        hippunfold_dir = os.path.realpath(args.hippunfold_dir)
        if not os.path.exists(hippunfold_dir):
            print(f"Error: HippUnfold directory {hippunfold_dir} does not exist.")
            sys.exit(1)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting PET data projection to surface for subject: {subject}, session: {session}.")

if cortical:
    print("Doing cortical surface projection.")
    for hemi in ['L','R']:
        for pvc in pvc_options:
            for ref in ref_region:
                print(f"Processing PVC method: {pvc}, reference region: {ref}, hemisphere: {hemi}...")
                SUVR_map=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-{ref}_trc-FDG_pet.nii.gz'
                
                surf_fsnative=f'{f_surf_dir}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-fsnative_label-midthickness.surf.gii'
                
                SUVR_on_surf=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-fsnative_label-midthickness_pvc-{pvc}_ref-{ref}_trc-FDG_pet.func.gii'
                WBCommand(f'wb_command -volume-to-surface-mapping {SUVR_map} {surf_fsnative} {SUVR_on_surf} -trilinear').run()
                
                for surf in ['fsLR-32k','fsLR-5k']:
                    print(f"Resampling to {surf}...")
                    
                    sphere_surf=f'{f_surf_dir}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-fsnative_label-sphere.surf.gii'
                    
                    reg_surf_gii=f'{repo_dir}/surfaces/{surf}.{hemi}.sphere.reg.surf.gii'
                    
                    SUVR_resampled_out=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-{surf}_label-midthickness_pvc-{pvc}_ref-{ref}_smooth-none_trc-FDG_pet.func.gii'
                    
                    WBCommand(f'wb_command -metric-resample {SUVR_on_surf} {sphere_surf} {reg_surf_gii} BARYCENTRIC {SUVR_resampled_out}').run()
                    
                    for smooth in [5,10]:
                        print(f"Smoothing with {smooth}mm kernel...")
                        midthick_surf=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_space-{space}_surf-{surf}_label-midthickness.surf.gii'
                        
                        SUVR_resampled_smooth_out=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-{surf}_label-midthickness_pvc-{pvc}_ref-{ref}_smooth-{smooth}mm_trc-FDG_pet.func.gii'
                        
                        WBCommand(f'wb_command -metric-smoothing {midthick_surf} {SUVR_resampled_out} {smooth} {SUVR_resampled_smooth_out}').run()

if hippocampal:
    print("Doing hippocampal surface projection.")
    for hemi in ['L','R']:
        for pvc in pvc_options:
            for ref in ref_region:
                print(f"Processing PVC method: {pvc}, reference region: {ref}, hemisphere: {hemi}...")
                SUVR_map=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1w_pvc-{pvc}_ref-{ref}_trc-FDG_pet.nii.gz'
                
                if os.path.exists(SUVR_map) is False:
                    print(f"Error: SUVR map in T1w space does not exist... Needed for HippUnfold projection.")
                    sys.exit(1)
                
                hipp_surf=f'{hippunfold_dir}/hippunfold/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_space-T1w_den-2mm_label-hipp_midthickness.surf.gii' #hippunfold space always T1w
                
                SUVR_on_surf=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-hipp_den-2mm_label-midthickness_pvc-{pvc}_ref-{ref}_trc-FDG_pet.func.gii'
                
                WBCommand(f'wb_command -volume-to-surface-mapping {SUVR_map} {hipp_surf} {SUVR_on_surf} -trilinear').run()
                    
        
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] PET data projection completed.")


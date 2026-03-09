#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for partial volume correction (PVC).
For PETSurfer, FreeSurfer/FastSurfer and gtmseg must have been run first.

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
f_surf_dir = f"{os.path.realpath(args.subj_dir)}/sub-{subject}_ses-{session}"
FSCommand.set_default_subjects_dir(args.subj_dir)

mica_pet_version = os.environ['MICA_PET_VERSION']
# Support custom output_dir or default to bids_dir/derivatives
if args.output_dir is not None:
    mica_pet_derivatives = os.path.join(os.path.realpath(args.output_dir), f"MICA-PET_{mica_pet_version}")
else:
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"
    
# gtmpvc.output 
if args.pvc_dir is None: 
    pvc_dir = f"{f_surf_dir}/gtmpvc.output"
else: 
    pvc_dir= os.path.realpath(args.pvc_dir)

force = args.force

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

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting GTMPVC for subject: {subject}, session: {session}.")

gtmpvc = freesurfer.GTMPVC()
gtmpvc.inputs.in_file = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_pet.nii.gz"
gtmpvc.inputs.reg_file = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from-pet_to-T1wFS_xfm.reg.lta'
gtmpvc.inputs.psf = psf
gtmpvc.inputs.segmentation = f"{f_surf_dir}/mri/gtmseg.mgz"
gtmpvc.inputs.auto_mask = (1, 0.01)
gtmpvc.inputs.mgx = 0.01
gtmpvc.inputs.rbv = True
gtmpvc.inputs.subjects_dir = f"{args.subj_dir}"
gtmpvc.inputs.default_seg_merge = True
gtmpvc.inputs.pvc_dir = pvc_dir
print(gtmpvc.cmdline)
# print(f_surf_dir)
# print(args.subj_dir)
gtmpvc.run()

# Resample RBV to T1w/nativepro space
def resample_RBV(rbv,mri,mica_pet_derivatives,subject,session,space):
    print(f"Resampling RBV to {space} space...")
    applyreg = ApplyVolTransform()
    applyreg.inputs.source_file= rbv
    applyreg.inputs.reg_header=True
    applyreg.inputs.target_file= mri
    applyreg.inputs.transformed_file=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-rbv_ref-none_trc-{trc}_pet.nii.gz"
    applyreg.run()

rbv = f"{pvc_dir}/rbv.nii.gz"

for space in ['T1wFS','T1wNative']:
    if space == 'T1wFS':
        mri = f"{f_surf_dir}/mri/orig.mgz"
    else: 
        mri = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
    resample_RBV(rbv,mri,mica_pet_derivatives,subject,session,space)

# if space is nativepro, running both nativepro and T1w space for hippunfold compatibility
    
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Partial volume correction completed.")

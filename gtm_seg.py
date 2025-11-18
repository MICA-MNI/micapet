#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for geometric transfer matrix segmentation.
FreeSurfer or FastSurfer must have first been completed and segmentations verified.
The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -seg_type   : 'freesurfer' or 'fastsurfer'. Default: 'fastsurfer'
    -subj_dir : Specify path to FreeSurfer/FastSurfer subjects directory.
    -force      : (Optional) Force gtmseg even if output exists.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import sys
from datetime import datetime
# from nipype.interfaces.freesurfer.petsurfer import GTMSeg
from nipype.interfaces import freesurfer

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
parser.add_argument("-seg_type", dest="seg_type", type=str, help="'freesurfer' or 'fastsurfer'. Default: 'fastsurfer'.", choices=['freesurfer','fastsurfer'], default="fastsurfer")
parser.add_argument("-subj_dir", dest="subj_dir", type=str, required=True, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-force", action='store_true', help="Force gtmseg even if output exists.")

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
seg_type = args.seg_type.lower()
f_surf_dir = f"{os.path.realpath(args.subj_dir)}/sub-{subject}_ses-{session}"
force = args.force

os.environ['SUBJECTS_DIR'] = os.path.realpath(args.subj_dir)

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
if not os.path.exists(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS derivatives directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)

print(f"Starting gtmseg for subject: {subject}, session: {session}")

# check seg type
if seg_type == 'freesurfer':
    # check if gtmseg was run already
    if os.path.exists(f"{f_surf_dir}/mri/gtmseg.mgz") and force==False:
        print(f"GTMseg was run already for subject {subject}. Exiting.")
        sys.exit(1)
    else:
        gtmseg = freesurfer.GTMSeg()
        gtmseg.inputs.subject_id = f"sub-{subject}_ses-{session}"
        gtmseg.inputs.ctx_annot = ("aparc.DKTatlas.annot",1000,2000)
        gtmseg.run()

elif seg_type == 'fastsurfer':
    if os.path.exists(f"{f_surf_dir}/mri/gtmseg.mgz") and force==False:
        print(f"GTMseg was run already for subject {subject}. Exiting.")
        sys.exit(1)
    else:
        # Create talairach.m3z if it doesn't exist
        if not os.path.exists(f"{f_surf_dir}/mri/transforms/talairach.m3z"):
            ca_register = freesurfer.CARegister()
            ca_register.inputs.in_file=f"{f_surf_dir}/mri/norm.mgz"
            ca_register.inputs.out_file=f"{f_surf_dir}/mri/transforms/talairach.m3z"
            ca_register.inputs.template=f"{os.environ.get('FREESURFER_HOME')}/average/RB_all_2016-05-10.vc700.gca"
            ca_register.inputs.transform=f"{f_surf_dir}/mri/transforms/talairach.lta"
            ca_register.inputs.mask=f"{f_surf_dir}/mri/brainmask.mgz"
            ca_register.inputs.no_big_ventricles=True
            ca_register.inputs.align='after'

            ca_register.run()

            gtmseg = freesurfer.GTMSeg()
            gtmseg.inputs.subject_id = f"sub-{subject}_ses-{session}"
            gtmseg.inputs.ctx_annot = ("aparc.DKTatlas.annot",1000,2000)
            gtmseg.run()
        else:
            gtmseg = freesurfer.GTMSeg()
            gtmseg.inputs.subject_id = f"sub-{subject}_ses-{session}"
            gtmseg.inputs.ctx_annot = ("aparc.DKTatlas.annot",1000,2000)
            gtmseg.run()

mc = freesurfer.MRIConvert()
mc.inputs.in_file = f'{f_surf_dir}/mri/gtmseg.mgz'
mc.inputs.out_file = f'{f_surf_dir}/mri/gtmseg.nii.gz'
mc.inputs.out_type = 'niigz'
mc.run()

print("GTM segmentation completed.")

#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for cortical surface generation with FastSurfer.

The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -threads    : Number of threads to use (default 15)
    -fastsurfer_img: Path to FastSurfer .sif image.
    -tmpdir     : Path to temporary directory.
    -fs_license : Path to FreeSurfer license. (eg. license.txt) 
    -subj_dir : Specify path to FastSurfer subjects directory. (Default fastsurfer subdirectory in BIDS derivatives directory.)
    -T1         : Path to T1w image. (Default T1w image in BIDS directory).
    -force      : (Optional) Force FastSurfer even if output exists.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import sys
from datetime import datetime
from spython.main import Client
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
parser.add_argument("-threads", dest="threads", type=int, help="(Int) Number of threads to use", default=15)
parser.add_argument("-fastsurfer_img", dest="fastsurfer_img", type=str, required=True, help="(Str) Specify path to FastSurfer singularity image.")
parser.add_argument("-tmpdir", dest="tmpdir", type=str, required=True, help="(Str) Specify path to temporary directory.")
parser.add_argument("-fs_license", dest="fs_license", type=str, required=True, help="(Str) Specify path to FreeSurfer license.")
parser.add_argument("-subj_dir", dest="subj_dir", type=str, help="(Str) Specify path to FastSurfer subjects directory.")
parser.add_argument("-T1", dest="T1_path", type=str, help="(Str) Specify path to T1w image. (Default T1w image in BIDS directory).")
parser.add_argument("-force", action='store_true', help="Force FastSurfer even if output exists.")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir, args.fastsurfer_img, args.tmpdir, args.fs_license]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
    sys.exit(1)
    
# Normalize paths and variables
session = f"{args.ses.replace('ses-', '')}"
subject = f"{args.sub.replace('sub-', '')}"
bids_dir = os.path.realpath(args.bids_dir)
threads = args.threads
fastsurfer_img = os.path.realpath(args.fastsurfer_img)
tmpdir = os.path.realpath(args.tmpdir)
fs_license = os.path.realpath(args.fs_license)
if args.subj_dir is None: #check if user inputted subj_dir
    subj_dir = f"{bids_dir}/derivatives/fastsurfer"
    os.makedirs(subj_dir,exist_ok=True) #makes subj_dir if it doesn't already exist
else:
    subj_dir = os.path.realpath(args.subj_dir)

if args.T1_path is None: #check if user inputted T1_path 
    if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"): # if not T1_path inputted, does T1w image exist already in BIDS?
        print(f"Error: T1w image for subject {subject}, session {session} does not exist. Please specify with -T1 flag.")
        sys.exit(1)
    else: 
        T1_path = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
else: 
    T1_path = os.path.realpath(args.T1_path)

force = args.force

if os.path.exists(f"{subj_dir}/sub-{subject}_ses-{session}") and force==False:
    print("FastSurfer already run. Please rerun with -force flag to overwrite.")
    sys.exit(1)
elif os.path.exists(f"{subj_dir}/sub-{subject}_ses-{session}") and force==True:
    shutil.rmtree(f"{subj_dir}/sub-{subject}_ses-{session}")

print(f"Starting FastSurfer for subject {subject}, session {session}.")

# Define command to run inside container
command = [
    "/fastsurfer/run_fastsurfer.sh",
    "--fs_license", "/output/license.txt",
    "--t1", f"/tmpdir/sub-{subject}_ses-{session}_T1w.nii.gz",
    "--sid", f"sub-{subject}_ses-{session}",
    "--sd", "/output",
    "--no_fs_T1",
    "--parallel",
    "--threads", str(threads)
]

# Run using spython
Client.execute(
    image=fastsurfer_img,
    command=command,
    options=[
        "--cleanenv",
        "--writable-tmpfs",
        "--containall",
        "-B", f"{subj_dir}:/output",
        "-B", f"{tmpdir}:/tmpdir",
        "-B", f"{T1_path}:/tmpdir/sub-{subject}_ses-{session}_T1w.nii.gz",
        "-B", f"{fs_license}:/output/license.txt"
    ]
)

print("FastSurfer completed.")

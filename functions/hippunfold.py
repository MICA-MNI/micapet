#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for hippocampal surface generation with HippUnfold.

The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -hippunfold_img: Path to HippUnfold .sif image.
    -hippunfold_dir : Specify path to HippUnfold output directory. (Default: hippunfold subdirectory in BIDS derivatives directory.)
    -tmpdir    : (Optional) Path to temporary directory. (Default /tmp)
    -cachedir  : (Optional) Set HIPPUNFOLD_CACHE_DIR manually. (Default ~/.cache)
    -B          : (Optional) Bind pathway for Singularity (eg. /host or /host,/opt etc)
    -T1         : (Optional) Path to T1w image. (Default T1w image in BIDS directory).
    -force      : (Optional) Force HippUnfold even if output exists.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
# -threads    : Number of threads to use (default 15)


import argparse
import os
import sys
from datetime import datetime
from spython.main import Client
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
parser.add_argument("-threads", dest="threads", type=str, help="(Int/Str) Number of threads to use", default="8")
parser.add_argument("-hippunfold_img", dest="hippunfold_img", type=str, required=True, help="(Str) Specify path to HippUnfold singularity image.")
parser.add_argument("-tmpdir", dest="tmpdir", type=str, help="(Str) Specify path to temporary directory.")
parser.add_argument("-cachedir", dest="cachedir", type=str, help="(Str) Set HIPPUNFOLD_CACHE_DIR manually. (Default ~/.cache).")
parser.add_argument("-hippunfold_dir", dest="hippunfold_dir", type=str, help="(Str) Specify path to HippUnfold output directory.")
parser.add_argument("-B", dest="B",type=str, help="(Str) Specify paths to bind for Singularity. (eg. /host or /host,/opt etc)")
parser.add_argument("-T1", dest="T1_path", type=str, help="(Str) Specify path to T1w image. (Default T1w image in BIDS directory).")
parser.add_argument("-force", action='store_true', help="Force HippUnfold even if output exists.")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir, args.hippunfold_img]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
    sys.exit(1)
    
# Normalize paths and variables
session = f"{args.ses.replace('ses-', '')}"
subject = f"{args.sub.replace('sub-', '')}"
bids_dir = os.path.realpath(args.bids_dir)
# threads = args.threads
hippunfold_img = os.path.realpath(args.hippunfold_img)
if args.tmpdir is None:
    tmpdir = []
else:
    tmpdir = ["--env",f"TMPDIR={os.path.realpath(args.tmpdir)}","-B",os.path.realpath(args.tmpdir)]
    os.environ['TMPDIR'] = args.tmpdir

if args.cachedir is None:
    cachedir = []
else:
    cachedir = ["--env",f"HIPPUNFOLD_CACHE_DIR={os.path.realpath(args.cachedir)}","-B",os.path.realpath(args.cachedir)]
    os.environ['HIPPUNFOLD_CACHE_DIR'] = args.cachedir

threads = args.threads

if args.B is None:
    bind = []
else:
    bind = ["-B",f"{os.path.realpath(args.B)}"]

if args.hippunfold_dir is None: #check if user inputted hippunfold_dir
    hippunfold_dir = f"{bids_dir}/derivatives/hippunfold_v1.4.1"
    os.makedirs(hippunfold_dir,exist_ok=True) #makes hippunfold_dir if it doesn't already exist
else:
    hippunfold_dir = os.path.realpath(args.hippunfold_dir)

if args.T1_path is None: #check if user inputted T1_path 
    if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"): # if not T1_path inputted, does T1w image exist already in BIDS?
        print(f"Error: T1w image for subject {subject}, session {session} does not exist. Please specify with -T1 flag and replace subject name with "+"{subject}.")
        sys.exit(1)
    else: 
        T1_path = []
else: 
    T1_path = ["--path-T1w", f"{os.path.realpath(args.T1_path)}"]

force = args.force
force_command=[]

if os.path.exists(f"{hippunfold_dir}/hippunfold/sub-{subject}/ses-{session}") and force==False: #check if HippUnfold run already & if no force flag
    print("HippUnfold already run. Skipping (use -force to overwrite).")
    sys.exit(0)
elif force==True: # Always pass --force-output when -force flag is set
    force_command=["--force-output", "--rerun-incomplete"] # ensure Snakemake reruns incomplete files

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting HippUnfold for subject {subject}, session {session}.")
# print(os.environ['HIPPUNFOLD_CACHE_DIR'])

# Define HippUnfold args to run inside container
args = [
    "/bids_dir",
    "/output_dir",
    "participant",
    "--participant-label",f"{subject}",
    "--modality", "T1w",
    "--output-density","2mm",
    "--cores", str(threads)
    ]
args.extend(T1_path)
args.extend(force_command)

# Create fake home for Singularity to avoid cache issues
user_home = os.path.expanduser("~")
fake_home = f"{hippunfold_dir}/fake_home"
os.makedirs(fake_home, exist_ok=True)

# set Singularity options
options=["--cleanenv",
        "--no-home",
        "-B", f"{bids_dir}:/bids_dir",
        "-B", f"{hippunfold_dir}:/output_dir",
        "-B", f"{fake_home}:{user_home}"
    ]
options.extend(tmpdir)
options.extend(cachedir)
options.extend(bind)

        # "--writable-tmpfs",
        # "--containall",
        # "--no-privs",
        # ^causing hang?

# print(options)

# Run using spython
if not shutil.which('singularity') and not shutil.which('apptainer'):
    print("ERROR: Singularity/Apptainer executable not found in PATH.")
    print("Please ensure apptainer is installed in the container environment.")
    sys.exit(127)

result = Client.run(
    image=hippunfold_img,
    args=args,
    options=options,
    return_result=True
)

if isinstance(result, dict) and result.get('return_code', 0) != 0:
    print(result.get('message', ''))
    print(f"HippUnfold failed with return code {result['return_code']}")
    sys.exit(result['return_code'])
elif isinstance(result, str):
    print(result)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HippUnfold completed.")
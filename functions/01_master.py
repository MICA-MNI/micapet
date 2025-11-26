#!/usr/bin/env python
# coding: utf-8
# ./01_master.py -sub PXtt169 -ses 01 -bids /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS/ -fastsurfer_img /data/mica1/01_programs/fastsurfer/fastsurfer-cpu-v2.4.2.sif -fs_license /data/mica1/01_programs/freesurfer-7.4.1/license.txt -hippunfold_img /data/mica1/01_programs/singularity/hippunfold_v1.4.1.sif -cachedir /host/verges/tank/data/jack/hippunfold_tmp/ -psf 4.5 -ref_region pons
# for subj in ; do qsub -q mica.q -l h_vmem=30G -N sub-${subj}_FDG_pipe -e /host/fladgate/local_raid/jack/scratch/logs/${subj}_FDG_pipe.txt -o /host/fladgate/local_raid/jack/scratch/logs/${subj}_FDG_pipe.txt ./01_master.py -sub $subj -ses pre -bids /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_20251111TLE_TZ_test/ -seg_type fastsurfer -fastsurfer_img /data/mica1/01_programs/fastsurfer/fastsurfer-cpu-v2.4.2.sif -fs_license /data/mica1/01_programs/freesurfer-7.4.1/license.txt -hippunfold_img /data/mica1/01_programs/singularity/hippunfold_v1.4.1.sif -cachedir /host/verges/tank/data/jack/hippunfold_tmp/ -psf 4.5 -ref_region pons

"""
Master script for MICA-PET pipeline.

The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory. (Default fastsurfer subdirectory in BIDS derivatives directory.)
    -seg_type   : 'freesurfer' or 'fastsurfer'. Default: 'fastsurfer'
    -fastsurfer_img: Provide path to FastSurfer .sif image. Presence of flag will run FastSurfer for cortical surface generation. If not present, assumes FreeSurfer/FastSurfer has already been run.
    -fs_license : If running FastSurfer, provide path to FreeSurfer license. (eg. license.txt).
    
    -hippunfold_img: Presence of flag will run HippUnfold for hippocampal surface generation. Path to HippUnfold .sif image.
    -hippunfold_dir : Specify path to HippUnfold output directory. (Default: hippunfold subdirectory in BIDS derivatives directory.)
    -cachedir   : (Optional) Set HIPPUNFOLD_CACHE_DIR manually. (Default ~/.cache)
    
    -psf        : Scanner PSF FWHM in mm (eg. 4.5)
    -ref_region : Options: 'pons', 'cerebellarGM', 'composite' (supratentorial white matter, cerebellum, brainstem), 'none' (Default: 'pons')
    
    -tmpdir    : (Optional) Path to temporary directory. (Default /tmp)
    -B          : (Optional) Bind pathway for HippUnfold Singularity (eg. /host or /host,/opt etc)
    -T1         : (Optional) Path to T1w image. (Default T1w image in BIDS directory).
    -pet        : (Optional) Path to PET image. (Default PET image in BIDS directory).
    -force      : (Optional) Force run even if output exists.

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
import shutil
import subprocess

# Load utilities functions from utils.py
# from utils import *

def main():
    # Set the working directory to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)

    # Argument Parsing
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
    parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
    parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
    parser.add_argument("-subj_dir", dest="subj_dir", type=str, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
    parser.add_argument("-seg_type", dest="seg_type", type=str, help="'freesurfer' or 'fastsurfer'. Default: 'fastsurfer'.", choices=['freesurfer','fastsurfer'], default="fastsurfer")

    parser.add_argument("-fastsurfer_img", dest="fastsurfer_img", type=str, help="(Str) Specify path to FastSurfer singularity image.")
    parser.add_argument("-fs_license", dest="fs_license", type=str, help="(Str) Specify path to FreeSurfer license.")

    # parser.add_argument("-threads", dest="threads", type=int, help="(Int) Number of threads to use", default=15)
    parser.add_argument("-hippunfold_img", dest="hippunfold_img", type=str, required=True, help="(Str) Specify path to HippUnfold singularity image.")
    parser.add_argument("-tmpdir", dest="tmpdir", type=str, help="(Str) Specify path to temporary directory.")
    parser.add_argument("-cachedir", dest="cachedir", type=str, help="(Str) Set HIPPUNFOLD_CACHE_DIR manually. (Default ~/.cache).")
    parser.add_argument("-hippunfold_dir", dest="hippunfold_dir", type=str, help="(Str) Specify path to HippUnfold output directory.")

    parser.add_argument("-psf", dest="psf", type=float, required=True, help="Scanner PSF in mm. Ask your PET physicist if unknown.", default=4.5)
    parser.add_argument("-ref_region",dest="ref_region", type=str, action='store', default='pons',help="Specify reference region. eg: pons/cerebellarGM/composite. Default: pons.")

    parser.add_argument("-B", dest="B",type=str, help="(Str) Specify paths to bind for Singularity. (eg. /host or /host,/opt etc)")
    parser.add_argument("-T1", dest="T1_path", type=str, help="(Str) Specify path to T1w image. (Default T1w image in BIDS directory).")    
    parser.add_argument("-pet", dest="pet_path", type=str, help="(Str) Specify path to PET image. (Default PET image in BIDS directory).")

    parser.add_argument("-force", dest="force", action='store_true', help="Force HippUnfold even if output exists.")

    args = parser.parse_args()

    # Validate mandatory arguments
    if not all([args.sub, args.ses, args.bids_dir, args.psf]):
        print("Error: One or more mandatory arguments are missing.")
        parser.print_help()
        sys.exit(1)
        
    # Normalize paths and variables
    session = f"{args.ses.replace('ses-', '')}"
    subject = f"{args.sub.replace('sub-', '')}"
    bids_dir = os.path.realpath(args.bids_dir)
    if args.subj_dir is None: #check if user inputted subj_dir
        subj_dir = f"{bids_dir}/derivatives/fastsurfer"
        print(f"FreeSurfer/FastSurfer directory not provided. Using default: {subj_dir}")
        if not os.path.exists(subj_dir):
            print("FastSurfer directory does not exist. Creating it now.")
            os.makedirs(subj_dir, exist_ok=True)
    else:
        subj_dir = os.path.realpath(args.subj_dir)
        if not os.path.exists(subj_dir):
            print("ERROR: FreeSurfer/FastSurfer directory does not exist. Please enter a valid -subj_dir.")
            sys.exit(1)

    seg_type = args.seg_type.lower()
    ref_region = args.ref_region

    fastsurfer_img = os.path.realpath(args.fastsurfer_img) if args.fastsurfer_img else None
    fs_license = os.path.realpath(args.fs_license) if args.fs_license else None
    if fastsurfer_img is None and fs_license is not None:
        print("Error: FastSurfer image not provided. Please provide the path using -fastsurfer_img argument.")
        sys.exit(1)
    elif fastsurfer_img is not None and fs_license is None:
        print("Error: FreeSurfer license not provided. Please provide the path using -fs_license argument.")
        sys.exit(1)
    fastsurfer_run = fastsurfer_img is not None and fs_license is not None

    hippunfold = args.hippunfold_img is not None
    hippunfold_img = os.path.realpath(args.hippunfold_img) if hippunfold else None
        
    if args.hippunfold_dir is None: #check if user inputted hippunfold_dir
        hippunfold_dir = f"{bids_dir}/derivatives/hippunfold_v1.4.1"
        os.makedirs(hippunfold_dir,exist_ok=True) #makes hippunfold_dir if it doesn't already exist
    else:
        hippunfold_dir = os.path.realpath(args.hippunfold_dir)
    if not os.path.exists(hippunfold_dir):
        print("ERROR: HippUnfold directory does not exist. Please enter a valid -hippunfold_dir.")
        sys.exit(1)
        
    if args.tmpdir is None:
        os.makedirs(f"{bids_dir}/derivatives/tmp", exist_ok=True)
        tmpdir_flag = [ "-tmpdir", f"{bids_dir}/derivatives/tmp"]
    else:
        tmpdir_flag = [ "-tmpdir", f"{os.path.realpath(args.tmpdir)}"]  

    if args.cachedir is None:
        cachedir_flag = []
    else:
        cachedir_flag = [ "-cachedir", f"{os.path.realpath(args.cachedir)}"]
    
    if args.force: 
        force_flag = ["-force"]
    else:
        force_flag = []
        
    if args.B is not None:
        bind_flag = ["-B", f"{args.B}"]
    else:
        bind_flag = []


    # create rawdata and derivatives directories if they don't exist
    os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat", exist_ok=True)
    os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet", exist_ok=True)
    os.makedirs(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat", exist_ok=True)
    os.makedirs(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet", exist_ok=True)
    os.makedirs(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/surf", exist_ok=True)
    os.makedirs(f"{bids_dir}/derivatives/fastsurfer", exist_ok=True)
    os.makedirs(f"{bids_dir}/derivatives/hippunfold_v1.4.1", exist_ok=True)
    
    
    # if T1 image not provided, check if it exists in BIDS rawdata
    if args.T1_path is None:
        if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"):
            print(f"Error: T1w image for subject {subject}, session {session} does not exist. Please specify with -T1 flag.")
            sys.exit(1)
    elif not os.path.exists(os.path.realpath(args.T1_path)):
        print(f"Error: Specified T1w image {args.T1_path} does not exist.")
        sys.exit(1)
    else: #copy T1 to BIDS rawdata if not already there
        if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"):
            shutil.copyfile(os.path.realpath(args.T1_path), f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz")
            
    # if PET image not provided, check if it exists in BIDS rawdata
    if args.pet_path is None:
        if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet.nii.gz"):
            print(f"Error: PET image for subject {subject}, session {session} does not exist. Please specify with -pet flag.")
            sys.exit(1)
    elif not os.path.exists(os.path.realpath(args.pet_path)):
        print(f"Error: Specified PET image {args.pet_path} does not exist.")
        sys.exit(1)
    elif not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet.nii.gz"): #copy PET to BIDS rawdata if not already there
            shutil.copyfile(os.path.realpath(args.pet_path), f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet.nii.gz")
        
    # Run FastSurfer if specified
    if fastsurfer_run:
        print("Running FastSurfer...")
        cmd = [f'{script_dir}/fastsurfer.py',"-sub",f'{subject}',"-ses",f'{session}',"-bids",f'{bids_dir}',"-subj_dir",f'{subj_dir}',"-fastsurfer_img",f'{fastsurfer_img}',"-fs_license",f'{fs_license}'] + tmpdir_flag + force_flag
        subprocess.call(cmd)
    
    # # Run HippUnfold if specified
    # if hippunfold:
    #     print("Running HippUnfold...")
    #     cmd = [f'{script_dir}/hippunfold.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-hippunfold_img", f'{hippunfold_img}'] + bind_flag + cachedir_flag + tmpdir_flag + force_flag
    #     subprocess.call(cmd)
    
    # # Linear coreg
    # cmd = [f'{script_dir}/linear_coreg.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-subj_dir", f'{subj_dir}']
    # subprocess.call(cmd)
    
    # # GTM seg
    # cmd = [f'{script_dir}/gtm_seg.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-subj_dir", f'{subj_dir}', "-seg_type", f'{seg_type}']
    # subprocess.call(cmd)
    
    # # PVC
    # cmd = [f'{script_dir}/pvc.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-subj_dir", f'{subj_dir}', "-psf", f'{args.psf}'] + force_flag
    # subprocess.call(cmd)
    
    # # SUVR calculation
    # cmd = [f'{script_dir}/suvr.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-subj_dir", f'{subj_dir}',"-ref_region", f'{ref_region}']
    # subprocess.call(cmd)
        
    # # Cortical surface generation
    # cmd = [f'{script_dir}/cortical_surface.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-subj_dir", f'{subj_dir}']
    # subprocess.call(cmd)
    
    # # Project PET data to surfaces
    # cmd = [f'{script_dir}/project_pet_data.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-subj_dir", f'{subj_dir}', "-hippunfold_dir", f'{hippunfold_dir}', "-pvc", "-ref_region", f'{ref_region}', "-cortical", "-hippocampal"]
    # subprocess.call(cmd)
    
    # # Subcortical maps
    # cmd = [f'{script_dir}/subcortical_map.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-subj_dir", f'{subj_dir}', "-ref_region", f'{ref_region}']
    # subprocess.call(cmd)
    
    # # QC
    # cmd = [f'{script_dir}/qc.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-subj_dir", f'{subj_dir}', "-ref_region", f'{ref_region}']
    # subprocess.call(cmd)
    
    # # Clinical report
    # cmd = [f'{script_dir}/clinical_reports.py', "-sub", f'{subject}', "-ses", f'{session}', "-bids", f'{bids_dir}', "-subj_dir", f'{subj_dir}', "-ref_region", f'{ref_region}']
    # subprocess.call(cmd)
    
    # # Clean up temporary directory
    # if args.tmpdir is None:
    #     shutil.rmtree(f"{bids_dir}/derivatives/tmp")


if __name__ == "__main__":
    main()
#!/usr/bin/env python
# coding: utf-8

"""
Master script for MICA-PET pipeline.

The script takes the following arguments:

    Mandatory arguments:
        -sub        : Subject identification. (ex. PX001)
        -ses        : Session. (ex. 01)
        -bids       : Path to BIDS directory (ex. /data/user/BIDS_FDGPET).
        -psf        : Scanner PSF FWHM in mm (ex. 4.5)
        -ref_region : Options: 'pons', 'cerebellarGM', 'composite' (supratentorial white matter, cerebellum, brainstem), 'none' (Default: 'pons')
        
    If running FastSurfer, the following are mandatory:
        -fastsurfer_img: Provide path to FastSurfer .sif image. Requires version 2.4.2+.
        -fs_license : If running FastSurfer, provide full path to FreeSurfer license (ex. /home/user/license.txt). The license may be obtained here: https://surfer.nmr.mgh.harvard.edu/registration.html
        
    If running HippUnfold, the following are mandatory:
        -hippunfold_img: Path to HippUnfold .sif image. Requires version 1.4.1+.
        
    Optional arguments:
    quired if running HippUnfold:
        -pvc_method : PVC method used for PET image. Options: 'rbv', 'MG'. Default: 'rbv'.
        -trc        : Select tracer for analysis ('FDG','MK6240'). (Default 'FDG').
        -hippunfold_dir : Specify path to HippUnfold output directory. (Default: hippunfold_v1.4.1 subdirectory in BIDS derivatives directory.)
        -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory. (Default: 'fastsurfer' subdirectory in BIDS derivatives directory.)
        -T1         : Path to T1w image. (Default: T1w image in BIDS rawdata directory).
        -pet        : Path to PET image. (Default: PET image in BIDS rawdata directory).

        -skip_FS    : Skip FreeSurfer/FastSurfer. Assumes segmentation already exists in subjects directory and subjects are named sub-{subject}_ses-{session}.
        -skip_hippunfold : Skip HippUnfold. Assumes HippUnfold has already been run.
        
        -cachedir   : Set HIPPUNFOLD_CACHE_DIR manually where the trained UNet model will be stored. After running the first time, the model will be cached here. (Default ~/.cache)
        -tmpdir     : Path to temporary directory. (Default: /bids_dir/derivatives/MICA-PET/sub-{subject}/ses-{session}/tmp)
        -B          : Bind pathway for HippUnfold Singularity (eg. /host or /host,/opt etc)
        -force      : Force run even if output exists.
    
    Select steps in the pipeline to run (if none of the following specified, all steps will be run):
        -fastsurfer : Run FastSurfer for cortical surface generation.
        -hippunfold : Run HippUnfold for hippocampal surface generation.
        -coreg      : Run PET to T1 coregistration.
        -pvc        : Run Partial Volume Correction.
        -suvr       : Run SUVR calculation.
        -cortical_surface: create cortical surface. 
        -project_pet : Project PET data onto surfaces.
        -clinical_report : Generate clinical report.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""

import argparse
import os
import sys
from datetime import datetime
import shutil
import subprocess
from nipype.interfaces.freesurfer import MRIConvert

# os.environ['FREESURFER_HOME'] = '/opt/freesurfer-7.4.1'
os.environ['FREESURFER_HOME'] = '/data/mica1/01_programs/freesurfer-7.4.1'


# Load utilities functions from utils.py
import utils
from utils import bcolors

def display_splash_screen(subject,session,bids_dir,subj_dir,psf,ref_region,seg_type,fastsurfer_img,hippunfold_img,hippunfold_dir,tmpdir,cachedir,force, run_all,fastsurfer_run,hippunfold_run,coreg_run,pvc_run,suvr_run,cortical_surface_run,project_pet_run,clinical_report_run,skip_FS,skip_hippunfold):
    """
    Prints a string centered inside a box made of '#' characters,
    sized to the full width of the terminal.
    """

    try:
        # 1. Get the current terminal width
        width = shutil.get_terminal_size().columns
    except OSError:
        # print(f"{bcolors.ERROR}Error: Could not determine terminal size.{bcolors.RESET}")
        return

    # Ensure the text is not longer than the terminal width
    max_text_len = width - 4  # -4 accounts for the surrounding '#  #' and padding
    
    ### Title ###
    title = f"Running MICA-PET Pipeline"
    # print(f"Title length: {len(title)}")
    
    if len(title) > max_text_len:
        # print(f"{bcolors.ERROR}Error: Text is too long for the current terminal width.{bcolors.RESET}")
        # Truncate the text if necessary
        title = title[:max_text_len - 3] + "..."

    # The text should be printed with one space of padding on the left and right.
    # Total characters used by the frame and inner padding: 4 ('#',' ','text',' ','#')
    
    # Calculate the total inner space available for padding
    inner_width = width - 2 # -2 for the two outer '#' characters
    
    # 2. Calculate the required left and right padding for centering
    # The total space needed for the text and its two inner spaces (' ' + text + ' ')
    title_len = len(title) +2
    
    # Remaining space to be divided for left/right padding
    remaining_space = inner_width - title_len
    
    # Calculate padding for left and right side
    padding_left = remaining_space // 2
    padding_right = remaining_space - padding_left # Takes care of odd remaining space

    # --- 3. Construct the output lines ---

    # A. Content Line (Centered Text)
    # The structure is: # [padding_left] [ ] [text] [ ] [padding_right] #
    title_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{bcolors.BOLD}{bcolors.RED}{title}{bcolors.RESET}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### VERSION ###
    subtitle = f"MICA-PET Version: "
    version = os.environ['MICA_PET_VERSION']
    if len(version) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        version = version[:max_text_len - len(subtitle) - 5] + "..."
    text_len = len(subtitle) + len(version) +2
    
    remaining_space = inner_width - text_len
    padding_left = remaining_space // 2
    padding_right = remaining_space - padding_left
    version_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{bcolors.BOLD}{bcolors.PURPLE}{subtitle}{bcolors.RESET}{version}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### DATETIME ###
    subtitle = f"Start time: "
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if len(current_datetime) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        current_datetime = current_datetime[:max_text_len - len(subtitle) - 5] + "..."
    current_datetime_len = len(subtitle) + len(current_datetime) +2
    
    remaining_space = inner_width - current_datetime_len
    padding_left = remaining_space // 2
    padding_right = remaining_space - padding_left
    current_datetime_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{bcolors.BOLD}{bcolors.BLUE}{subtitle}{bcolors.RESET}{current_datetime}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### JOBS ###
    if run_all:
        jobs_text = "all"
        if skip_FS or skip_hippunfold:
            jobs_text += " (skipping: "
            if skip_FS:
                jobs_text += "FastSurfer"
            if skip_hippunfold:
                if skip_FS:
                    jobs_text += ", "
                jobs_text += "HippUnfold"
            jobs_text += ")"
    else:
        jobs = []
        if fastsurfer_run:
            jobs.append("FastSurfer")
        if hippunfold_run:
            jobs.append("HippUnfold")
        if coreg_run:
            jobs.append("linear coregistration")
        if pvc_run:
            jobs.append("PVC")
        if suvr_run:
            jobs.append("SUVR")
        if cortical_surface_run:
            jobs.append("cortical surface")
        if project_pet_run:
            jobs.append("project PET data")
        if clinical_report_run:
            jobs.append("clinical report")
        jobs_text = ", ".join(jobs) if jobs else "None"
        
    # Top and Bottom Borders (full width of '#')
    border = '#' * width
    # Blank lines for visual spacing
    blank_padding = '#' + ' ' * (width - 2) + '#'

    # --- 4. Print the final box ---
    print("\n"*2)
    print(border)
    print(blank_padding)
    print(title_line)
    print(blank_padding)
    print(version_line)
    print(blank_padding)
    print(current_datetime_line)
    print(blank_padding)
    print_splash_screen_line("Subject: ",subject)
    print_splash_screen_line("Session: ",session)
    print_splash_screen_line("BIDS Directory: ",bids_dir)
    print_splash_screen_line("Subject Directory: ",subj_dir)
    if psf is not None:
        print_splash_screen_line("PSF: ",f"{psf}mm")
    print_splash_screen_line("Reference Region: ",ref_region)
    print_splash_screen_line("Segmentation Type: ",seg_type)
    if fastsurfer_img is not None:
        print_splash_screen_line("FastSurfer Image: ",fastsurfer_img)
    if hippunfold_img is not None:
        print_splash_screen_line("HippUnfold Image: ",hippunfold_img)
    if hippunfold_dir is not None:
        print_splash_screen_line("HippUnfold Directory: ",hippunfold_dir)
    if tmpdir is not None:
        print_splash_screen_line("Temporary Directory: ",tmpdir)
    if cachedir is not None:
        print_splash_screen_line("Cache Directory: ",cachedir)
    print_splash_screen_line("Force: ",str(force))
    print_splash_screen_line("Jobs to run: ",jobs_text)
    print(border)
    print("\n"*2)

def print_splash_screen_line(subtitle, text):
    
    width = shutil.get_terminal_size().columns
    max_text_len = width - 4
    inner_width = width - 2
    blank_padding = '#' + ' ' * (width - 2) + '#'
    
    # Split text into multiple lines if it exceeds the maximum length
    lines = []
    while len(text) + len(subtitle) >= max_text_len:
        # Find the maximum length of text that fits on one line
        split_index = max_text_len - len(subtitle) - 5
        lines.append(text[:split_index])
        text = text[split_index:]
    lines.append(text)  # Add the remaining text

    # Print each line
    for i, line in enumerate(lines):
        if i == 0:
            # First line includes the subtitle
            text_len = len(subtitle) + len(line) + 2
            remaining_space = inner_width - text_len
            padding_left = 2
            padding_right = remaining_space - padding_left
            text_line = (
                f'#' +
                ' ' * padding_left +
                ' ' + f"{bcolors.BOLD}{bcolors.GREEN}{subtitle}{bcolors.RESET}{line}" + ' ' +  # Inner space around text
                ' ' * padding_right +
                f'#'
            )
        else:
            # Subsequent lines do not include the subtitle
            text_len = len(line) + 2
            remaining_space = inner_width - text_len
            padding_left = 10
            padding_right = remaining_space - padding_left
            text_line = (
                f'#' +
                ' ' * padding_left +
                ' ' + f"{line}" + ' ' +  # Inner space around text
                ' ' * padding_right +
                f'#'
            )
        print(text_line)
    print(blank_padding)


def display_subsection_splash_screen(title, log=None):
    """
    Prints a string centered inside a box made of '#' characters,
    sized to the full width of the terminal, and writes it to the log file if provided.
    """
    try:
        # Get the current terminal width
        width = shutil.get_terminal_size().columns
    except OSError:
        width = 80  # Default width if terminal size cannot be determined

    # Ensure the text is not longer than the terminal width
    max_text_len = width - 4  # -4 accounts for the surrounding '#  #' and padding

    if len(title) > max_text_len:
        title = title[:max_text_len - 3] + "..."

    # Calculate padding for centering
    inner_width = width - 2
    title_len = len(title) + 2
    remaining_space = inner_width - title_len
    padding_left = remaining_space // 2
    padding_right = remaining_space - padding_left

    # Construct the output lines
    border = '#' * width
    blank_padding = '#' + ' ' * (width - 2) + '#'
    title_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{bcolors.BOLD}{bcolors.RED}{title}{bcolors.RESET}" + ' ' +
        ' ' * padding_right +
        f'#'
    )

    # Print to terminal
    print("\n" * 2)
    print(border)
    print(blank_padding)
    print(title_line)
    print(blank_padding)
    print(border)
    print("\n" * 2)

    # Write to log file if provided
    if log:
        log.write("\n" * 2)
        log.write(border + "\n")
        log.write(blank_padding + "\n")
        log.write(title_line + "\n")
        log.write(blank_padding + "\n")
        log.write(border + "\n")
        log.write("\n" * 2)

def main():
    
    # Set the working directory to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)

    # Argument Parsing
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("-trc", type=str, dest='trc', default='FDG',choices=['FDG','MK6240'],help="(Str) Select tracer for analysis ('FDG','MK6240'). (Default 'FDG').")
    parser.add_argument("-pvc_method", dest="pvc_method", type=str, default='rbv', choices=['rbv', 'MG'], help="(Str) PVC method used for PET image. Options: 'rbv', 'MG'. Default: 'rbv'.")
    parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
    parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
    parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
    parser.add_argument("-subj_dir", dest="subj_dir", type=str, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory. (Default: 'fastsurfer' subdirectory in BIDS derivatives directory.)")

    parser.add_argument("-skip_FS", dest="skip_FS", action='store_true', help="Skip FreeSurfer/FastSurfer. Assumes segmentation already exists in subjects directory and subjects are named sub-{subject}_ses-{session}.")
    parser.add_argument("-fastsurfer_img", dest="fastsurfer_img", type=str, help="(Str) Specify path to FastSurfer singularity image.")
    parser.add_argument("-fs_license", dest="fs_license", type=str, help="(Str) Specify full path to FreeSurfer license (ex. /home/user/license.txt). The license may be obtained here: https://surfer.nmr.mgh.harvard.edu/registration.html")
    
    parser.add_argument("-skip_hippunfold", dest="skip_hippunfold", action='store_true', help="Skip HippUnfold. Assumes HippUnfold has already been run.")
    parser.add_argument("-hippunfold_img", dest="hippunfold_img", type=str, help="(Str) Specify path to HippUnfold singularity image.")
    parser.add_argument("-tmpdir", dest="tmpdir", type=str, help="(Str) Specify path to temporary directory.")
    parser.add_argument("-cachedir", dest="cachedir", type=str, help="(Str) Set HIPPUNFOLD_CACHE_DIR manually. (Default ~/.cache).")
    parser.add_argument("-hippunfold_dir", dest="hippunfold_dir", type=str, help="(Str) Specify path to HippUnfold output directory.")

    parser.add_argument("-psf", dest="psf", type=float, help="Scanner PSF in mm. Ask your PET physicist if unknown.")
    parser.add_argument("-ref_region",dest="ref_region", type=str, action='store', default='pons',help="Specify reference region. eg: pons/cerebellarGM/composite. Default: pons.")

    parser.add_argument("-B", dest="B",type=str, help="(Str) Specify paths to bind for Singularity. (eg. /host or /host,/opt etc)")
    parser.add_argument("-T1", dest="T1_path", type=str, help="(Str) Specify path to T1w image. (Default T1w image in BIDS directory).")    
    parser.add_argument("-pet", dest="pet_path", type=str, help="(Str) Specify path to PET image. (Default PET image in BIDS directory).")
    
    parser.add_argument("-force", dest="force", action='store_true', help="Force HippUnfold even if output exists.")
    
    parser.add_argument("-fastsurfer", dest="fastsurfer_run", action='store_true', help="Run FastSurfer for cortical surface generation.")
    parser.add_argument("-hippunfold", dest="hippunfold_run", action='store_true', help="Run HippUnfold for hippocampal surface generation.")
    parser.add_argument("-coreg", dest="coreg_run", action='store_true', help="Run PET to T1 coregistration.")
    parser.add_argument("-pvc", dest="pvc_run", action='store_true', help="Run Partial Volume Correction.")
    parser.add_argument("-suvr", dest="suvr_run", action='store_true', help="Run SUVR calculation.")
    parser.add_argument("-cortical_surface", dest="cortical_surface_run", action='store_true', help="Create cortical surface.")
    parser.add_argument("-project_pet", dest="project_pet_run", action='store_true', help="Project PET data onto surfaces.")
    parser.add_argument("-clinical_report", dest="clinical_report_run", action='store_true', help="Generate clinical report.")

    args = parser.parse_args()

    # Validate mandatory arguments
    if not all([args.sub, args.ses, args.bids_dir]):
        print(f"{bcolors.ERROR}Error: One or more mandatory arguments are missing.{bcolors.RESET}")
        parser.print_help()
        sys.exit(1)
        
    # Run all steps if none of the specific steps are selected
    if not any([args.fastsurfer_run, args.hippunfold_run, args.coreg_run, args.pvc_run, args.suvr_run, args.cortical_surface_run, args.project_pet_run, args.clinical_report_run]):
        run_all = True
    else:
        run_all = False

    # Normalize paths and variables
    trc = args.trc
    pvc_method = args.pvc_method
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
            # print(f"{bcolors.ERROR}Error: FreeSurfer/FastSurfer directory does not exist. Please enter a valid -subj_dir.{bcolors.RESET}")
            # sys.exit(1)
            print(f"{bcolors.WARNING}Warning: FreeSurfer/FastSurfer directory does not exist. Creating it now.{bcolors.RESET}")
            os.makedirs(subj_dir, exist_ok=True)
            
    mica_pet_version = os.environ['MICA_PET_VERSION']
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"

    
    ref_region = args.ref_region

    # Validate FastSurfer arguments if running FastSurfer
    skip_FS = args.skip_FS
    
    fastsurfer_img = os.path.realpath(args.fastsurfer_img) if args.fastsurfer_img else None
    fs_license = os.path.realpath(args.fs_license) if args.fs_license else None
    
    if skip_FS==False:
        
        if (run_all==True or args.fastsurfer_run==True) and fastsurfer_img is None and fs_license is not None:
            print(f"{bcolors.ERROR}Error: FastSurfer image not provided or not valid. Please provide the path using -fastsurfer_img argument.{bcolors.RESET}")
            sys.exit(1)
        elif (run_all==True or args.fastsurfer_run==True) and fastsurfer_img is not None and fs_license is None:
            print(f"{bcolors.ERROR}Error: FreeSurfer license not provided or not valid. Please provide the path using -fs_license argument.")
            sys.exit(1)
        elif (run_all==True or args.fastsurfer_run==True) and fastsurfer_img is None and fs_license is None:
            print(f"{bcolors.ERROR}Error: FastSurfer image and FreeSurfer license not provided or not valid. Please provide the paths using -fastsurfer_img and -fs_license arguments.{bcolors.RESET}")
            sys.exit(1)
        elif run_all==False and args.fastsurfer_run==False:
            fastsurfer_run = False
        if (run_all==True or args.fastsurfer_run==True) and fastsurfer_img is not None and fs_license is not None:
            fastsurfer_run = True
            if not os.path.exists(fs_license):
                print(f"{bcolors.ERROR}Error: FreeSurfer license file does not exist. Please enter a valid -fs_license.{bcolors.RESET}")
                sys.exit(1)
    else:
        fastsurfer_run = False
    
    # Determine segmentation type   
    if os.path.exists(f'{subj_dir}/sub-{subject}_ses-{session}/scripts/deep-seg.log'): #deep-seg only exists in fastsurfer
        seg_type = 'fastsurfer'
    else:
        if fastsurfer_run == True:
            seg_type = 'fastsurfer'
        else:
            seg_type = 'freesurfer'
            
    # Validate HippUnfold arguments if running HippUnfold 
    skip_hippunfold = args.skip_hippunfold
    hippunfold_img = os.path.realpath(args.hippunfold_img) if args.hippunfold_img else None
    if args.hippunfold_dir is None: #check if user inputted hippunfold_dir
            hippunfold_dir = f"{bids_dir}/derivatives/hippunfold_v1.4.1"
            os.makedirs(hippunfold_dir,exist_ok=True) #makes hippunfold_dir if it doesn't already exist
    else:
        hippunfold_dir = os.path.realpath(args.hippunfold_dir)
    if not os.path.exists(hippunfold_dir):
        print(f"{bcolors.ERROR}Error: HippUnfold directory does not exist. Please enter a valid -hippunfold_dir.{bcolors.RESET}")
        sys.exit(1)
        
    if skip_hippunfold==False and not run_all: 
        if (run_all==True or args.hippunfold_run==True) and hippunfold_img is None:
            print(f"{bcolors.ERROR}Error: HippUnfold image not provided or not valid. Please provide the path using -hippunfold_img argument.{bcolors.RESET}")
            sys.exit(1)
        elif (run_all==True or args.hippunfold_run==True) and hippunfold_img is not None:
            if not os.path.exists(hippunfold_img):
                print(f"{bcolors.ERROR}Error: HippUnfold singularity image does not exist. Please enter a valid -hippunfold_img.{bcolors.RESET}")
                sys.exit(1)
            hippunfold_run = True
        elif run_all==False and args.hippunfold_run==False:
            hippunfold_run = False
    else:
        hippunfold_run = False
        if not os.path.exists(hippunfold_dir):
            print(f"{bcolors.ERROR}Error: HippUnfold directory does not exist. Please enter a valid -hippunfold_dir.{bcolors.RESET}")
            sys.exit(1)
        
    if args.tmpdir is None:
        tmpdir = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/tmp"
        os.makedirs(tmpdir, exist_ok=True)
    else:
        if not os.path.exists(os.path.realpath(args.tmpdir)):
            print(f"{bcolors.ERROR}Error: Specified temporary directory does not exist. Please enter a valid -tmpdir.{bcolors.RESET}")
            sys.exit(1)
        tmpdir = os.path.realpath(args.tmpdir)
    tmpdir_flag = [ "-tmpdir", tmpdir]  

    if args.cachedir is None:
        cachedir = None
        cachedir_flag = []
    else:
        cachedir = os.path.realpath(args.cachedir)
        cachedir_flag = [ "-cachedir", cachedir]
    
    if args.force: 
        force_flag = ["-force"]
    else:
        force_flag = []
        
    if args.B is not None:
        bind_flag = ["-B", f"{args.B}"]
    else:
        bind_flag = []

    # if T1 image not provided, check if it exists in BIDS rawdata
    if args.T1_path is None:
        if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"):
            print(f"{bcolors.ERROR}Error: T1w image for subject {subject}, session {session} does not exist. Please specify with -T1 flag.{bcolors.RESET}")
            sys.exit(1)
    elif not os.path.exists(os.path.realpath(args.T1_path)):
        print(f"{bcolors.ERROR}Error: Specified T1w image {args.T1_path} does not exist.{bcolors.RESET}")
        sys.exit(1)
    else: #copy T1 to BIDS rawdata if not already there
        if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"):
            # make rawdata directories if they don't exist
            os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat", exist_ok=True)
            
            # shutil.copyfile(os.path.realpath(args.T1_path), f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz")
            mc = MRIConvert()
            mc.inputs.in_file = os.path.realpath(args.T1_path)
            mc.inputs.out_file = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
            mc.inputs.out_type = 'niigz'
            mc.run()
            
    # if PET image not provided, check if it exists in BIDS rawdata
    if args.pet_path is None:
        if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_pet.nii.gz"):
            print(f"{bcolors.ERROR}Error: PET image for subject {subject}, session {session} does not exist. Please specify with -pet flag.{bcolors.RESET}")
            sys.exit(1)
    elif not os.path.exists(os.path.realpath(args.pet_path)):
        print(f"{bcolors.ERROR}Error: Specified PET image {args.pet_path} does not exist.{bcolors.RESET}")
        sys.exit(1)
    elif not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_pet.nii.gz"): #copy PET to BIDS rawdata if not already there
        # make rawdata directories if they don't exist
        os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet", exist_ok=True)
        
        #copy PET file
        shutil.copyfile(os.path.realpath(args.pet_path), f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_pet.nii.gz")
        
    if trc == 'MK6240':
        if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_desc-transmission_pet.nii.gz"):
            print(f"{bcolors.ERROR}Error: Transmission scan for subject {subject}, session {session} does not exist. Please include sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_desc-transmission_pet.nii.gz in the pet subdirectory.{bcolors.RESET}")
            sys.exit(1)
            
    # check if psf specified
    if run_all or args.pvc_run:
        if args.psf is None:
            print(f"{bcolors.ERROR}Error: PSF not specified. Please provide the scanner PSF in mm using -psf argument.{bcolors.RESET}")
            sys.exit(1)

    # create derivatives directories if they don't exist
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat", exist_ok=True)
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet", exist_ok=True)
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf", exist_ok=True)
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm", exist_ok=True)
    os.makedirs(f"{bids_dir}/derivatives/fastsurfer", exist_ok=True)
    os.makedirs(f"{bids_dir}/derivatives/hippunfold_v1.4.1", exist_ok=True)
            
    display_splash_screen(subject,session,bids_dir,subj_dir,args.psf,ref_region,seg_type,fastsurfer_img,hippunfold_img,hippunfold_dir,tmpdir,cachedir,args.force,run_all,fastsurfer_run,hippunfold_run,args.coreg_run,args.pvc_run,args.suvr_run,args.cortical_surface_run,args.project_pet_run,args.clinical_report_run,skip_FS,skip_hippunfold)
    
    # #### Run components of the pipeline ####

    # Define a log file
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/logs", exist_ok=True)
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/logs/MICA-PET_{mica_pet_version}_{current_time}.log"

    # Open the log file for appending
    with open(log_file, "a") as log:
        # Function to print to both terminal and log
        def run_command(cmd):
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in process.stdout:
                print(line, end="")  # Print to terminal
                log.write(line)      # Write to log file
            for line in process.stderr:
                print(line, end="")  # Print errors to terminal
                log.write(line)      # Write errors to log file
            process.wait()
            if process.returncode != 0:
                print(f"{bcolors.ERROR}Error: Command failed with return code {process.returncode}.{bcolors.RESET}")
                sys.exit(process.returncode)

        # Run FastSurfer if specified
        if (run_all == True or fastsurfer_run) and skip_FS == False:
            display_subsection_splash_screen("Running FastSurfer...", log)
            cmd = ['python', '-u', f'{script_dir}/fastsurfer.py', \
                "-sub", \
                f'{subject}', \
                "-ses", \
                f'{session}', \
                "-bids", \
                f'{bids_dir}', \
                "-subj_dir", \
                f'{subj_dir}', \
                "-fastsurfer_img", \
                f'{fastsurfer_img}', \
                "-fs_license", \
                f'{fs_license}'] + tmpdir_flag + force_flag
            run_command(cmd)
            # subprocess.call(cmd)

        # Run HippUnfold if specified
        if (run_all == True or hippunfold_run) and skip_hippunfold == False:
            display_subsection_splash_screen("Running HippUnfold...", log)
            cmd = ['python', '-u', f'{script_dir}/hippunfold.py', \
                "-sub", \
                f'{subject}', \
                "-ses", \
                f'{session}', \
                "-bids", \
                f'{bids_dir}', \
                "-hippunfold_img", \
                f'{hippunfold_img}', \
                "-hippunfold_dir", \
                f'{hippunfold_dir}'] + bind_flag + cachedir_flag + tmpdir_flag + force_flag
            run_command(cmd)
            # subprocess.call(cmd)

        # Linear coreg
        if run_all == True or args.coreg_run == True:
            display_subsection_splash_screen("Running Linear Coregistration...", log)
            cmd = ['python', '-u', f'{script_dir}/linear_coreg.py', \
                "-sub", \
                f'{subject}', \
                "-ses", \
                f'{session}', \
                "-bids", \
                f'{bids_dir}', \
                "-subj_dir", \
                f'{subj_dir}', \
                "-trc",f'{trc}', \
                "-pvc_method", \
                f'{pvc_method}']
            run_command(cmd)

        # GTM seg
        if run_all == True or args.pvc_run == True:
            display_subsection_splash_screen("Running GTM Segmentation...", log)
            cmd = ['python', '-u', f'{script_dir}/gtm_seg.py', \
                "-sub", \
                f'{subject}', \
                "-ses", \
                f'{session}', \
                "-bids", \
                f'{bids_dir}', \
                "-subj_dir", \
                f'{subj_dir}', \
                "-seg_type", \
                f'{seg_type}'] + force_flag
            run_command(cmd)
                
            if pvc_method == 'rbv':
                display_subsection_splash_screen("Running RBV PVC...", log)
                # PVC
                cmd = ['python', '-u', f'{script_dir}/pvc.py', \
                    "-trc", \
                    f'{trc}', \
                    "-sub", \
                    f'{subject}', \
                    "-ses", \
                    f'{session}', \
                    "-bids", \
                    f'{bids_dir}', \
                    "-subj_dir", \
                    f'{subj_dir}', \
                    "-psf", \
                    f'{args.psf}'] + force_flag
                run_command(cmd)
            elif pvc_method == 'MG':
                display_subsection_splash_screen("Running Muller-Gartner PVC...", log)
                cmd = ['python', '-u', f'{script_dir}/petpvc.py', \
                    "-trc", \
                    f'{trc}', \
                    "-sub", \
                    f'{subject}', \
                    "-ses", \
                    f'{session}', \
                    "-bids", \
                    f'{bids_dir}', \
                    "-subj_dir", \
                    f'{subj_dir}', \
                    "-psf", \
                    f'{args.psf}'] + force_flag
                run_command(cmd)
        # SUVR calculation
        if run_all == True or args.suvr_run == True:
            display_subsection_splash_screen("Calculating SUVR...", log)
            cmd = ['python', '-u', f'{script_dir}/suvr.py', \
                "-sub", \
                f'{subject}', \
                "-ses", \
                f'{session}', \
                "-bids", \
                f'{bids_dir}', \
                "-subj_dir", \
                f'{subj_dir}', \
                "-ref_region", \
                f'{ref_region}', \
                "-trc", \
                f'{trc}', \
                "-pvc_method", \
                f'{pvc_method}'] + force_flag
            run_command(cmd)

        # Cortical surface generation
        if run_all == True or args.cortical_surface_run == True:
            display_subsection_splash_screen("Creating Cortical Surfaces...", log)
            cmd = ['python', '-u', f'{script_dir}/cortical_surface.py', \
                "-sub", \
                f'{subject}', \
                "-ses", \
                f'{session}', \
                "-bids", \
                f'{bids_dir}', \
                "-subj_dir", \
                f'{subj_dir}']
            run_command(cmd)

        # Project PET data to surfaces
        if run_all == True or args.project_pet_run == True:
            display_subsection_splash_screen("Projecting PET data to Surfaces...", log)
            cmd = ['python', '-u', f'{script_dir}/project_pet_data.py', \
                "-sub", \
                f'{subject}', \
                "-ses", \
                f'{session}', \
                "-bids", \
                f'{bids_dir}', \
                "-subj_dir", \
                f'{subj_dir}', \
                "-hippunfold_dir", \
                f'{hippunfold_dir}', \
                "-pvc_method", \
                f'{pvc_method}', \
                "-trc", \
                f'{trc}', \
                "-ref_region", \
                f'{ref_region}', \
                "-cortical", \
                "-hippocampal"]+tmpdir_flag
            run_command(cmd)

            # Subcortical maps
            cmd = ['python', '-u', f'{script_dir}/subcortical_map.py', \
                "-sub", \
                f'{subject}', \
                "-ses", \
                f'{session}', \
                "-bids", \
                f'{bids_dir}', \
                "-subj_dir", \
                f'{subj_dir}', \
                "-ref_region", \
                f'{ref_region}', \
                "-pvc_method", \
                f'{pvc_method}', \
                "-trc", \
                f'{trc}']
            run_command(cmd)

        # QC
        if run_all == True or args.clinical_report_run == True:
            display_subsection_splash_screen("Generating Clinical Report...", log)
            cmd = ['python', '-u', f'{script_dir}/qc.py', \
                "-sub", \
                f'{subject}', \
                "-ses", \
                f'{session}', \
                "-bids", \
                f'{bids_dir}', \
                "-subj_dir", \
                f'{subj_dir}', \
                "-ref_region", \
                f'{ref_region}', \
                "-trc", \
                f'{trc}', \
                "-pvc_method", \
                f'{pvc_method}']
            run_command(cmd)

            if trc == 'FDG':
                # Clinical report
                cmd = ['python', '-u', f'{script_dir}/clinical_reports.py', \
                    "-sub", \
                    f'{subject}', \
                    "-ses", \
                    f'{session}', \
                    "-bids", \
                    f'{bids_dir}', \
                    "-subj_dir", \
                    f'{subj_dir}', \
                    "-ref_region", \
                    f'{ref_region}']
                run_command(cmd)
    
    # Clean up temporary directory
    # if args.tmpdir is None:
    #     shutil.rmtree(tmpdir)

if __name__ == "__main__":
    main()
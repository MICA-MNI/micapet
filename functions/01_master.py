#!/usr/bin/env python
# coding: utf-8

"""
Master script for MICA-PET pipeline.

The script takes the following arguments:

    Mandatory arguments:
        -sub        : Subject identification. (ex. PX001)
        -ses        : Session. (ex. 01)
        -bids       : Path to BIDS directory ( . or FULL PATH)
        -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory. (Default fastsurfer subdirectory in BIDS derivatives directory.)
        -psf        : Scanner PSF FWHM in mm (ex. 4.5)
        -ref_region : Options: 'pons', 'cerebellarGM', 'composite' (supratentorial white matter, cerebellum, brainstem), 'none' (Default: 'pons')
        
    Optional arguments:
        -T1         : (Optional) Path to T1w image. (Default: T1w image in BIDS rawdata directory).
        -pet        : (Optional) Path to PET image. (Default: PET image in BIDS rawdata directory).
        -seg_type   : If FastSurfer/FreeSurfer already run, specify if 'freesurfer' or 'fastsurfer' was done. (Default: 'fastsurfer')
        
        -fastsurfer_img: Provide path to FastSurfer .sif image. Presence of flag will run FastSurfer for cortical surface generation. If not present, assumes FreeSurfer/FastSurfer has already been run.
        -fs_license : If running FastSurfer, provide path to FreeSurfer license. (eg. license.txt).
        
        -hippunfold_img: Path to HippUnfold .sif image. Presence of flag will run HippUnfold for hippocampal surface generation. Otherwise, assumes HippUnfold has already been run.
        -hippunfold_dir : Specify path to HippUnfold output directory. (Default: hippunfold_v1.4.1 subdirectory in BIDS derivatives directory.)
        -cachedir   : Set HIPPUNFOLD_CACHE_DIR manually where the trained UNet model will be stored. After running the first time, the model will be cached here. (Default ~/.cache)
        
        -tmpdir    : (Optional) Path to temporary directory. (Default /tmp)
        -B          : (Optional) Bind pathway for HippUnfold Singularity (eg. /host or /host,/opt etc)
        -force      : (Optional) Force run even if output exists.
    
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
# -threads    : Number of threads to use (default 15)


import argparse
import os
import sys
import time
from datetime import datetime
import shutil
import subprocess

# Load utilities functions from utils.py
# from utils import *

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_splash_screen():
    # clear_screen()
    # print("\n" * 3)  # Add some vertical spacing
    # Print '#' characters based on the terminal window width
    try:
        terminal_width = shutil.get_terminal_size().columns
        print('#' * terminal_width)
    except OSError:
        print("###################################################")
    print("#")
    print("#","Running MICA-PET Pipeline".center(terminal_width))
    print("#")
    print("#","Loading... Please wait.".center(terminal_width))
    try:
        terminal_width = shutil.get_terminal_size().columns
        print('#' * terminal_width)
    except OSError:
        print("###################################################")
    print("\n" * 3)
    time.sleep(3)  # Display the splash screen for 3 seconds
    # clear_screen()

def print_centered_box():#subject,session,bids_dir,subj_dir,psf,ref_region,seg_type,fastsurfer_img,hippunfold_img,hippunfold_dir,tmpdir,cachedir,force):
    subject = "PX001"  # Example subject, replace with actual variable
    session = "01"    # Example session, replace with actual variable 
    bids_dir = "/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_20251111TLE_TZ_test"  # Example BIDS directory, replace with actual variable  
    subj_dir = "/host/fladgate/local_raid/jack/FDG/MICA-PET/derivatives/fastsurfer"  # Example subjects directory, replace with actual variable
    psf = 4.5
    ref_region = "pons"
    seg_type = "fastsurfer"
    fastsurfer_img = None  # "/path/to/fastsurfer.sif"
    hippunfold_img = "/path/to/hippunfold.sif"
    hippunfold_dir = "/host/fladgate/local_raid/jack/FDG/MICA-PET/derivatives/hippunfold_v1.4.1"  # Example HippUnfold directory, replace with actual variable
    tmpdir = "/tmp"
    cachedir = "~/.cache"
    force = False
    """
    Prints a string centered inside a box made of '#' characters,
    sized to the full width of the terminal.
    """
    RED = '\033[91m'     # Bright Red
    GREEN = '\033[92m'   # Bright Green
    BLUE = '\033[94m'    # Bright Blue
    BOLD = '\033[1m'     # Bold text
    RESET = '\033[0m'    # Reset color and style
    try:
        # 1. Get the current terminal width
        width = shutil.get_terminal_size().columns
    except OSError:
        # print("Error: Could not determine terminal size.")
        return

    # Ensure the text is not longer than the terminal width
    max_text_len = width - 4  # -4 accounts for the surrounding '#  #' and padding
    
    ### Title ###
    title = f"Running MICA-PET Pipeline"
    # print(f"Title length: {len(title)}")
    
    if len(title) > max_text_len:
        # print("Error: Text is too long for the current terminal width.")
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
        ' ' + f"{BOLD}{RED}{title}{RESET}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    # In case of tiny terminals, ensure the line still starts and ends with '#'
    # if len(content_line) != width:
    #     # Fallback for very small widths where the math might break; ensure it is cut to width
    #     content_line = content_line[:width-1] + '#'

    ### SUBJECT ###
    subtitle = f"Subject: "
    if len(subject) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        subject = subject[:max_text_len - len(subtitle) - 5] + "..."
    subject_len = len(subtitle) + len(subject) +2
    
    remaining_space = inner_width - subject_len
    padding_left = 2
    padding_right = remaining_space - padding_left
    subject_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{subject}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### SESSION ###
    subtitle = f"Session: "
    if len(session) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        session = session[:max_text_len - len(subtitle) - 5] + "..."
    session_len = len(subtitle) + len(session) +2
    
    remaining_space = inner_width - session_len
    padding_left = 2
    padding_right = remaining_space - padding_left
    session_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{session}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### BIDS DIR ###
    subtitle = f"BIDS Directory: "
    if len(bids_dir) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        bids_dir = bids_dir[:max_text_len - len(subtitle) - 5] + "..."
    bids_dir_len = len(subtitle) + len(bids_dir) +2
    
    remaining_space = inner_width - bids_dir_len
    padding_left = 2
    padding_right = remaining_space - padding_left
    bids_dir_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{bids_dir}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### SUBJ DIR ###
    subtitle = f"Subject Directory: "
    if len(subj_dir) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        subj_dir = subj_dir[:max_text_len - len(subtitle) - 5] + "..."
    subj_dir_len = len(subtitle) + len(subj_dir) +2
    
    remaining_space = inner_width - subj_dir_len
    padding_left = 2
    padding_right = remaining_space - padding_left
    subj_dir_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{subj_dir}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### PSF ###
    subtitle = f"PSF: "
    psf = str(psf)
    if len(psf) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        psf = psf[:max_text_len - len(subtitle) - 7] + "..."
    psf_len = len(subtitle) + len(psf) +2 +2
    
    remaining_space = inner_width - psf_len
    padding_left = 2
    padding_right = remaining_space - padding_left
    psf_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{psf}mm" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### REF REGION ###
    subtitle = f"Reference Region: "
    if len(ref_region) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        ref_region = ref_region[:max_text_len - len(subtitle) - 5] + "..."
    ref_region_len = len(subtitle) + len(ref_region) +2
    
    remaining_space = inner_width - ref_region_len
    padding_left = 2
    padding_right = remaining_space - padding_left
    ref_region_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{ref_region}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### SEG TYPE ###
    subtitle = f"Segmentation Type: "
    if len(seg_type) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        seg_type = seg_type[:max_text_len - len(subtitle) - 5] + "..."
    seg_type_len = len(subtitle) + len(seg_type) +2
    
    remaining_space = inner_width - seg_type_len
    padding_left = 2
    padding_right = remaining_space - padding_left
    seg_type_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{seg_type}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
    ### FastSurfer IMG ###
    if fastsurfer_img is not None:
        subtitle = f"FastSurfer Image: "
        if len(fastsurfer_img) + len(subtitle) > max_text_len:
            # Truncate the text if necessary
            fastsurfer_img = fastsurfer_img[:max_text_len - len(subtitle) - 5] + "..."
        fastsurfer_img_len = len(subtitle) + len(fastsurfer_img) +2
        
        remaining_space = inner_width - fastsurfer_img_len
        padding_left = 2
        padding_right = remaining_space - padding_left
        fastsurfer_img_line = (
            f'#' +
            ' ' * padding_left +
            ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{fastsurfer_img}" + ' ' +  # Inner space around text
            ' ' * padding_right +
            f'#'
        )
        
    ### HIPPUNFOLD IMG ###
    if hippunfold_img is not None:
        subtitle = f"HippUnfold Image: "
        if len(hippunfold_img) + len(subtitle) > max_text_len:
            # Truncate the text if necessary
            hippunfold_img = hippunfold_img[:max_text_len - len(subtitle) - 5] + "..."
        hippunfold_img_len = len(subtitle) + len(hippunfold_img) +2
        
        remaining_space = inner_width - hippunfold_img_len
        padding_left = 2
        padding_right = remaining_space - padding_left
        hippunfold_img_line = (
            f'#' +
            ' ' * padding_left +
            ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{hippunfold_img}" + ' ' +  # Inner space around text
            ' ' * padding_right +
            f'#'
        )
    
    ### HIPPUNFOLD DIR ###
    if hippunfold_dir is not None:
        subtitle = f"HippUnfold Directory: "
        if len(hippunfold_dir) + len(subtitle) > max_text_len:
            # Truncate the text if necessary
            hippunfold_dir = hippunfold_dir[:max_text_len - len(subtitle) - 5] + "..."
        hippunfold_dir_len = len(subtitle) + len(hippunfold_dir) +2
        
        remaining_space = inner_width - hippunfold_dir_len
        padding_left = 2
        padding_right = remaining_space - padding_left
        hippunfold_dir_line = (
            f'#' +
            ' ' * padding_left +
            ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{hippunfold_dir}" + ' ' +  # Inner space around text
            ' ' * padding_right +
            f'#'
        )
    
    ### TMP DIR ###
    if tmpdir is not None:
        subtitle = f"Temporary Directory: "
        if len(tmpdir) + len(subtitle) > max_text_len:
            # Truncate the text if necessary
            tmpdir = tmpdir[:max_text_len - len(subtitle) - 5] + "..."
        tmpdir_len = len(subtitle) + len(tmpdir) +2
        
        remaining_space = inner_width - tmpdir_len
        padding_left = 2
        padding_right = remaining_space - padding_left
        tmpdir_line = (
            f'#' +
            ' ' * padding_left +
            ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{tmpdir}" + ' ' +  # Inner space around text
            ' ' * padding_right +
            f'#'
        )
    ### CACHE DIR ###
    if cachedir is not None:
        subtitle = f"Cache Directory: "
        if len(cachedir) + len(subtitle) > max_text_len:
            # Truncate the text if necessary
            cachedir = cachedir[:max_text_len - len(subtitle) - 5] + "..."
        cachedir_len = len(subtitle) + len(cachedir) +2
        
        remaining_space = inner_width - cachedir_len
        padding_left = 2
        padding_right = remaining_space - padding_left
        cachedir_line = (
            f'#' +
            ' ' * padding_left +
            ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{cachedir}" + ' ' +  # Inner space around text
            ' ' * padding_right +
            f'#'
        )
    
    ### FORCE ###
    subtitle = f"Force: "
    force = str(force)
    if len(force) + len(subtitle) > max_text_len:
        # Truncate the text if necessary
        force = force[:max_text_len - len(subtitle) - 5] + "..."
    force_len = len(subtitle) + len(force) +2
    
    remaining_space = inner_width - force_len
    padding_left = 2
    padding_right = remaining_space - padding_left
    force_line = (
        f'#' +
        ' ' * padding_left +
        ' ' + f"{BOLD}{GREEN}{subtitle}{RESET}{force}" + ' ' +  # Inner space around text
        ' ' * padding_right +
        f'#'
    )
    
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
    print(subject_line)
    print(blank_padding)
    print(session_line)
    print(blank_padding)
    print(bids_dir_line)
    print(blank_padding)
    print(subj_dir_line)
    print(blank_padding)
    print(psf_line)
    print(blank_padding)
    print(ref_region_line)
    print(blank_padding)
    print(seg_type_line)
    print(blank_padding)
    if fastsurfer_img is not None:
        print(fastsurfer_img_line)
        print(blank_padding)
    if hippunfold_img is not None:
        print(hippunfold_img_line)
        print(blank_padding)
    if hippunfold_dir is not None:
        print(hippunfold_dir_line)
        print(blank_padding)
    if tmpdir is not None:
        print(tmpdir_line)
        print(blank_padding)
    if cachedir is not None:
        print(cachedir_line)
        print(blank_padding)
    print(force_line)
    print(blank_padding)
    print(border)
    print("\n"*2)

def main():
    ## test
    # display_splash_screen()
    print_centered_box()
    
    # # Set the working directory to the script's location
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # repo_dir = os.path.dirname(script_dir)

    # # Argument Parsing
    # parser = argparse.ArgumentParser(add_help=True)
    # parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
    # parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
    # parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
    # parser.add_argument("-subj_dir", dest="subj_dir", type=str, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
    # parser.add_argument("-seg_type", dest="seg_type", type=str, help="'freesurfer' or 'fastsurfer'. Default: 'fastsurfer'.", choices=['freesurfer','fastsurfer'], default="fastsurfer")

    # parser.add_argument("-fastsurfer_img", dest="fastsurfer_img", type=str, help="(Str) Specify path to FastSurfer singularity image.")
    # parser.add_argument("-fs_license", dest="fs_license", type=str, help="(Str) Specify path to FreeSurfer license.")
    
    # parser.add_argument("-hippunfold_img", dest="hippunfold_img", type=str, help="(Str) Specify path to HippUnfold singularity image.")
    # parser.add_argument("-tmpdir", dest="tmpdir", type=str, help="(Str) Specify path to temporary directory.")
    # parser.add_argument("-cachedir", dest="cachedir", type=str, help="(Str) Set HIPPUNFOLD_CACHE_DIR manually. (Default ~/.cache).")
    # parser.add_argument("-hippunfold_dir", dest="hippunfold_dir", type=str, help="(Str) Specify path to HippUnfold output directory.")

    # parser.add_argument("-psf", dest="psf", type=float, required=True, help="Scanner PSF in mm. Ask your PET physicist if unknown.", default=4.5)
    # parser.add_argument("-ref_region",dest="ref_region", type=str, action='store', default='pons',help="Specify reference region. eg: pons/cerebellarGM/composite. Default: pons.")

    # parser.add_argument("-B", dest="B",type=str, help="(Str) Specify paths to bind for Singularity. (eg. /host or /host,/opt etc)")
    # parser.add_argument("-T1", dest="T1_path", type=str, help="(Str) Specify path to T1w image. (Default T1w image in BIDS directory).")    
    # parser.add_argument("-pet", dest="pet_path", type=str, help="(Str) Specify path to PET image. (Default PET image in BIDS directory).")

    # parser.add_argument("-force", dest="force", action='store_true', help="Force HippUnfold even if output exists.")
    
    # parser.add_argument("-fastsurfer", dest="fastsurfer_run", action='store_true', help="Run FastSurfer for cortical surface generation.")
    # parser.add_argument("-hippunfold", dest="hippunfold_run", action='store_true', help="Run HippUnfold for hippocampal surface generation.")
    # parser.add_argument("-coreg", dest="coreg_run", action='store_true', help="Run PET to T1 coregistration.")
    # parser.add_argument("-pvc", dest="pvc_run", action='store_true', help="Run Partial Volume Correction.")
    # parser.add_argument("-suvr", dest="suvr_run", action='store_true', help="Run SUVR calculation.")
    # parser.add_argument("-cortical_surface", dest="cortical_surface_run", action='store_true', help="Create cortical surface.")
    # parser.add_argument("-project_pet", dest="project_pet_run", action='store_true', help="Project PET data onto surfaces.")
    # parser.add_argument("-clinical_report", dest="clinical_report_run", action='store_true', help="Generate clinical report.")

    # args = parser.parse_args()

    # # Validate mandatory arguments
    # if not all([args.sub, args.ses, args.bids_dir, args.psf]):
    #     print("Error: One or more mandatory arguments are missing.")
    #     parser.print_help()
    #     sys.exit(1)
        
    # # Run all steps if none of the specific steps are selected
    # if not any([args.fastsurfer_run, args.hippunfold_run, args.coreg_run, args.pvc_run, args.suvr_run, args.cortical_surface_run, args.project_pet_run, args.clinical_report_run]):
    #     run_all = True
    # else:
    #     run_all = False
        
    # # Normalize paths and variables
    # session = f"{args.ses.replace('ses-', '')}"
    # subject = f"{args.sub.replace('sub-', '')}"
    # bids_dir = os.path.realpath(args.bids_dir)
    # if args.subj_dir is None: #check if user inputted subj_dir
    #     subj_dir = f"{bids_dir}/derivatives/fastsurfer"
    #     print(f"FreeSurfer/FastSurfer directory not provided. Using default: {subj_dir}")
    #     if not os.path.exists(subj_dir):
    #         print("FastSurfer directory does not exist. Creating it now.")
    #         os.makedirs(subj_dir, exist_ok=True)
    # else:
    #     subj_dir = os.path.realpath(args.subj_dir)
    #     if not os.path.exists(subj_dir):
    #         print("ERROR: FreeSurfer/FastSurfer directory does not exist. Please enter a valid -subj_dir.")
    #         sys.exit(1)

    # seg_type = args.seg_type.lower()
    # ref_region = args.ref_region

    # # Validate FastSurfer arguments if running FastSurfer
    # fastsurfer_img = os.path.realpath(args.fastsurfer_img) if args.fastsurfer_img else None
    # fs_license = os.path.realpath(args.fs_license) if args.fs_license else None
    # if (run_all==True or args.fastsurfer_run==True) and fastsurfer_img is None and fs_license is not None:
    #     print("Error: FastSurfer image not provided or not valid. Please provide the path using -fastsurfer_img argument.")
    #     sys.exit(1)
    # elif (run_all==True or args.fastsurfer_run==True) and fastsurfer_img is not None and fs_license is None:
    #     print("Error: FreeSurfer license not provided or not valid. Please provide the path using -fs_license argument.")
    #     sys.exit(1)
    # elif (run_all==True or args.fastsurfer_run==True) and fastsurfer_img is None and fs_license is None:
    #     print("Error: FastSurfer image and FreeSurfer license not provided or not valid. Please provide the paths using -fastsurfer_img and -fs_license arguments.")
    #     sys.exit(1)
    # if (run_all==True or args.fastsurfer_run==True) and fastsurfer_img is not None and fs_license is not None:
    #     fastsurfer_run = True
    # else:
    #     fastsurfer_run = False
        
    # # Validate HippUnfold arguments if running HippUnfold    
    # hippunfold_img = os.path.realpath(args.hippunfold_img) if args.hippunfold_img else None
    # if (run_all==True or args.hippunfold_run==True) and hippunfold_img is None:
    #     print("Error: HippUnfold image not provided or not valid. Please provide the path using -hippunfold_img argument.")
    #     sys.exit(1)
    # elif (run_all==True or args.hippunfold_run==True) and hippunfold_img is not None:
    #     hippunfold_run = True
        
    # if args.hippunfold_dir is None: #check if user inputted hippunfold_dir
    #     hippunfold_dir = f"{bids_dir}/derivatives/hippunfold_v1.4.1"
    #     os.makedirs(hippunfold_dir,exist_ok=True) #makes hippunfold_dir if it doesn't already exist
    # else:
    #     hippunfold_dir = os.path.realpath(args.hippunfold_dir)
    # if not os.path.exists(hippunfold_dir):
    #     print("ERROR: HippUnfold directory does not exist. Please enter a valid -hippunfold_dir.")
    #     sys.exit(1)
        
    # if args.tmpdir is None:
    #     os.makedirs(f"{bids_dir}/derivatives/tmp", exist_ok=True)
    #     tmpdir_flag = [ "-tmpdir", f"{bids_dir}/derivatives/tmp"]
    # else:
    #     tmpdir_flag = [ "-tmpdir", f"{os.path.realpath(args.tmpdir)}"]  

    # if args.cachedir is None:
    #     cachedir_flag = []
    # else:
    #     cachedir_flag = [ "-cachedir", f"{os.path.realpath(args.cachedir)}"]
    
    # if args.force: 
    #     force_flag = ["-force"]
    # else:
    #     force_flag = []
        
    # if args.B is not None:
    #     bind_flag = ["-B", f"{args.B}"]
    # else:
    #     bind_flag = []


    # # create rawdata and derivatives directories if they don't exist
    # os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat", exist_ok=True)
    # os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet", exist_ok=True)
    # os.makedirs(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/anat", exist_ok=True)
    # os.makedirs(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/pet", exist_ok=True)
    # os.makedirs(f"{bids_dir}/derivatives/MICA-PET/sub-{subject}/ses-{session}/surf", exist_ok=True)
    # os.makedirs(f"{bids_dir}/derivatives/fastsurfer", exist_ok=True)
    # os.makedirs(f"{bids_dir}/derivatives/hippunfold_v1.4.1", exist_ok=True)
    
    
    # # if T1 image not provided, check if it exists in BIDS rawdata
    # if args.T1_path is None:
    #     if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"):
    #         print(f"Error: T1w image for subject {subject}, session {session} does not exist. Please specify with -T1 flag.")
    #         sys.exit(1)
    # elif not os.path.exists(os.path.realpath(args.T1_path)):
    #     print(f"Error: Specified T1w image {args.T1_path} does not exist.")
    #     sys.exit(1)
    # else: #copy T1 to BIDS rawdata if not already there
    #     if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"):
    #         shutil.copyfile(os.path.realpath(args.T1_path), f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz")
            
    # # if PET image not provided, check if it exists in BIDS rawdata
    # if args.pet_path is None:
    #     if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet.nii.gz"):
    #         print(f"Error: PET image for subject {subject}, session {session} does not exist. Please specify with -pet flag.")
    #         sys.exit(1)
    # elif not os.path.exists(os.path.realpath(args.pet_path)):
    #     print(f"Error: Specified PET image {args.pet_path} does not exist.")
    #     sys.exit(1)
    # elif not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet.nii.gz"): #copy PET to BIDS rawdata if not already there
    #         shutil.copyfile(os.path.realpath(args.pet_path), f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet.nii.gz")
            
            
    # display_splash_screen()
    
    # #### Run components of the pipeline ####
        
    # # Run FastSurfer if specified
    # if fastsurfer_run:
    #     print("Running FastSurfer...")
    #     cmd = [f'{script_dir}/fastsurfer.py',"-sub",f'{subject}',"-ses",f'{session}',"-bids",f'{bids_dir}',"-subj_dir",f'{subj_dir}',"-fastsurfer_img",f'{fastsurfer_img}',"-fs_license",f'{fs_license}'] + tmpdir_flag + force_flag #sys.executable, 
    #     subprocess.call(cmd)
    
    # # Run HippUnfold if specified
    # if hippunfold_run:
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
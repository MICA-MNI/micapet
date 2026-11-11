#!/usr/bin/env python3

import argparse
import glob
import os
from re import sub
import sys
from datetime import datetime
import shutil
import numpy as np
import nibabel as nib
from typing import Union, List
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

AFNI_dir = os.path.join(script_dir, "resources","AFNI")
if AFNI_dir not in sys.path:
    sys.path.insert(0, AFNI_dir)

import utils
import warnings 
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
warnings.filterwarnings("ignore", category=UserWarning, module="stopit")

repo_dir = os.path.dirname(script_dir)

def dicom_convert(
    subject: str,
    session: str,
    bids_dir: str,
    dicom_dir: str,
    trc: str,
    image_type: str = "pet",
    series: int = 12
):
    """
    This script is part of MICA-PET pipeline for converting DICOM to NIfTI format.

    The script requires the following arguments:
        -subject        : Subject identification. (eg. PX001)
        -session        : Session. (eg. 01)
        -bids_dir       : Path to BIDS directory ( . or FULL PATH)
        -dicom_dir      : Path to DICOM directory.
        -trc            : Tracer used (eg. FDG)
        -image_type     : Type of image ("pet" or "mri", default "pet")
        -series         : Series number (default 12)
    """
    import dcm2niixpy

    # Check if DICOM directory exists
    if not os.path.exists(dicom_dir):
        print(f"Error: DICOM directory not found at {dicom_dir}")
        sys.exit(1)

    if image_type == "mri":
        image_type = "anat"

    utils.print_time_stamp(f"Starting FastSurfer for subject: {subject}, session: {session}.")

    # Create BIDS directory structure if it doesn't exist
    if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
        os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}")
        os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat")
        os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet")

    # DICOM to NIfTI conversion using dcm2niixpy
    dcm2niix = dcm2niixpy.DCM2NIIX(version="1.0.20241211")
    dcm2niix.bids_sidecar = 'y'
    dcm2niix.anonymize_bids_sidecar = 'y'
    dcm2niix.compress = 'y'
    dcm2niix.convert_only_this_crc = str(series)
    dcm2niix.conflict_write_behavior = 2

    if image_type == "pet":
        dcm2niix.filename = f"sub-{subject}_ses-{session}_trc-{trc}_pet"
    elif image_type == "anat":
        dcm2niix.filename = f"sub-{subject}_ses-{session}_T1w"

    dcm2niix.convert(dicom_dir,output_path=f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/{image_type}")

    utils.print_time_stamp("DICOM to NIfTI conversion completed.")


def fastsurfer(
    subject: str,
    session: str,
    bids_dir: str,
    subj_dir: str,
    fastsurfer_img: str,
    fs_license: str,
    threads: int = 15,
    force: bool = False,
    tmpdir: str = None
):
    """
    This script is part of MICA-PET pipeline for cortical surface generation with FastSurfer.

    The script requires the following arguments:
        -subject        : Subject identification. (eg. PX001)
        -session        : Session. (eg. 01)
        -bids_dir       : Path to BIDS directory ( . or FULL PATH)
        -subj_dir : Specify path to FastSurfer subjects directory. (Default fastsurfer subdirectory in BIDS derivatives directory.)
        -fastsurfer_img : Path to FastSurfer .sif image.
        -fs_license : Path to FreeSurfer license. (eg. license.txt) 
        -threads        : Number of threads to use (default 15)
        -force      : (Optional) Force FastSurfer even if output exists.
        -tmpdir     : Path to temporary directory.
    """
    from spython.main import Client
    from utils import bcolors
    from pathlib import Path
    import subprocess

    utils.print_time_stamp(f"Starting FastSurfer for subject: {subject}, session: {session}.")

    # Check if FastSurfer image exists
    if os.path.exists(fastsurfer_img):
            print(f"Using FastSurfer image at {fastsurfer_img}")
    else:
        print(f"Error: FastSurfer image not found at {fastsurfer_img}")
        sys.exit(1)

    def copy_FSfiles_to_tmp(subj_dir, subject, session, bids_dir):
        # copy to tmp to avoid deletion of original files if snakemake fails on fastsurfer rule
        derivatives_tmp_dir = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}/sub-{subject}/ses-{session}/tmp"
        os.makedirs(derivatives_tmp_dir, exist_ok=True)

        for file in [
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/surf/lh.pial"),
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/surf/rh.pial"),
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/surf/lh.white"),
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/surf/rh.white"),
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/surf/lh.sphere.reg"),
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/surf/rh.sphere.reg"),
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/mri/transforms/talairach.lta"),
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/mri/brainmask.mgz"),
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/mri/norm.mgz"),
            Path(f"{subj_dir}/sub-{subject}_ses-{session}/mri/aparc+aseg.mgz")
        ]:
            if os.path.exists(file):
                print(f"Copying {file} to derivatives tmp directory")
                shutil.copy(file, f"{derivatives_tmp_dir}/")

    # Check if FastSurfer output already exists
    if os.path.exists(f"{subj_dir}/sub-{subject}_ses-{session}/mri/orig.mgz") and force==False:
        utils.print_time_stamp("FastSurfer already run. Please rerun with -force flag to overwrite.","red")
        

        copy_FSfiles_to_tmp(subj_dir, subject, session, bids_dir)
        
        return
    elif os.path.exists(f"{subj_dir}/sub-{subject}_ses-{session}") and force==True:
        shutil.rmtree(f"{subj_dir}/sub-{subject}_ses-{session}", ignore_errors=True)

    # Check if T1w image exists
    T1_path = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
    if not os.path.exists(T1_path):
        print(f"Error: T1w image not found at {T1_path}")
        sys.exit(1)

    # Check if fastsurfer output directory exists, if not create it
    if not os.path.exists(subj_dir):
        os.makedirs(subj_dir, exist_ok=True)

    command = [
        "/fastsurfer/run_fastsurfer.sh",
        "--fs_license", "/output/license.txt",
        "--t1", "/mnt/T1.nii.gz",
        "--sid", f"sub-{subject}_ses-{session}",
        "--sd", "/output",
        "--no_fs_T1",
        "--parallel",
        "--no_hypothal",
        "--no_cereb",
        "--threads", str(threads)
    ]
    options=[
        "--cleanenv",
        "--writable-tmpfs",
        "--containall",
        "--no-home",
        "-B", f"{subj_dir}:/output",
        "-B", f"{tmpdir}:/tmpdir",
        "-B", f"{T1_path}:/mnt/T1.nii.gz",
        "-B", f"{fs_license}:/output/license.txt"
    ]

    # Run using spython
    print(f"Executing command in Singularity: \n{bcolors.BLUE}singularity exec {' '.join(options)} {fastsurfer_img} {' '.join(command)}{bcolors.RESET}")

    if shutil.which('singularity') is None:
        print("Error: 'singularity' executable not found in PATH. Please ensure Singularity is installed.")
        sys.exit(1)

    try:
        subprocess.run(
            ["singularity", "exec"] + options + [fastsurfer_img] + command,
            check=True
        )

        copy_FSfiles_to_tmp(subj_dir, subject, session, bids_dir)

    except subprocess.CalledProcessError as e:
        print(f"An error occurred during Singularity execution: {e}")
        sys.exit(1)

    utils.print_time_stamp("FastSurfer completed.","green")

def hippunfold(
        subject: str,
        session: str,
        bids_dir: str,
        hippunfold_img: str,
        hippunfold_dir: str = None,
        tmpdir: str = None,
        cachedir: str = None,
        B: list = None,
        T1_path: str = None,
        force: bool = False,
        threads: int = 8
):
    """
    This script is part of MICA-PET pipeline for hippocampal surface generation with HippUnfold.

    The script requires the following arguments:
        -subject        : Subject identification. (eg. PX001)
        -session        : Session. (eg. 01)
        -bids_dir       : Path to BIDS directory ( . or FULL PATH)
        -hippunfold_img : Path to HippUnfold .sif image.
        -hippunfold_dir : Specify path to HippUnfold output directory. (Default: hippunfold subdirectory in BIDS derivatives directory.)
        -tmpdir         : (Optional) Path to temporary directory. (Default /tmp)
        -cachedir       : (Optional) Set HIPPUNFOLD_CACHE_DIR manually. (Default ~/.cache)
        -B              : (Optional) Bind pathway for Singularity (eg. /host or /host,/opt etc)
        -T1_path        : (Optional) Path to T1w image. (Default T1w image in BIDS directory).
        -force          : (Optional) Force HippUnfold even if output exists.
    """
    from spython.main import Client
    from pathlib import Path
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"

    # Check tmpdir
    if tmpdir is None:
        tmpdir = []
    else:
        os.environ['TMPDIR'] = tmpdir
        tmpdir = ["--env",f"TMPDIR={os.path.realpath(tmpdir)}","-B",os.path.realpath(tmpdir)]

    # Check cachedir
    if cachedir is None:
        cachedir = []
    else:
        cachedir = ["--env",f"HIPPUNFOLD_CACHE_DIR={os.path.realpath(cachedir)}","-B",os.path.realpath(cachedir)]
        os.environ['HIPPUNFOLD_CACHE_DIR'] = cachedir

    # Check bind paths
    if B is None:
        bind = []
    else:
        bind = ["-B",f"{os.path.realpath(B)}"]

    # Check if HippUnfold image exists
    if not os.path.exists(hippunfold_img):
        print(f"Error: HippUnfold image not found at {hippunfold_img}")
        sys.exit(1)

    # Check if HippUnfold directory exists
    if hippunfold_dir is None: #check if user inputted hippunfold_dir
        hippunfold_dir = f"{bids_dir}/derivatives/hippunfold_v1.4.1"
        os.makedirs(hippunfold_dir,exist_ok=True) #makes hippunfold_dir if it doesn't already exist
    elif not os.path.exists(hippunfold_dir):
        print(f"Error: HippUnfold directory not found at {hippunfold_dir}")
        sys.exit(1)
    else:
        hippunfold_dir = os.path.realpath(hippunfold_dir)

    # Create BIDS directory structure
    utils.make_bids_dir(mica_pet_derivatives, subject, session)

    def copy_hippunfold_files_to_tmp(hippunfold_dir, subject, session, bids_dir):
            # copy to tmp to avoid deletion of original files if snakemake fails on hippunfold rule
            derivatives_tmp_dir = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}/sub-{subject}/ses-{session}/tmp"
            os.makedirs(derivatives_tmp_dir, exist_ok=True)
            derivatives_surf_dir = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}/sub-{subject}/ses-{session}/surf"

            for file in [
                Path(os.path.join(hippunfold_dir, "hippunfold", f"sub-{subject}", f"ses-{session}", "surf", f"sub-{subject}_ses-{session}_hemi-L_space-T1w_den-2mm_label-hipp_midthickness.surf.gii")),
                Path(os.path.join(hippunfold_dir, "hippunfold", f"sub-{subject}", f"ses-{session}", "surf", f"sub-{subject}_ses-{session}_hemi-R_space-T1w_den-2mm_label-hipp_midthickness.surf.gii")),
            ]:
                if os.path.exists(file):
                    print(f"Copying {file} to derivatives tmp directory")
                    shutil.copy(file, f"{derivatives_tmp_dir}/") 
                    shutil.copy(file, f"{derivatives_surf_dir}/") 

    # Check if HippUnfold output already exists
    if os.path.exists(os.path.join(hippunfold_dir, "hippunfold", f"sub-{subject}", f"ses-{session}", "surf", f"sub-{subject}_ses-{session}_hemi-L_space-T1w_den-2mm_label-hipp_midthickness.surf.gii")) and force==False:
        utils.print_time_stamp("HippUnfold already run. Please rerun with -force flag to overwrite.","red")

        copy_hippunfold_files_to_tmp(hippunfold_dir, subject, session, bids_dir)

        return

               

    # Check T1 path
    if T1_path is None: #check if user inputted T1_path 
        if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"): # if not T1_path inputted, does T1w image exist already in BIDS?
            print(f"Error: T1w image for subject {subject}, session {session} does not exist. Please specify T1_path argument and replace subject name with "+"{subject}.")
            sys.exit(1)
        else: 
            T1_path = []
    else: 
        T1_path = ["--path-T1w", f"{os.path.realpath(args.T1_path)}"]

    # Check force argument
    if force==True: # Always pass --force-output when -force flag is set
        force_command=["--force-output", "--rerun-incomplete"] # ensure Snakemake reruns incomplete files
    else:
        force_command=[]

    utils.print_time_stamp(f"Starting HippUnfold for subject: {subject}, session: {session}.")

    args = [
        "/bids_dir",
        "/output_dir",
        "participant",
        "--participant-label",f"{subject}",
        "--modality", "T1w",
        "--filter-T1w", f"session={session}",
        "--output-density","2mm",
        "--cores", str(threads),
        "--force-output", "--rerun-incomplete"
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

    copy_hippunfold_files_to_tmp(hippunfold_dir, subject, session, bids_dir)

    utils.print_time_stamp(f"HippUnfold completed for subject: {subject}, session: {session}.","green")

def cortical_surface(
        subject: str,
        session: str,
        bids_dir: str,
        subj_dir: str
):
    """
    This script is part of MICA-PET pipeline for mapping FreeSurfer/FastSurfer cortical surfaces to HCP.
    FreeSurfer/FastSurfer must have been run first.

    The script requires the following arguments:
        -subject        : Subject identification. (eg. PX001)
        -session        : Session. (eg. 01)
        -bids_dir       : Path to BIDS directory ( . or FULL PATH)
        -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
    """
    from nipype.interfaces.freesurfer import FSCommand, MRIsConvert
    from nipype.interfaces.workbench.base import WBCommand

    f_surf_dir = f"{os.path.realpath(subj_dir)}/sub-{subject}_ses-{session}"
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"
    FSCommand.set_default_subjects_dir(subj_dir)

    # Check if surface files exists
    file_patterns = ["lh.pial", "lh.white", "lh.sphere.reg","rh.pial", "rh.white", "rh.sphere.reg"]
    missing_files = [pattern for pattern in file_patterns if not os.path.exists(f"{f_surf_dir}/surf/{pattern}")]
    if missing_files:
        print(f"Error: missing surface files for subject {subject}, session {session}. Please ensure FreeSurfer/FastSurfer have been run properly.")
        sys.exit(1)

    utils.print_time_stamp(f"Starting FreeSurfer/FastSurfer mapping to fsLR for subject: {subject}, session: {session}.")

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

    utils.print_time_stamp(f"Cortical surface generation completed for subject: {subject}, session: {session}.","green")

def linear_coreg(
    subject: str,
    session: str,
    trc: str,
    bids_dir: str,
    subj_dir: str,
    edge_reg: bool = False,
    pet: str = None,
    mri: str = None
):
    """
    This script is part of MICA-PET pipeline for linear co-registration of PET to MRI using FreeSurfer mri_coreg or edge-based registration.

    The script requires the following arguments:
        -subject        : Subject identification. (eg. PX001)
        -session        : Session. (eg. 01)
        -trc            : Tracer (eg. FDG, MK6240)
        -bids_dir       : Path to BIDS directory ( . or FULL PATH)
        -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
        -edge_reg       : Uses edge-based registration method for PET to T1w registration rather than FreeSurfer mri_coreg.
        -pet            : (Optional) Specify path to PET nifti file. Default: sub-<sub>_ses-<ses>_trc-<trc>_pet.nii.gz in pet BIDS directory.
        -mri            : (Optional) Specify path to MRI nifti file. Default: sub-<sub>_ses-<ses>_T1w.nii.gz in anat BIDS directory.
    """
    from nipype.interfaces.freesurfer import MRICoreg, ApplyVolTransform, FSCommand, MRIConvert, FSCommand
    from nipype.interfaces.freesurfer.utils import LTAConvert

    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"
    FSCommand.set_default_subjects_dir(subj_dir)

    # Check if PET/MRI exists
    if pet is None:
        pet = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_pet.nii.gz"
    if not os.path.exists(pet):
        print(f"Error: PET image {pet} does not exist. Please specify pet argument.")
        sys.exit(1)

    if mri is None: 
        mri = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
        if not os.path.exists(mri):
            print(f"Error: MRI image for subject {subject}, session {session} does not exist. Please specify mri argument.")
            sys.exit(1)
    if not os.path.exists(mri):
        print(f"Error: MRI image {mri} does not exist. Please specify mri argument.")
        sys.exit(1)

    # Check if transmission PET scan exists
    transmission_list = sorted(glob.glob(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_*transmission*.nii.gz"))
    if len(transmission_list) > 1:
        print(f"Warning: Multiple transmission scans found for subject {subject}, session {session}. Using the first one found: {transmission_list[0]}")
    transmission = transmission_list[0] if len(transmission_list) > 0 else None
    
    # Create BIDS directory structure
    utils.make_bids_dir(mica_pet_derivatives, subject, session)

    utils.print_time_stamp(f"Starting PET to MRI co-registration for subject: {subject}, session: {session}.")

    # 3d resample MRI to nativepro space
    # remove nativepro MRI if present
    nativepro_mri = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
    if os.path.exists(nativepro_mri):
        print(f"Removing existing nativepro MRI: {nativepro_mri}")
        os.remove(nativepro_mri)

    input_mri = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-FS_T1w.nii.gz"
    if not os.path.exists(input_mri):
        # Convert FreeSurfer mgz to nifti if not already done
        mc = MRIConvert()
        mc.inputs.in_file = f"{subj_dir}/sub-{subject}_ses-{session}/mri/orig.mgz"
        mc.inputs.out_file = input_mri
        mc.inputs.out_type = 'niigz'
        mc.run()
    
    utils.resample_to_nativepro(
        input=input_mri, 
        output=nativepro_mri,
        reference=None,
        interp='trilin'
    )

    ## MRICoreg
    def mricoreg(transmission,pet,subject,session,subj_dir,mica_pet_derivatives,space,trc):
        print(f"Co-registering PET to {space}...")
        coreg = MRICoreg()
        if transmission is not None: # check if transmission scan exists and use it for co-registration if it does
            print(f"Using transmission scan for co-registration to space {space}...")
            coreg.inputs.source_file=transmission
        else:
            coreg.inputs.source_file=pet

        if space == 'T1wFS': # use FreeSurfer mgz as reference
            coreg.inputs.subjects_dir=subj_dir
            coreg.inputs.subject_id=f"sub-{subject}_ses-{session}"
        else: # use rawdata mri
            coreg.inputs.reference_file=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
        coreg.inputs.out_lta_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-{space}_xfm.reg.lta'
        print(coreg.cmdline)
        coreg.run()
        
        applyreg = ApplyVolTransform()
        applyreg.inputs.source_file=pet
        applyreg.inputs.reg_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-{space}_xfm.reg.lta'
        if space == 'T1wFS':
            applyreg.inputs.fs_target=True
        else:
            applyreg.inputs.target_file=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
        applyreg.inputs.transformed_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-none_trc-{trc}_pet.nii.gz'
        applyreg.run()

    # edgereg
    def pet_to_t1w_edge_registration(
        pet_path: str,
        subject: str,
        session: str,
        subj_dir: str,
        mica_pet_derivatives: str,
        space: str,
        trc: str,
        smooth_sigma_mm: float = 1.0,
        interpolator: str = "nearestNeighbor",
    ) -> nib.Nifti1Image:
        """
        Register PET to T1w using edge-based affine registration.
    
        Mirrors: antsRegistrationSyN.sh -d 3 -t a -j 1 on smoothed edge images,
        then antsApplyTransforms -n NearestNeighbor on the original PET.
    
        Parameters
        ----------
        pet_path        : path to PET NIfTI (average or single frame)
        t1w_path        : path to T1w NIfTI (registration target)
        output_prefix   : ANTs output prefix; affine .mat saved here
        smooth_sigma_mm : Gaussian sigma in mm (default 1.0 → fslmaths -s 1)
        interpolator    : interpolation for final warp (default "nearestNeighbor". Also supports "linear")
    
        Returns
        -------
        nib.Nifti1Image  PET resampled into T1w space
        """
        import ants
        import subprocess
        from pathlib import Path

        # Absolute path to the directory above the current script
        parent_dir = Path(__file__).resolve().parents[1]
        resources_path = f"{parent_dir}/resources"
    
        # ------------------------------------------------------------------
        # Step 0 – load

        utils.print_time_stamp(f"Starting edge-based registration of PET to T1w for subject: {subject}, session: {session}.")
        utils.print_time_stamp(f"PET path: {pet_path}")
        
        if space == 'T1wNativepro':
            t1w_path = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
            
        elif space == 'T1wFS':
            t1w_path = f"{subj_dir}/sub-{subject}_ses-{session}/mri/orig.nii.gz"
            if not os.path.exists(t1w_path):
                # Convert FreeSurfer mgz to nifti if not already done
                mc = MRIConvert()
                mc.inputs.in_file = f"{subj_dir}/sub-{subject}_ses-{session}/mri/orig.mgz"
                mc.inputs.out_file = t1w_path
                mc.inputs.out_type = 'niigz'
                mc.run()
        utils.print_time_stamp(f"T1w path: {t1w_path}")

        t1w_nib = nib.load(t1w_path)          # kept only for output header/affine
        pet_nib = nib.load(pet_path)          # kept only for output header/affine
        pet = ants.image_read(pet_path)
        t1w = ants.image_read(t1w_path)
        output_prefix = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-{space}_"
    
        # ------------------------------------------------------------------
        # Step 1 – smooth  (fslmaths -s sigma)
        utils.print_time_stamp(f"Smoothing PET and T1w images with sigma={smooth_sigma_mm} mm.")
        pet_smooth = ants.smooth_image(pet, smooth_sigma_mm, sigma_in_physical_coordinates=True)
        t1w_smooth = ants.smooth_image(t1w, smooth_sigma_mm, sigma_in_physical_coordinates=True)
    
        # ------------------------------------------------------------------
        # Step 2 – edge filter  (fslmaths -edge → gradient magnitude)
        utils.print_time_stamp("Computing edge images for PET and T1w.")
        def _edge(img):
            d, sp = img.numpy().astype(np.float64), np.array(img.spacing)
            g = [np.gradient(d, sp[i], axis=i) for i in range(3)]
            return img.new_image_like(np.sqrt(sum(gi**2 for gi in g)))
    
        pet_edge = _edge(pet_smooth)
        t1w_edge = _edge(t1w_smooth)

        # def _smooth_and_edge(img_path):
        #     basename = Path(os.path.basename(img_path)).name.split(".nii.gz")[0]
        #     smooth_img = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/tmp/{basename}_smooth.nii.gz"
        #     cmd = [f"{resources_path}/FSL/fslmaths",
        #            f"{img_path}",
        #            "-s", "1",
        #            f"{smooth_img}"
        #     ]

        #     subprocess.run(cmd)

        #     edge_img = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/tmp/{basename}_edge.nii.gz"
        #     cmd = [f"{resources_path}/FSL/fslmaths",
        #            f"{smooth_img}",
        #            "-edge",
        #            f"{edge_img}"
        #     ]

        #     subprocess.run(cmd)

        #     return ants.image_read(edge_img)

        # t1w_edge = _smooth_and_edge(t1w_path)
        # pet_edge = _smooth_and_edge(pet_path)
    
        # ------------------------------------------------------------------
        # Step 3 – affine registration on edge images
        # use_legacy_histogram_matching=True mirrors -j 1 in antsRegistrationSyN.sh
        utils.print_time_stamp("Performing affine registration on edge images using ANTS.")
        reg = ants.registration(
            fixed             = t1w_edge,
            moving            = pet_edge,
            type_of_transform = "antsRegistrationSyN[a]",
            outprefix         = output_prefix,
            use_legacy_histogram_matching = True,
        )
    
        # ------------------------------------------------------------------
        # Step 4 – apply transform to original (unmodified) PET
        utils.print_time_stamp(f"Applying affine transform to original PET image {pet_path}.")
        pet_warped = ants.apply_transforms(
            fixed         = t1w,
            moving        = pet,
            transformlist = reg["fwdtransforms"],
            interpolator  = interpolator,
        )
        
        # ------------------------------------------------------------------
        # Step 5 – convert .mat to .lta for FreeSurfer compatibility
        # Convert ANTs affine matrix to FreeSurfer LTA format
        utils.print_time_stamp("Converting ANTs affine matrix to FreeSurfer LTA format.")
        tx = ants.read_transform(f"{output_prefix}0GenericAffine.mat")

        ants.write_transform(tx, f"{output_prefix}0GenericAffine.txt")

        lta_convert = LTAConvert()
        lta_convert.inputs.in_itk = f"{output_prefix}0GenericAffine.txt"
        lta_convert.inputs.out_lta = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-{space}_xfm.reg.lta"
        lta_convert.inputs.source_file = pet_path
        lta_convert.inputs.target_file = t1w_path
        lta_convert.cmdline
        lta_convert.run()

        with open(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-{space}_xfm.reg.lta", "a") as file:
            file.write(f"subject sub-{subject}_ses-{session}\n")
        
        # ------------------------------------------------------------------
        # Step 6 – save resampled PET in T1w space
        
        out = nib.Nifti1Image(pet_warped.numpy(), t1w_nib.affine, t1w_nib.header)

        nib.save(out, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-none_trc-{trc}_pet.nii.gz")

        # -------------------------------------------------------------------
        # debug

        out_T1w_edge = nib.Nifti1Image(t1w_edge.numpy(), t1w_nib.affine, t1w_nib.header)
        nib.save(out_T1w_edge, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-T1wEdge.nii.gz")

        out_pet_edge = nib.Nifti1Image(pet_edge.numpy(), pet_nib.affine, pet_nib.header)
        nib.save(out_pet_edge, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-PETEdge.nii.gz")

    for space in ['T1wFS','T1wNativepro']:
        if edge_reg:
            pet_to_t1w_edge_registration(
                pet_path=pet,
                subject=subject,
                session=session,
                subj_dir=subj_dir,
                mica_pet_derivatives=mica_pet_derivatives,
                space=space,
                trc=trc,
                interpolator = "linear")
        else:
            mricoreg(transmission,
                    pet,
                    subject,
                    session,
                    subj_dir,
                    mica_pet_derivatives,
                    space,
                    trc)

    utils.print_time_stamp(f"PET to MRI co-registration completed for subject: {subject}, session: {session}.","green")

def nonlinear_coreg(
    subject: str,
    session: str,
    trc: str,
    bids_dir: str,
    pvc_method: str,
    ref_region: str
):
    """
    This script is part of MICA-PET pipeline for linear co-registration of PET to MRI.
    The script requires the following arguments:
        -subject        : Subject identification. (eg. PX001)
        -session        : Session. (eg. 01)
        -trc            : Tracer (eg. FDG, MK6240)
        -bids_dir       : Path to BIDS directory ( . or FULL PATH)
        -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
        -pvc_method     : PVC method used for PET image. Options: 'RBV-FS','MG-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'.
        -ref_region     : Reference regions to use. eg. 'pons','cerebellarGM','cerebellum','composite','WM','GM'.
    """
    from pathlib import Path
    import subprocess

    # Absolute path to the directory above the current script
    parent_dir = Path(__file__).resolve().parents[1]
    resources_path = f"{parent_dir}/resources"

    # Check if lamareg weights are present
    lamareg_weights_path = f"{resources_path}/lamareg"

    if not os.path.exists(lamareg_weights_path):
        print(f"Error: lamareg weights not found at {lamareg_weights_path}. Please ensure the lamareg weights are downloaded.")
        sys.exit(1)

    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"

    for pvc in ['none']:
        # register PET to MNI
        utils.print_time_stamp(f"Starting PET to MNI nonlinear co-registration for sub-{subject} ses-{session}...")
        cmd = ["lamareg",
            "register",
            "--moving",
            f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz",
            "--fixed",
            f"{resources_path}/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz",
            "--output",
            f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-MNI_T1w.nii.gz",
            "--fixed-parc",
            f"{resources_path}/mni_icbm152_t1_tal_nlin_sym_09a_parc.nii.gz",
            "--skip-fixed-parc",
            "--affine",
            f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wNativepro_to-MNI_lamaregAffine.mat",
            "--warpfield",
            f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wNativepro_to-MNI_lamaregWarp1.nii.gz",
            "--secondary-warpfield",
            f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wNativepro_to-MNI_lamaregWarp2.nii.gz",
            "--threads", "4"]
        
        subprocess.call(cmd)
        
    # apply existing transforms to other PET images
    for pvc in ['none',pvc_method]:
        for ref in ['none',ref_region]:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Applying PET to MNI nonlinear co-registration for sub-{subject} ses-{session} with PVC: {pvc} and reference region: {ref}...")
            cmd = ["lamareg",
                "apply-warpfield",
                "--moving",
                f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wNativepro_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.nii.gz",
                "--fixed",
                f"{resources_path}/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz",
                "--output",
                f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-MNI_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.nii.gz",
                "--affine",
                f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wNativepro_to-MNI_lamaregAffine.mat",
                "--warpfield",
                f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wNativepro_to-MNI_lamaregWarp1.nii.gz",
                "--secondary-warpfield",
                f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wNativepro_to-MNI_lamaregWarp2.nii.gz",
                "--threads", "4"]
            
            subprocess.call(cmd)        

    utils.print_time_stamp(f"PET to MNI nonlinear co-registration completed for subject: {subject}, session: {session}.","green")

def gtm_seg(
    subject: str,
    session: str,
    bids_dir: str,
    subj_dir: str,
    threads: int = 1,
    force: bool = False   
):
    """
    This script is part of MICA-PET pipeline for geometric transfer matrix segmentation.
    FreeSurfer or FastSurfer must have first been completed and segmentations verified.
    The script requires the following arguments:
        -subject        : Subject identification. (eg. PX001)
        -session        : Session. (eg. 01)
        -bids_dir       : Path to BIDS directory ( . or FULL PATH)
        -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
        -threads        : (Optional) Number of threads to use for FreeSurfer tools.
        -force          : (Optional) Force gtmseg even if output exists.
    """

    from nipype.interfaces.freesurfer import ApplyVolTransform, MRIConvert, GTMSeg, CARegister
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"
    f_surf_dir = f"{os.path.realpath(subj_dir)}/sub-{subject}_ses-{session}"

    # Determine segmentation type   
    if os.path.exists(f'{f_surf_dir}/scripts/deep-seg.log'): #deep-seg only exists in fastsurfer
        seg_type = 'fastsurfer'
    else:
        seg_type = 'freesurfer'

    # set SUBJECTS_DIR environment variable for FreeSurfer tools
    os.environ['SUBJECTS_DIR'] = os.path.realpath(subj_dir)
    # Set OpenMP threads for FreeSurfer tools
    os.environ['OMP_NUM_THREADS'] = str(threads)

    utils.print_time_stamp(f"Starting GTM segmentation for subject: {subject}, session: {session}.")

    # check seg type
    gtmseg = GTMSeg()
    if seg_type == 'freesurfer':
        # check if gtmseg was run already
        if os.path.exists(f"{f_surf_dir}/mri/gtmseg.mgz") and force==False:
            print(f"GTMseg was run already for subject {subject}. Re-run with -force flag to rerun GTMseg.")
            
        else:
            gtmseg.inputs.subject_id = f"sub-{subject}_ses-{session}"
            gtmseg.inputs.ctx_annot = ("aparc.DKTatlas.annot",1000,2000)
            if os.path.exists(f"{f_surf_dir}/mri/apas+head.mgz"):
                gtmseg.inputs.args = "--no-xcerseg"
            else:
                gtmseg.inputs.xcerseg = True
            # Try to set openmp if supported by nipype interface, or rely on OMP_NUM_THREADS
            try:
                gtmseg.inputs.openmp = threads
            except:
                pass
            print(gtmseg.cmdline)
            gtmseg.run()

    elif seg_type == 'fastsurfer':
        if os.path.exists(f"{f_surf_dir}/mri/gtmseg.mgz") and force==False: 
            print(f"GTMseg was run already for subject {subject}. Re-run with -force flag to rerun GTMseg.")
        else:
            # Create talairach.m3z if it doesn't exist
            if not os.path.exists(f"{f_surf_dir}/mri/transforms/talairach.m3z"):
                ca_register = CARegister()
                ca_register.inputs.in_file=f"{f_surf_dir}/mri/norm.mgz"
                ca_register.inputs.out_file=f"{f_surf_dir}/mri/transforms/talairach.m3z"
                ca_register.inputs.template=f"{os.environ.get('FREESURFER_HOME')}/average/RB_all_2016-05-10.vc700.gca"
                ca_register.inputs.transform=f"{f_surf_dir}/mri/transforms/talairach.lta"
                ca_register.inputs.mask=f"{f_surf_dir}/mri/brainmask.mgz"
                ca_register.inputs.no_big_ventricles=True
                ca_register.inputs.align='after'
                print(ca_register.cmdline)
                ca_register.run()

                gtmseg.inputs.subject_id = f"sub-{subject}_ses-{session}"
                gtmseg.inputs.ctx_annot = ("aparc.DKTatlas.annot",1000,2000)
                gtmseg.inputs.xcerseg = True
                # Try to set openmp if supported by nipype interface, or rely on OMP_NUM_THREADS
                try:
                    gtmseg.inputs.openmp = threads
                except:
                    pass
                print(gtmseg.cmdline)
                gtmseg.run()
            else:
                gtmseg.inputs.subject_id = f"sub-{subject}_ses-{session}"
                gtmseg.inputs.ctx_annot = ("aparc.DKTatlas.annot",1000,2000)
                if os.path.exists(f"{f_surf_dir}/mri/apas+head.mgz"):
                    gtmseg.inputs.args = "--no-xcerseg"
                else:
                    gtmseg.inputs.xcerseg = True
                # Try to set openmp if supported by nipype interface, or rely on OMP_NUM_THREADS
                try:
                    gtmseg.inputs.openmp = threads
                except:
                    pass
                    
                print(gtmseg.cmdline)
                gtmseg.run()

    # Resample GTMseg to T1w/nativepro space
    def resample_gtmseg(gtm,mri,space):
        print(f"Resampling GTMseg to {space} space...")
        applyreg = ApplyVolTransform()
        applyreg.inputs.source_file= gtm
        if space == 'T1wFS':
            applyreg.inputs.reg_header=True
            applyreg.inputs.interp = 'nearest'
            applyreg.inputs.target_file= mri
            applyreg.inputs.transformed_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-gtmseg.nii.gz'
            applyreg.run()

        elif space == 'T1wNativepro':
            utils.resample_to_nativepro(
                input=gtm,
                output=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-gtmseg.nii.gz',
                reference=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz",
                interp='nearest')
        
    gtm = f'{f_surf_dir}/mri/gtmseg.nii.gz'

    if not os.path.exists(gtm):
        mc = MRIConvert()
        mc.inputs.in_file = f'{f_surf_dir}/mri/gtmseg.mgz'
        mc.inputs.out_file = gtm
        mc.inputs.out_type = 'niigz'
        mc.run()

    for space in ['T1wFS','T1wNativepro']:
        if space == 'T1wFS':
            mri = f"{f_surf_dir}/mri/orig.mgz"
        else: 
            mri = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
        resample_gtmseg(gtm,mri,space)

    utils.print_time_stamp(f"GTM segmentation completed for subject: {subject}, session: {session}.","green")

def pvc(
    subject: str,
    session: str,
    trc: str,
    bids_dir: str,
    subj_dir: str,
    pvc_method: str,
    psf: float,
    pvc_dir: str = None,
    pvc_mask: str = None,
    pvc_n_iter: int = 10,
    pvc_n_deconv: int = 10,
    force: bool = False   
):
    """
    This script is part of MICA-PET pipeline for partial volume correction (PVC) using either PETSurfer or PETPVC.
    FreeSurfer/FastSurfer and gtmseg must have been run first.

    The script requires the following arguments:
        -subject        : Subject identification. (eg. PX001)
        -session        : Session. (eg. 01)
        -trc            : Tracer (eg. FDG, MK6240)
        -bids_dir       : Path to BIDS directory ( . or FULL PATH)
        -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
        -psf            : Scanner PSF FWHM in mm (eg. 4.5)
        -pvc_method     : PVC method used for PET image. Options: 'RBV-FS','MG-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'.
        -pvc_dir        : (Optional) Specify PVC output directory. (Default {subj_dir}/sub-{subject}_ses-{session}/gtmpvc.output).
        -force          : (Optional) Force PVC even if output exists.

    Specific for PETPVC: 
        -pvc_mask       : (Optional) Custom mask to use for PETPVC. Must be a 4D NIfTI with one ROI per frame. Sum across timeframes must be 1 at each voxel. Must be in FreeSurfer/FastSurfer space (eg. orig.mgz). If not provided, a two tissue mask will be generated for MG PVC and a GM+WM+CSF+background mask will be generated for all others.
        -pvc_n_iter     : (Optional) Number of iterations for iterative PVC methods (IY). Default: 10.
        -pvc_n_deconv   : (Optional) Number of iterations for deconvolution PVC methods (RL, VC). Default: 10.
    """
    from nipype.interfaces.freesurfer import FSCommand
    f_surf_dir = f"{os.path.realpath(subj_dir)}/sub-{subject}_ses-{session}"
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"
    FSCommand.set_default_subjects_dir(subj_dir)

    utils.print_time_stamp(f"Starting PVC for subject: {subject}, session: {session}, tracer: {trc}, method: {pvc_method}.")

    if pvc_method not in ['RBV-FS','MG-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL']:
        print(f"Error: PVC method {pvc_method} is not supported. Please choose from the following: RBV-FS, MG-FS, MG, IY, LABBE, RL, VC, RBV, LABBE+RBV, RBV+VC, RBV+RL, LABBE+RBV+VC, LABBE+RBV+RL, MTC, LABBE+MTC, MTC+VC, MTC+RL, LABBE+MTC+VC, LABBE+MTC+RL, IY+VC, IY+RL, MG+VC, MG+RL.")
        sys.exit(1)

    # FreeSurfer RBV or MG PVC  
    elif pvc_method == 'RBV-FS' or pvc_method == 'MG-FS':
            
        from nipype.interfaces import freesurfer
        from nipype.interfaces.freesurfer import ApplyVolTransform

        FSCommand.set_default_subjects_dir(subj_dir)

        # gtmpvc.output 
        if pvc_dir is None: 
            pvc_dir = f"{f_surf_dir}/gtmpvc.output"
        else: 
            pvc_dir= os.path.realpath(pvc_dir)

        # Check if gtmseg.mgz exists
        if not os.path.exists(f"{f_surf_dir}/mri/gtmseg.mgz"):
            print(f"Error: gtmseg.mgz for subject {subject}, session {session} does not exist. Please run gtm_seg.py first.")
            sys.exit(1)

        gtmpvc = freesurfer.GTMPVC()
        gtmpvc.inputs.in_file = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_pet.nii.gz"
        gtmpvc.inputs.reg_file = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-T1wFS_xfm.reg.lta'
        gtmpvc.inputs.psf = psf
        gtmpvc.inputs.segmentation = f"{f_surf_dir}/mri/gtmseg.mgz"
        gtmpvc.inputs.auto_mask = (1, 0.01)
        gtmpvc.inputs.mgx = 0.01
        gtmpvc.inputs.rbv = True
        gtmpvc.inputs.subjects_dir = f"{subj_dir}"
        gtmpvc.inputs.default_seg_merge = True
        gtmpvc.inputs.pvc_dir = pvc_dir
        print(gtmpvc.cmdline)

        gtmpvc.run()

        if pvc_method == 'RBV-FS':
            pvc_img = f"{pvc_dir}/rbv.nii.gz"
        elif pvc_method == 'MG-FS':
            pvc_img = f"{pvc_dir}/mgx.gm_reg2T1w.nii.gz"

            # resample mgx.gm to T1wFS space
            applyreg = ApplyVolTransform()
            applyreg.inputs.source_file= f"{pvc_dir}/mgx.gm.nii.gz"
            applyreg.inputs.lta_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-T1wFS_xfm.reg.lta'
            applyreg.inputs.target_file= f"{f_surf_dir}/mri/orig.mgz"
            applyreg.inputs.transformed_file= pvc_img
            applyreg.run()

        # Resample RBV/MG to T1w/nativepro space
        for space in ['T1wFS']:
            print(f"Resampling {pvc_method} to {space} space...")
            mri = f"{f_surf_dir}/mri/orig.mgz"
            applyreg = ApplyVolTransform()
            applyreg.inputs.source_file= pvc_img
            applyreg.inputs.reg_header=True
            applyreg.inputs.target_file= mri
            applyreg.inputs.transformed_file=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc_method}_ref-none_trc-{trc}_pet.nii.gz"
            applyreg.run()

        utils.resample_to_nativepro(
            input=pvc_img,
            output=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wNativepro_pvc-{pvc_method}_ref-none_trc-{trc}_pet.nii.gz",
            reference=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz",
            interp='trilin')

    # PETPVC
    else: 
        import nipype.interfaces.petpvc as PETPVC

        if pvc_mask is None:
            print("No custom PVC mask provided. Generating default mask.")
            # make GM/WM mask
            gtmseg = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-gtmseg.nii.gz")
            gtmseg_data = gtmseg.get_fdata()

            GM_idx = [8, 10, 11, 12, 13,17,18,26,28,47,49,50,51,52,53,54,58,60,172,1001,1002,1003,1005,1006,1007,1008,1009,1010,1011,1012,1013,1014,1015,1016,1017,1018,1019,1020,1021,1022,1023,1024,1025,1026,1027,1028,1029,1030,1031,1032,1033,1034,1035,2001,2002,2003,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035]
            CSF_idx = [4,5,14,15,24,31,43,44,63,257]
            WM_idx = [2,7,16,41,46,85,174]
            background_idx = [0,130,165,258]

            GM_mask = np.isin(gtmseg_data, GM_idx).astype(int)
            CSF_mask = np.isin(gtmseg_data, CSF_idx).astype(int)
            WM_mask = np.isin(gtmseg_data, WM_idx).astype(int)
            background_mask = np.isin(gtmseg_data, background_idx).astype(int)

            if pvc_method == 'MG':
                gm_wm_mask = np.stack([GM_mask,WM_mask],axis=-1)
            else:
                gm_wm_mask = np.stack([GM_mask,WM_mask,CSF_mask,background_mask],axis=-1)
                
            nib.save(nib.Nifti1Image(gm_wm_mask,gtmseg.affine,gtmseg.header),f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz")
        else:
            print(f"Using custom PVC mask provided at {pvc_mask}.")
            # if mask provided is not f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz", copy it there
            if pvc_mask != f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz":
                print(f"Copying custom PVC mask to {mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz")
                shutil.copy(pvc_mask, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz")

        # Run PETPVC
        print("Running PETPVC...")
        pvc = PETPVC.PETPVC()
        pvc.inputs.in_file = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-none_ref-none_trc-{trc}_pet.nii.gz'
        pvc.inputs.mask_file = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-T1wFS_desc-PETPVCmask.nii.gz"
        pvc.inputs.out_file = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-{pvc_method}_ref-none_trc-{trc}_pet.nii.gz"
        pvc.inputs.pvc = pvc_method
        pvc.inputs.fwhm_x = psf
        pvc.inputs.fwhm_y = psf
        pvc.inputs.fwhm_z = psf
        if pvc_method == 'IY':
            pvc.inputs.n_iter = pvc_n_iter
        if pvc_method in ['RL', 'VC']:
            pvc.inputs.n_deconv = pvc_n_deconv
        pvc.run()
        
        ##############
        # Resample to T1w/nativepro space
        utils.resample_to_nativepro(
            input=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-{pvc_method}_ref-none_trc-{trc}_pet.nii.gz",
            output=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wNativepro_pvc-{pvc_method}_ref-none_trc-{trc}_pet.nii.gz",
            reference=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz",
            interp='trilin')

    utils.print_time_stamp(f"PVC completed for subject: {subject}, session: {session}, tracer: {trc}, method: {pvc_method}.","green")

def project_pet_data(
    subject: str,
    session: str,
    trc: str,
    bids_dir: str,
    subj_dir: str,
    pvc_method: str,
    ref_region: str,
    tmpdir: str,
    hippunfold_dir: str = None,
    cortical: bool = True,
    hippocampal: bool = True,
    smoothing: Union[float, List[float]] = 0.0,
):
    """
        This script is part of MICA-PET pipeline for projecting PET data to the cortical and/or hippocampal surface.
        FreeSurfer/FastSurfer must have been run first.
        The script requires the following arguments:
            -subject        : Subject identification. (eg. PX001)
            -session        : Session. (eg. 01)
            -trc            : Tracer (eg. FDG, MK6240)
            -bids_dir       : Path to BIDS directory ( . or FULL PATH)
            -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
            -pvc_method     : PVC method used for PET image. Options: 'RBV-FS', 'MG-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'.
            -ref_region : Reference regions to use for projection. eg. 'pons','cerebellarGM','cerebellum','composite','WM','GM'. Default: 'pons'.
            -tmpdir        : Path to temporary directory.
    """
    from nipype.interfaces.freesurfer import FSCommand, MRICoreg, ApplyVolTransform
    from nipype.interfaces.workbench.base import WBCommand
    import pandas as pd
    from pathlib import Path

    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"
    f_surf_dir = f"{os.path.realpath(subj_dir)}/sub-{subject}_ses-{session}"
    FSCommand.set_default_subjects_dir(subj_dir)

    # Normalize input into a list if a single int/float was passed
    if isinstance(smoothing, (int, float)):
        smoothing_list = [float(smoothing)]
    elif isinstance(smoothing, list):
        smoothing_list = [float(s) for s in smoothing]
    elif isinstance(smoothing, str):
        smoothing_list = [float(x) for x in smoothing.split()]
    else:
        raise TypeError(f"smoothing must be a float or list of floats, got {type(smoothing)}")

    # Check that at least one of cortical or hippocampal is specified
    if not (cortical or hippocampal):
        print("Error: At least one of 'cortical' or 'hippocampal' must be specified.")
        sys.exit(1)

    parent_dir = Path(__file__).resolve().parents[1]
    ref_region_list_df = pd.read_csv(f"{parent_dir}/resources/ref_region_list.csv")
    ref_region_list = ref_region_list_df.ref_region.to_list()
    if ref_region not in ref_region_list:
        print(f"Error: Inputted: {ref_region}. None of the reference regions are valid.")
        sys.exit(1)

    
    # check if hippunfold_dir exists
    if hippocampal:
        if hippunfold_dir is None: #check if user inputted hippunfold_dir
            hippunfold_dir = f"{bids_dir}/derivatives/hippunfold_v1.4.1" 
            if not os.path.exists(hippunfold_dir):
                print(f"Error: HippUnfold directory {hippunfold_dir} does not exist.")
                sys.exit(1)
        else:
            hippunfold_dir = os.path.realpath(hippunfold_dir)
            if not os.path.exists(hippunfold_dir):
                print(f"Error: HippUnfold directory {hippunfold_dir} does not exist.")
                sys.exit(1)

    # Set pvc_options and smoothing_list_int for later use
    pvc_options = ['none', pvc_method]
    smoothing_list_int = [int(x) for x in smoothing_list]

    utils.print_time_stamp(f"Starting PET data projection to surface for subject: {subject}, session: {session}, tracer: {trc}, PVC method: {pvc_method}, reference regions: {ref_region}.")

    ref_region = [ref_region]

    space='T1wFS'
    if cortical:
        print("Doing cortical surface projection.")
        for hemi in ['L','R']:
            for pvc in pvc_options:
                for ref in ref_region:
                    print(f"Processing PVC method: {pvc}, reference region: {ref}, hemisphere: {hemi}...")
                    SUVR_map=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.nii.gz'
                    
                    surf_fsnative=f'{f_surf_dir}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-fsnative_label-midthickness.surf.gii'
                    
                    SUVR_on_surf=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-fsnative_label-midthickness_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.func.gii'
                    WBCommand(f'wb_command -volume-to-surface-mapping {SUVR_map} {surf_fsnative} {SUVR_on_surf} -trilinear').run()
                    
                    for surf in ['fsLR-32k','fsLR-5k']:
                        print(f"Resampling to {surf}...")
                        
                        sphere_surf=f'{f_surf_dir}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-fsnative_label-sphere.surf.gii'
                        
                        reg_surf_gii=f'{repo_dir}/surfaces/{surf}.{hemi}.sphere.reg.surf.gii'
                        
                        SUVR_resampled_out=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-{surf}_label-midthickness_pvc-{pvc}_ref-{ref}_smooth-none_trc-{trc}_pet.func.gii'
                        
                        WBCommand(f'wb_command -metric-resample {SUVR_on_surf} {sphere_surf} {reg_surf_gii} BARYCENTRIC {SUVR_resampled_out}').run()
                        
                        if np.max(smoothing_list_int) > 0: # only do smoothing if user specified smoothing values > 0
                            for smooth in smoothing_list_int:
                                print(f"Smoothing with {smooth}mm kernel...")
                                midthick_surf=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_space-{space}_surf-{surf}_label-midthickness.surf.gii'
                                
                                SUVR_resampled_smooth_out=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-{surf}_label-midthickness_pvc-{pvc}_ref-{ref}_smooth-{smooth}mm_trc-{trc}_pet.func.gii'
                            
                                WBCommand(f'wb_command -metric-smoothing {midthick_surf} {SUVR_resampled_out} {smooth} {SUVR_resampled_smooth_out}').run()

    if hippocampal:
        print("Doing hippocampal surface projection.")
        # register FS T1w to hippunfold T1w, as they may be in different spaces
        coreg = MRICoreg()
        coreg.inputs.source_file=f'{hippunfold_dir}/hippunfold/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_desc-preproc_T1w.nii.gz'
        coreg.inputs.subjects_dir=subj_dir
        coreg.inputs.subject_id=f"sub-{subject}_ses-{session}"
        coreg.inputs.out_lta_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from-T1wHippUnfold_to-T1wFS_xfm.reg.lta'
        coreg.run()
        
        
        for ref in ref_region:
            for pvc in pvc_options:
                # apply inverse transforms to PET images -> they will be in hippunfold T1w space
                applyreg = ApplyVolTransform()
                applyreg.inputs.source_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-T1wFS_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.nii.gz'
                applyreg.inputs.lta_inv_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from-T1wHippUnfold_to-T1wFS_xfm.reg.lta'
                applyreg.inputs.target_file=f'{hippunfold_dir}/hippunfold/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_desc-preproc_T1w.nii.gz'
                applyreg.inputs.transformed_file=f'{tmpdir}/sub-{subject}_ses-{session}_space-T1wHippUnfold_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.nii.gz'
                applyreg.run()
                
                for hemi in ['L','R']:
                    print(f"Processing PVC method: {pvc}, reference region: {ref}, hemisphere: {hemi}...")
                    SUVR_map=f'{tmpdir}/sub-{subject}_ses-{session}_space-T1wHippUnfold_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.nii.gz'
                    
                    if os.path.exists(SUVR_map) is False:
                        print(f"Error: SUVR map in T1w space does not exist... Needed for HippUnfold projection.")
                        sys.exit(1)
                    
                    hipp_surf=f'{hippunfold_dir}/hippunfold/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_space-T1w_den-2mm_label-hipp_midthickness.surf.gii'
                    
                    SUVR_on_surf=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-{hemi}_surf-hipp_den-2mm_label-midthickness_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.func.gii'
                    
                    WBCommand(f'wb_command -volume-to-surface-mapping {SUVR_map} {hipp_surf} {SUVR_on_surf} -trilinear').run()

    utils.print_time_stamp(f"PET data projection to surface completed for subject: {subject}, session: {session}, tracer: {trc}, PVC method: {pvc_method}, reference regions: {ref_region[0]}.","green")

def suvr(
    subject: str,
    session: str,
    trc: str,
    bids_dir: str,
    subj_dir: str,
    pvc_method: str,
    ref_region: str
):
    """
        This script is part of MICA-PET pipeline for standard uptake value ratio (SUVR) calculation.
        GTMseg and partial volume correction must have been run first.
        The script requires the following arguments:
            -subject        : Subject identification. (eg. PX001)
            -session        : Session. (eg. 01)
            -trc            : Tracer (eg. FDG, MK6240)
            -bids_dir       : Path to BIDS directory ( . or FULL PATH)
            -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
            -pvc_method     : PVC method used for PET image. Options: 'RBV-FS','MG-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'.
            -ref_region : Reference regions to use for projection. eg. 'pons','cerebellarGM','cerebellum','composite','WM','GM'. Default: 'pons'.
    """
    from nipype.interfaces.freesurfer import FSCommand, ApplyVolTransform
    import glob
    from scipy.ndimage import binary_erosion
    from pathlib import Path
    import pandas as pd

    parent_dir = Path(__file__).resolve().parents[1]
    ref_region_list_df = pd.read_csv(f"{parent_dir}/resources/ref_region_list.csv")
    ref_region_list = ref_region_list_df.ref_region.to_list()
    
    f_surf_dir = f"{os.path.realpath(subj_dir)}/sub-{subject}_ses-{session}"
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"
    FSCommand.set_default_subjects_dir(subj_dir)

    utils.print_time_stamp(f"Starting SUVR calculation for subject: {subject}, session: {session}, tracer: {trc}, PVC method: {pvc_method}, reference regions: {ref_region}.")

    def ROImaker(roi,f_surf_dir,mica_pet_derivatives,subject,session,space, pvc_method, erode=False):
        print(f"Creating ROI mask for ROI {roi}...")

        in_file = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-gtmseg.nii.gz")
        in_data = in_file.get_fdata()
        roi_data = np.zeros(in_data.shape)
        # Set values in roi_data to 1 where in_data equals roi
        roi_data[in_data == roi] = 1
        if erode:
            roi_data = binary_erosion(roi_data, iterations=2)
        out_file = nib.Nifti1Image(roi_data, in_file.affine, in_file.header)
        nib.save(out_file, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/tmp_sub-{subject}_ses-{session}_space-{space}_desc-roi{roi}_mask.nii.gz")
        
    def combineROIs(ref,mica_pet_derivatives,subject,session,space):
        print(f"Combining ROI masks for reference region: {ref}...")
        mask_files = sorted(glob.glob(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/tmp_sub-{subject}_ses-{session}_space-{space}_desc-roi*_mask.nii.gz"))
        if len(mask_files) == 0:    
            print("Error: No ROI mask files found to combine.")
            sys.exit(1)
        
        # Combine masks using nibabel
        add_mask = nib.load(mask_files[0])
        add_mask_data = add_mask.get_fdata()
        for mask in mask_files[1:]:
            tmp = nib.load(mask)
            tmp_data = tmp.get_fdata()
            add_mask_data += tmp_data
        # Binarize
        add_mask_data[add_mask_data > 0] = 1
        out_file = nib.Nifti1Image(add_mask_data, add_mask.affine, add_mask.header)
        nib.save(out_file, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-{ref}_mask.nii.gz")

        # delete temporary files
        for mask in mask_files:
            os.remove(mask)
            
    ref_region = [ref_region]
    if ref_region[0] not in ref_region_list:
        print(f"Error: Inputted: {ref_region[0]}. None of the reference regions are valid. Please check resources/ref_region_list.csv for valid reference regions.")
        sys.exit(1)

    ## Create ROIs and calculate SUVR       
    for space in ['T1wFS','T1wNativepro']:
        for ref in ref_region:
            print(f"Processing reference region: {ref}...")

            ROI_ids = ref_region_list_df.loc[ref_region_list_df['ref_region'] == ref].ROI
            ROI_ids_list = [int(x) for val in ROI_ids for x in val.split(",")]

            erode_ids = ref_region_list_df.loc[ref_region_list_df['ref_region'] == ref].erode
            erode_ids_list = [x.strip().lower() == "true" for val in erode_ids for x in val.split(",")]

            for i in range(len(ROI_ids_list)):
                roi = ROI_ids_list[i]
                erode = erode_ids_list[i]
                ROImaker(roi,f_surf_dir,mica_pet_derivatives,subject,session,space, pvc_method, erode=erode)

            combineROIs(ref,mica_pet_derivatives,subject,session,space)      
                
            for pvc in [pvc_method, 'none']:
                # Calculate avg in reference region
                print(f"Calculating average uptake in reference region: {ref}, PVC: {pvc}, space: {space}...")

                if pvc == 'RBV-FS' or pvc == 'MG-FS': #use PVC image to calculate ref region uptake
                    in_file = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-none_trc-{trc}_pet.nii.gz")
                else: #use non-PVC image to calculate ref region uptake (as PVC image other than RBV-FS may have zero values in reference region)
                    in_file = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-none_trc-{trc}_pet.nii.gz")

                in_data = in_file.get_fdata()
                mask_file = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-{ref}_mask.nii.gz")
                mask_data = mask_file.get_fdata()
                masked_data = in_data[mask_data > 0]
                masked_data = masked_data[masked_data > 0]  # Exclude zero values. Only find average uptake in reference region where PET uptake is greater than zero.
                ref_region_avg = np.mean(masked_data)

                print(f"Reference region {ref}, pvc {pvc}, space {space} average uptake: {ref_region_avg}")

                # Calculate SUVR
                print("Calculating SUVR image...")
                in_file = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-none_trc-{trc}_pet.nii.gz")
                in_data = in_file.get_fdata()
                suvr_data = in_data / float(ref_region_avg)
                out_file = nib.Nifti1Image(suvr_data, in_file.affine, in_file.header)
                nib.save(out_file, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-{ref}_trc-{trc}_pet.nii.gz")

    utils.print_time_stamp(f"SUVR calculation completed for subject: {subject}, session: {session}, tracer: {trc}, PVC method: {pvc_method}, reference regions: {ref_region[0]}.","green")

def subcortical_map(
    subject: str,
    session: str,
    trc: str,
    bids_dir: str,
    subj_dir: str,
    pvc_method: str,
    ref_region: str
):
    """
        This script is part of MICA-PET pipeline for generating subcortical maps.
        GTMseg and partial volume correction must have been run first.

        The script requires the following arguments:
            -subject        : Subject identification. (eg. PX001)
            -session        : Session. (eg. 01)
            -trc            : Tracer (eg. FDG, MK6240)
            -bids_dir       : Path to BIDS directory ( . or FULL PATH)
            -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
            -pvc_method     : PVC method used for PET image. Options: 'RBV-FS', 'MG-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'.
            -ref_region : Reference regions to use for projection. eg. 'pons','cerebellarGM','cerebellum','composite','WM','GM'. Default: 'pons'.
    """  
    from nibabel.processing import resample_from_to
    import csv
    f_surf_dir = f"{os.path.realpath(subj_dir)}/sub-{subject}_ses-{session}"
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"
    qc_dir = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/qc"

    space='T1wFS'

    utils.print_time_stamp(f"Starting subcortical map generation for subject: {subject}, session: {session}, tracer: {trc}, PVC method: {pvc_method}, reference regions: {ref_region}.")


    print("Loading PET and aparc+aseg data...")
    src = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.nii.gz")
    pet_data = src.get_fdata()
    tgt = nib.load(f"{f_surf_dir}/mri/aparc+aseg.mgz")
    aseg_aparc_data = tgt.get_fdata()

    # This uses the header affines by default — equivalent to regheader
    print("Resampling PET to aparc+aseg space...")
    resampled = resample_from_to(src, tgt,order=0)

    # puts pet in same space as aparc+aseg
    print("Putting pet in same space as aparc+aseg...")
    pet_resampled_data = resampled.get_fdata()

    # Compute means for each region
    print("Computing means for each subcortical region...")
    regions = list(utils.subcortical_dict.keys())
    means = [np.mean(pet_resampled_data[aseg_aparc_data == utils.subcortical_dict[region]]) for region in regions]

    for region, mean_val in zip(regions, means):
        print(f"{region:25s}: {mean_val:.4f}")

    # Write to CSV
    output_file = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_subcortical_means_pet.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(regions)
        writer.writerow(means)

    utils.print_time_stamp(f"Subcortical map generation completed for subject: {subject}, session: {session}, tracer: {trc}, PVC method: {pvc_method}, reference regions: {ref_region}.","green")
    print("")

def report(
    subject: str,
    session: str,
    trc: str,
    bids_dir: str,
    subj_dir: str,
    pvc_method: str,
    ref_region: str,
    hippocampal: bool = True,
    max_value: float = None
):
    """
        This script is part of MICA-PET pipeline for generating HTML reports.

        The script requires the following arguments:
            -subject        : Subject identification. (eg. PX001)
            -session        : Session. (eg. 01)
            -trc            : Tracer (eg. FDG, MK6240)
            -bids_dir       : Path to BIDS directory ( . or FULL PATH)
            -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
            -pvc_method     : PVC method used for PET image. Options: 'RBV-FS', 'MG-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'.
            -ref_region : Reference regions to use for projection. eg. 'pons','cerebellarGM','cerebellum','composite','WM','GM'. Default: 'pons'.
            -hippocampal    : (Optional) Whether to include hippocampal surface in report. Default: True.
            -max_value      : (Optional) Maximum SUVR value for color scale. Default: 1.5 times the 85th percentile SUVR in the data.

    """
    import gc
    from nipype.interfaces.freesurfer import FSCommand, MRIConvert, ApplyVolTransform
    import nilearn
    from nilearn import plotting
    from brainstat.datasets import fetch_mask, fetch_template_surface
    from brainspace.plotting import plot_hemispheres
    import hippomaps as hm
    import matplotlib.pyplot as pltl
    import pandas as pd
    from PIL import Image
    # import report_creator as rc
    from petreport import report as rc
    import nibabel as nib
    from brainspace.mesh.mesh_io import read_surface
    from pathlib import Path
    from typing import List, Union, Tuple, Literal
    PathType = Union[str, os.PathLike]
    Analysis = Literal["regional", "asymmetry"]

    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"
    f_surf_dir = f"{os.path.realpath(subj_dir)}/sub-{subject}_ses-{session}"
    qc_dir = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/qc"
    FSCommand.set_default_subjects_dir(subj_dir)

    display_flag = False
    import platform
    if (
            "DISPLAY" not in os.environ or not os.environ["DISPLAY"]
        ) and platform.system() != "Windows":
            try:
                from pyvirtualdisplay import Display
                os.environ["PYVIRTUALDISPLAY_DISPLAYFD"] = "0"
                dsize = (900, 750)
                display = Display(visible=False, size=dsize)
                display.start()
                display_flag = True
            except ImportError:
                print("Warning: pyvirtualdisplay not available, plotting may fail in headless environment")
    
    space='T1wFS'

    # Max value
    if max_value is not None:
        max_value = max_value
    else:
        max_value = None

    utils.print_time_stamp(f"Starting report generation for subject: {subject}, session: {session}, tracer: {trc}, PVC method: {pvc_method}, reference regions: {ref_region}.")

    pial_left, pial_right = fetch_template_surface("fslr32k",join=False)
    mask = fetch_mask("fslr32k")

    # Create brainmasked PET
    if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-{ref_region}_trc-{trc}_pet_desc-brainmask.nii.gz"):
        print("Creating brainmasked PET image...")
        mc = MRIConvert()
        mc.inputs.in_file = f'{f_surf_dir}/mri/apas+head.mgz'
        mc.inputs.out_file = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/tmp.brainmask.nii.gz'
        mc.inputs.out_type = 'niigz'
        print(mc.cmdline)
        mc.run()
        
        applyreg = ApplyVolTransform()
        
        if os.path.exists(f'{f_surf_dir}/mri/apas+head.mgz'):
            applyreg.inputs.source_file=f'{f_surf_dir}/mri/apas+head.mgz'
        else:
            applyreg.inputs.source_file=f'{f_surf_dir}/mri/aparc+aseg.mgz'
        applyreg.inputs.reg_header=True
        applyreg.inputs.target_file=f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-{ref_region}_trc-{trc}_pet.nii.gz"
        applyreg.inputs.transformed_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/tmp.brainmask.nii.gz'
        applyreg.run()

        in_file = nib.load(f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/tmp.brainmask.nii.gz')
        in_data = in_file.get_fdata()
        tmp_data = np.zeros(in_data.shape)
        tmp_data[in_data > 0] = 1
        out_file = nib.Nifti1Image(tmp_data, in_file.affine, in_file.header)
        nib.save(out_file, f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/tmp.brainmask_bin.nii.gz')
        
        pet_in_file = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-{ref_region}_trc-{trc}_pet.nii.gz")
        pet_in_data = pet_in_file.get_fdata()
        brainmasked_data = pet_in_data * tmp_data
        out_pet_file = nib.Nifti1Image(brainmasked_data, pet_in_file.affine, pet_in_file.header)
        nib.save(out_pet_file, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-{ref_region}_trc-{trc}_pet_desc-brainmask.nii.gz")

        # remove temp files
        os.remove(f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/tmp.brainmask.nii.gz')
        os.remove(f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/tmp.brainmask_bin.nii.gz')
        
    # make maps
    pial_left, pial_right = fetch_template_surface("fslr32k",join=False)
    mask = fetch_mask("fslr32k")

    def get_surf_path(mica_pet_derivatives, subject, session, hemi, pvc_method, ref_region, trc):
        """Return the surface .func.gii path with the highest smooth-Xmm kernel,
        falling back to smooth-none if no smoothed file exists."""
        import glob
        import re
        pattern = (
            f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/"
            f"sub-{subject}_ses-{session}_hemi-{hemi}_surf-fsLR-32k_label-midthickness"
            f"_pvc-{pvc_method}_ref-{ref_region}_smooth-*mm_trc-{trc}_pet.func.gii"
        )
        matches = glob.glob(pattern)
        if matches:
            def smooth_val(p): # return image with highest smoothing
                m = re.search(r'smooth-(\d+)mm', p)
                return int(m.group(1)) if m else 0
            return max(matches, key=smooth_val)
        return (
            f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/"
            f"sub-{subject}_ses-{session}_hemi-{hemi}_surf-fsLR-32k_label-midthickness"
            f"_pvc-{pvc_method}_ref-{ref_region}_smooth-none_trc-{trc}_pet.func.gii"
        )

    ## Cortical surface
    print("Generating cortical surface QC images...")
    tmp_surf_L = nilearn.surface.load_surf_data(get_surf_path(mica_pet_derivatives, subject, session, "L", pvc_method, ref_region, trc))
    tmp_surf_R = nilearn.surface.load_surf_data(get_surf_path(mica_pet_derivatives, subject, session, "R", pvc_method, ref_region, trc))

    to_plot = np.hstack((tmp_surf_L,tmp_surf_R))
    to_plot[~mask] = np.nan
    plot_hemispheres(pial_left,pial_right,to_plot,color_bar=True, cmap="jet",color_range=(0,np.max(to_plot[mask])*1.5), embed_nb=False,transparent_bg=True,size=(900,200),nan_color=(0.7, 0.7, 0.7, 1),screenshot=True,filename=f"{qc_dir}/sub-{subject}_ses-{session}_cortical_surf_screenshot.png")

    ## HC surface
    if hippocampal:
        tmp_hcsurf_L = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")
        tmp_hcsurf_R = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")

        to_plot = np.hstack((np.expand_dims(tmp_hcsurf_L,axis=1),np.expand_dims(tmp_hcsurf_R,axis=1)))
        hm.plotting.surfplot_canonical_foldunfold(to_plot,hemis=['L','R'],den='2mm',labels=['hipp'],embed_nb=False,transparent_bg=True,tighten_cwindow=True,screenshot=True,filename=f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_hippunfold_screenshot.png")

    ## Plot PET-MRI overlay
    plotting.plot_roi(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-{ref_region}_trc-{trc}_pet_desc-brainmask.nii.gz",
        bg_img=f"{f_surf_dir}/mri/orig.mgz",
        display_mode='mosaic',
        cut_coords=15,
        alpha=0.6,
        radiological=True,
        title=f"Subject {subject} SUVR QC",
        resampling_interpolation='continuous',
        output_file=f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_SUVR_mosaic_screenshot.png")

    ## Subcortical surface
    parent_dir = Path(__file__).resolve().parents[1]

    sctx_left = read_surface(f"{parent_dir}/surfaces/sctx.L.surf.gii", itype="gii")
    sctx_right = read_surface(f"{parent_dir}/surfaces/sctx.R.surf.gii", itype="gii")
    # Utility functions ------------------------------------------------------------
    def map_subcortical_vertices(x) -> np.ndarray:
        """
        Taken from the ENIGMA toolbox
        https://github.com/MICA-MNI/ENIGMA/blob/master/enigmatoolbox
        Map one value per subcortical area to surface vertices (author:
        @saratheriver)
        Parameters
        ----------
        x:
            Subcortical values with shape = (16,) in the following order:
            L_accumbens, L_amygdala, L_caudate, L_hippocampus, L_pallidun,
            L_putamen, L_thalamus, L_ventricles,
            R_accumbens, R_amygdala, R_caudate, R_hippocampus, R_pallidun,
            R_putamen, R_thalamus, R_ventricles
        zbrains output (the fisrt colum is SubjID):
            'Laccumb', 'Lamyg', 'Lcaud', 'Lhippo', 'Lpal', 'Lput','Lthal',
            'Raccumb', 'Ramyg', 'Rcaud', 'Rhippo', 'Rpal', 'Rput', 'Rthal'
        Returns
        -------
        data :
            Mapped data, shape = (51278,)
        """
        n_vert = [
            867,
            1419,
            3012,
            3784,
            1446,
            4003,
            3726,
            7653,
            838,
            1457,
            3208,
            3742,
            1373,
            3871,
            3699,
            7180,
        ]
        x = np.asarray(x)
        if x.shape == (16,):
            return np.repeat(x, n_vert)
        else:
            raise ValueError("Input data must have 16 values.")
        
    def _load_data_sctx(
        sctx_file: PathType,
        analysis: Analysis,
        threshold: Union[float, None] = None,
        threshold_alpha: float = 0.5,
    ):
        # Load CSV data
        x = pd.read_csv(sctx_file, header=[0], index_col=None).to_numpy().ravel()
        if threshold is not None:
            x[np.abs(x) < threshold] *= threshold_alpha
        # if analysis == "asymmetry":
        #     print("e")
        # Array of data
        array_16 = np.full(16, np.nan)
        
        if analysis != "asymmetry":
            array_16[0:7] = x[0:7]
            array_16[8:15] = x[7:]
        else:
            array_16[0:7] = (x[0:7]-x[7:])/((x[0:7]+x[7:])/2)
            array_16[8:15] = x[0:7]
            array_16[8:15] = np.nan
        # Fill ventricle slots with 0 (or another default) instead of leaving as NaN
        array_16[7] = np.nan #0.0   # Left ventricle
        array_16[15] = np.nan #0.0  # Right ventricle
        # Map array to vertices of surfaces
        feat_map = map_subcortical_vertices(array_16)
        # Map array to left and right surfaces
        data_lh = feat_map[0:25910]
        data_rh = feat_map[25910:]
        return data_lh, data_rh

    def plot_SUVR(subject,session,bids_dir,qc_dir,pial_left,pial_right,mask,max_value,mica_pet_derivatives,ref_region,trc,pvc_method):

        tmp_pt_FDG_surf_L = nilearn.surface.load_surf_data(get_surf_path(mica_pet_derivatives, subject, session, "L", pvc_method, ref_region, trc))
        tmp_pt_FDG_surf_R = nilearn.surface.load_surf_data(get_surf_path(mica_pet_derivatives, subject, session, "R", pvc_method, ref_region, trc))

        to_plot = np.hstack((tmp_pt_FDG_surf_L,tmp_pt_FDG_surf_R))
        to_plot[~mask] = np.nan
        

        if max_value is None:
            max_value = np.max(to_plot[mask]) *1.5
            
        img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_SUVR_clin_report.png"
        plot_hemispheres(pial_left,pial_right,to_plot,color_bar=True, 
                        cmap="jet",color_range=(0,max_value), embed_nb=False,transparent_bg=True,size=(900,200),nan_color=(1,1,1, 1),screenshot=True,filename=img_stream)
        return img_stream, max_value


    # Plotting functions ------------------------------------------------------------

    def plot_subcort(subject,session,bids_dir,qc_dir,ref_region,max_value,pvc_method,trc):
        # subcort_SUVR = pd.read_csv(f'{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_subcortical_means_pet.csv',header=None).to_numpy()
        # to_plot = subcort_SUVR[1,:]
        
        data_lh, data_rh = _load_data_sctx(
        sctx_file=Path(f'{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_subcortical_means_pet.csv'),
        analysis="regional"
    )
        to_plot = np.hstack((data_lh, data_rh))

        img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_SUVR_subcortical_clin_report.png"

        plot_hemispheres(sctx_left,sctx_right,to_plot,color_bar='right', 
            cmap="jet",color_range=(0,max_value), embed_nb=False,transparent_bg=True,size=(900,200),nan_color=(1,1,1, 0),screenshot=True,filename=img_stream)

        return img_stream

    def plot_hippunfold(subject,session,bids_dir,qc_dir,max_value,mica_pet_derivatives,ref_region,trc,pvc_method):
        tmp_hcsurf_L = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")

        tmp_hcsurf_R = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")             

        to_plot = np.hstack((np.expand_dims(tmp_hcsurf_L,axis=1),np.expand_dims(tmp_hcsurf_R,axis=1)))

        img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_hippunfold_clin_report.png"

        hm.plotting.surfplot_canonical_foldunfold(to_plot,color_bar=True,color_range=(0,max_value),hemis=['L','R'],den='2mm',labels=['hipp'],embed_nb=False,transparent_bg=True,tighten_cwindow=True,screenshot=True,cmap='jet',  size=[350,300],filename=img_stream) #,color_range=(0,max_value)

        return img_stream

    def plot_hippunfold_AI(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region,trc,pvc_method):
        tmp_hcsurf_L = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")

        tmp_hcsurf_R = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")

        AI_L = (tmp_hcsurf_L - tmp_hcsurf_R)/(0.5 * (tmp_hcsurf_L+tmp_hcsurf_R))             

        to_plot = AI_L

        img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_AI_hippunfold_clin_report.png"

        hm.plotting.surfplot_canonical_foldunfold(to_plot,hemis=['L'],den='2mm',labels=['hipp'],embed_nb=False,color_bar='bottom',transparent_bg=True,tighten_cwindow=True,screenshot=True,cmap='bwr',color_range=(-0.25,0.25), size=[350,350],filename=img_stream)

        return img_stream

    # Plotting asymmetry -------------------------------------------------------------
        
    def plot_AI(subject,session,bids_dir,qc_dir,pial_left,pial_right,mica_pet_derivatives,ref_region,trc,pvc_method):
        from utils import convert_array_to_gifti
        
        tmp_pt_FDG_surf_L = nilearn.surface.load_surf_data(get_surf_path(mica_pet_derivatives, subject, session, "L", pvc_method, ref_region, trc))
        tmp_pt_FDG_surf_R = nilearn.surface.load_surf_data(get_surf_path(mica_pet_derivatives, subject, session, "R", pvc_method, ref_region, trc))

        AI_R = (tmp_pt_FDG_surf_R - tmp_pt_FDG_surf_L)/ (0.5 * (tmp_pt_FDG_surf_R + tmp_pt_FDG_surf_L))
        AI_L = (tmp_pt_FDG_surf_L - tmp_pt_FDG_surf_R)/ (0.5 * (tmp_pt_FDG_surf_R + tmp_pt_FDG_surf_L))

        to_plot = np.hstack((AI_L,np.zeros(32492)))
        to_plot[~mask] = np.nan

        img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_AI_surface_clin_report.png"
        
        plot_hemispheres(pial_left, pial_right,to_plot,color_bar='left',cmap="bwr",color_range=(-0.25,0.25),embed_nb=False,transparent_bg=True,size=(900,200),nan_color=(1,1,1,1),screenshot=True,filename=img_stream)

        convert_array_to_gifti(to_plot[: len(to_plot) // 2], f"{qc_dir}/sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_desc-SUVRAI_pet.func.gii")
        convert_array_to_gifti(to_plot[len(to_plot) // 2 :], f"{qc_dir}/sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_desc-SUVRAI_pet.func.gii")
        
        # Crop the image in half lengthwise and keep the left side
        original_image_path = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_AI_surface_clin_report.png"
        cropped_image_path = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_AI_surface_clin_report_cropped.png"

        with Image.open(original_image_path) as img:
            width, height = img.size
            cropped_img = img.crop((0, 0, 500, height))  # Keep the left half
        
        cropped_img.save(cropped_image_path)

        return cropped_image_path

    def plot_subcortical_AI(subject,session,bids_dir,ref_region,qc_dir,pvc_method,trc):
        
        data_lh, data_rh = _load_data_sctx(
        sctx_file=Path(f'{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_subcortical_means_pet.csv'),
        analysis="asymmetry")   
        
        to_plot = np.hstack((data_lh, data_rh))

        img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_AI_subcortical_clin_report.png"

        plot_hemispheres(sctx_left,sctx_right,to_plot,color_bar='left', 
            cmap="bwr",color_range=(-0.25,0.25), embed_nb=False,transparent_bg=True,size=(900,200),nan_color=(1,1,1, 0),screenshot=True,filename=img_stream)
            
        cropped_image_path = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_AI_subcortical_clin_report_cropped.png"

        with Image.open(img_stream) as img:
            width, height = img.size
            cropped_img = img.crop((0, 0, 475, height))  # Keep the left half
        
        cropped_img.save(cropped_image_path)

        return cropped_image_path

    def plot_roi(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region,trc,pvc_method):
        pet_derivatives=f'{mica_pet_derivatives}'
        mri_derivatives=f'{bids_dir}/derivatives/fastsurfer'

        img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_SUVR_plot_roi_clin_report.png"

        plotting.plot_roi(f'{pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-{ref_region}_trc-{trc}_pet_desc-brainmask.nii.gz',bg_img=f'{mri_derivatives}/sub-{subject}_ses-{session}/mri/orig.mgz',display_mode='z',cut_coords=tuple(np.linspace(-75,75,15)),alpha=0.3,radiological=True, title=f'sub-{subject} ses-{session} FDG SUVR',dim=0,resampling_interpolation='continuous',output_file=img_stream)

        return img_stream

    def max_hist(data, bins=50):
        data = data[~np.isnan(data)]  # Remove NaN values
        hist_values, bin_edges = np.histogram(data, bins=bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        max_index = np.argmax(hist_values)
        max_value = bin_centers[max_index]
        return max_value

    def plot_Zscore(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region,trc):
        from utils import convert_array_to_gifti

        pet_derivatives=f'{mica_pet_derivatives}'
        mri_derivatives=f'{bids_dir}/derivatives/fastsurfer'
        pvc_method = 'none'
        Z_score_threhold = 1.96

        FDG_surf_ctrl_hist_norm_mean = np.genfromtxt(f'{parent_dir}/surfaces/FDG_surf_ctrl_hist_norm_mean.csv', delimiter=',', missing_values='""', filling_values=np.nan)
        FDG_surf_ctrl_hist_norm_std = np.genfromtxt(f'{parent_dir}/surfaces/FDG_surf_ctrl_hist_norm_std.csv', delimiter=',', missing_values='""', filling_values=np.nan)
        
        tmp_L = nilearn.surface.load_surf_data(get_surf_path(pet_derivatives, subject, session, "L", pvc_method, ref_region, trc))
        tmp_R = nilearn.surface.load_surf_data(get_surf_path(pet_derivatives, subject, session, "R", pvc_method, ref_region, trc))

        tmp = np.hstack((tmp_L,tmp_R))
        tmp[~mask] = np.nan
        norm_factor = max_hist(tmp) #normalize by histogram max
        test_FDG_surf_pt = tmp / norm_factor

        Zscore = (test_FDG_surf_pt - FDG_surf_ctrl_hist_norm_mean)/ FDG_surf_ctrl_hist_norm_std

        to_plot = Zscore
        # to_plot = test_FDG_surf_pt
        to_plot[~mask] = np.nan   
        to_plot[(to_plot >= -Z_score_threhold) & (to_plot <= Z_score_threhold)] = 0 # Filter out values outside the range

        img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_SUVR_plot_Zscore_clin_report.png"

        # save gifti
        convert_array_to_gifti(to_plot[: len(to_plot) // 2], f"{qc_dir}/sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_desc-SUVRZscore_pet.func.gii")
        convert_array_to_gifti(to_plot[len(to_plot) // 2 :], f"{qc_dir}/sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_desc-SUVRZscore_pet.func.gii")

        plot_hemispheres(pial_left, pial_right,to_plot,color_bar=True,embed_nb=False,transparent_bg=True,cmap=["bwr"],color_range=(-5,5),size=(900,200),nan_color=(0.7, 0.7, 0.7, 1),screenshot=True,filename=img_stream)

        return img_stream

    def parcel_stats(subject,session,bids_dir,subj_dir,qc_dir,space,mica_pet_derivatives,ref_region,trc,pvc_method):
        import nibabel as nib
        import numpy as np
        from nibabel.processing import resample_from_to
        import csv
        dict = {
            "L":{
                "Cerebellum-Cortex": 8,
                "Thalamus": 10,
                "Caudate": 11,
                "Putamen": 12,
                "Hippocampus": 17,
                "Amygdala": 18,
                "Caudal-Anterior-Cingulate": 1002,
                "Caudal-Middle-Frontal": 1003,
                "Cuneus": 1005,
                "Entorhinal": 1006,
                "Fusiform": 1007,
                "Inferior-Parietal": 1008,
                "Inferior-Temporal": 1009,
                "Isthmus-Cingulate": 1010,
                "Lateral-Occipital": 1011,
                "Lateral-Orbitofrontal": 1012,
                "Lingual": 1013,
                "Medial-Orbitofrontal": 1014,
                "Middle-Temporal": 1015,
                "Parahippocampal": 1016,
                "Paracentral": 1017,
                "Pars-Opercularis": 1018,
                "Pars-Orbitalis": 1019,
                "Pars-Triangularis": 1020,
                "Pericalcarine": 1021,
                "Postcentral": 1022,
                "Posterior-Cingulate": 1023,
                "Precentral": 1024,
                "Precuneus": 1025,
                "Rostral-Anterior-Cingulate": 1026,
                "Rostral-Middle-Frontal": 1027,
                "Superior-Frontal": 1028,
                "Superior-Parietal": 1029,
                "Superior-Temporal": 1030,
                "Supramarginal": 1031,
                # "Frontalpole": 1032,
                # "Temporalpole": 1033,
                "Transverse-Temporal": 1034,
                "Insula": 1035
            },
            "R":{            
                "Cerebellum-Cortex": 47,
                "Thalamus": 49,
                "Caudate": 50,
                "Putamen": 51,
                "Hippocampus": 53,
                "Amygdala": 54,
                "Caudal-Anterior-Cingulate": 2002,
                "Caudal-Middle-Frontal": 2003,
                "Cuneus": 2005,
                "Entorhinal": 2006,
                "Fusiform": 2007,
                "Inferior-Parietal": 2008,
                "Inferior-Temporal": 2009,
                "Isthmus-Cingulate": 2010,
                "Lateral-Occipital": 2011,
                "Lateral-Orbitofrontal": 2012,
                "Lingual": 2013,
                "Medial-Orbitofrontal": 2014,
                "Middle-Temporal": 2015,
                "Parahippocampal": 2016,
                "Paracentral": 2017,
                "Pars-Opercularis": 2018,
                "Pars-Orbitalis": 2019,
                "Pars-Triangularis": 2020,
                "Pericalcarine": 2021,
                "Postcentral": 2022,
                "Posterior-Cingulate": 2023,
                "Precentral": 2024,
                "Precuneus": 2025,
                "Rostral-Anterior-Cingulate": 2026,
                "Rostral-Middle-Frontal": 2027,
                "Superior-Frontal": 2028,
                "Superior-Parietal": 2029,
                "Superior-Temporal": 2030,
                "Supramarginal": 2031,
                # "Frontalpole": 2032,
                # "Temporalpole": 2033,
                "Transverse-Temporal": 2034,
                "Insula": 2035
            }
        }
        
        src = nib.load(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.nii.gz")
        pet_data = src.get_fdata()
        tgt = nib.load(f"{subj_dir}/sub-{subject}_ses-{session}/mri/aparc+aseg.mgz")
        # ^ change to f_surf_dir eventually
        aseg_aparc_data = tgt.get_fdata()

        # This uses the header affines by default — equivalent to regheader
        resampled = resample_from_to(src, tgt,order=0)

        # puts pet in same space as aparc+aseg
        pet_resampled_data = resampled.get_fdata()

        # Compute means for each region
        df = pd.DataFrame(columns=['Region','L_SUVR','R_SUVR','L-R_difference','Asymmetry_Index'])

        df.Region = dict["L"].keys()

        for i in df.index:
            region = df.loc[i,'Region']
            L_mean = round(np.mean(pet_resampled_data[aseg_aparc_data == dict["L"][region]]), 2)
            R_mean = round(np.mean(pet_resampled_data[aseg_aparc_data == dict["R"][region]]), 2)
            mean_suvr = round((L_mean + R_mean) / 2, 2)
            asym_index = round((L_mean - R_mean) / mean_suvr, 2) if mean_suvr != 0 else 0
            df.loc[i,'L_SUVR'] = L_mean
            df.loc[i,'R_SUVR'] = R_mean
            df.loc[i,'L-R_difference'] = round(L_mean - R_mean, 2)
            df.loc[i,'Asymmetry_Index'] = asym_index
            
            regions = list(dict['L'].keys())
            
        df = df.sort_values(by='Asymmetry_Index', ascending=True).reset_index(drop=True) 

        output_file = f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_AI_parcelstats.csv"

        df.to_csv(output_file, index=False)
        return df


    cortical_SUVR, max_value = plot_SUVR(subject,session,bids_dir,qc_dir, pial_left, pial_right, mask,max_value,mica_pet_derivatives,ref_region,trc,pvc_method)

    # if trc == "FDG":
    #     with rc.ReportCreator(
    #         title="MICA-PET Report",
    #         description=f"**Subject**: {subject} | **Session**: {session} | **Modality**: {trc} PET | **Ref region**: {ref_region} | **PVC method**: {pvc_method}",
    #         footer="Multimodal Imaging and Connectome Analysis (MICA) Lab - McGill University. For research use only.",
    #         logo=f"https://box.bic.mni.mcgill.ca/s/GbLcj26GmYWBfLL/download"
    #     ) as report:
            
    #         if hippocampal:
    #             SUVR_blocks = [
    #                     rc.Image(
    #                         cortical_SUVR,
    #                         label=f"Cortical {trc} SUVR",
    #                         extra_css="width: 900px; height: auto;",
    #                     ),
    #                     # rc.Image(
    #                     #     plot_subcort(subject,session,bids_dir,qc_dir,ref_region,max_value,pvc_method,trc),
    #                     #     label=f"Subcortical {trc} SUVR",
    #                     #     extra_css="width: 900px; height: auto;",
    #                     # ),
    #                     rc.Image(
    #                         plot_hippunfold(subject,session,bids_dir,qc_dir,max_value,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label=f"Hippocampal {trc} SUVR",
    #                         extra_css="width: 450px; height: auto;",
    #                     ) 
    #                 ]
    #             AI_blocks = [
    #                     # The `rc.Image()` blocks in the code are creating images to be displayed in the report.
    #                     # Each `rc.Image()` block specifies the path to an image file and provides a label for
    #                     # that image.
    #                     rc.Image(
    #                         plot_AI(subject,session,bids_dir,qc_dir, pial_left, pial_right,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label=f"Cortical {trc} SUVR AI"
    #                     ),
    #                     rc.Image(
    #                         plot_subcortical_AI(subject,session,bids_dir,ref_region,qc_dir,pvc_method,trc),
    #                         label=f"Subcortical {trc} SUVR AI"
    #                     ),
    #                     rc.Image(
    #                         plot_hippunfold_AI(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label=f"Hippocampal {trc} SUVR AI",
    #                     ),
                        
    #                 ]
    #         else:
    #             SUVR_blocks = [
    #                     rc.Image(
    #                         cortical_SUVR,
    #                         label=f"Cortical {trc} SUVR",
    #                         extra_css="width: 900px; height: auto;",
    #                     ),
    #                     rc.Image(
    #                         plot_subcort(subject,session,bids_dir,qc_dir,ref_region,max_value,pvc_method,trc),
    #                         label=f"Subcortical {trc} SUVR",
    #                         extra_css="width: 900px; height: auto;",
    #                     )
    #                 ]
    #             AI_blocks = [
    #                     # The `rc.Image()` blocks in the code are creating images to be displayed in the report.
    #                     # Each `rc.Image()` block specifies the path to an image file and provides a label for
    #                     # that image.
    #                     rc.Image(
    #                         plot_AI(subject,session,bids_dir,qc_dir, pial_left, pial_right,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label=f"Cortical {trc} SUVR AI"
    #                     ),
    #                     rc.Image(
    #                         plot_subcortical_AI(subject,session,bids_dir,ref_region,qc_dir,pvc_method,trc),
    #                         label=f"Subcortical {trc} SUVR AI"
    #                     ),       
    #                 ]

    #         view = rc.Block(
    #             rc.Heading(label="Standard Uptake Value Ratio (SUVR)"),
                
    #             rc.Select(
    #                 blocks=SUVR_blocks
    #             ),

    #             rc.Heading(label="Asymmetry Index (AI)"), 
    #                     # rc.Heading(label="(BLUE = Left < Right; RED = Right < Left)",level=3),
                
    #             rc.Select(
    #                 blocks=AI_blocks
    #             ),
    #             rc.Group(
    #                 rc.Metric(
    #                     heading="Asymmetry Index interpretation",
    #                     value="BLUE = Left < Right; RED = Right < Left",
    #                     label="AI = (L - R) / (0.5 * (L + R))"
    #                 ),
    #             ),
                
    #             rc.Heading(label=f"{trc} PET Z score thresholded at |Z| > 1.96"), 
                
    #             rc.Select(
    #                 blocks=[
    #                     rc.Image(
    #                         plot_Zscore(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region,trc),
    #                         label=f"{trc} PET Z score",
    #                         extra_css="width: 900px; height: auto;"
    #                     ),
    #                 ]
    #             ),
    #             rc.Select(
    #                 blocks=[
    #                     rc.DataTable(
    #                         parcel_stats(subject,session,bids_dir,subj_dir,qc_dir,space,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label="Regional SUVR and Asymmetry Index Statistics",
    #                         index=False
    #                     )
    #                 ]
    #             ), 
    #             rc.Select(
    #                 blocks=[
    #                     rc.Image(
    #                         f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_SUVR_mosaic_screenshot.png",
    #                         label="PET-MRI Overlay",
    #                         extra_css="width: 1300px; height: auto;"
    #                     ),
    #                 ]
    #             )
    #         )

    # else: 
    #     with rc.ReportCreator(
    #         title="MICA-PET Report",
    #         description=f"**Subject**: {subject} | **Session**: {session} | **Modality**: {trc} PET | **Ref region**: {ref_region} | **PVC method**: {pvc_method}",
    #         footer="Multimodal Imaging and Connectome Analysis (MICA) Lab - McGill University. For research use only.",
    #         logo=f"https://box.bic.mni.mcgill.ca/s/GbLcj26GmYWBfLL/download"
    #     ) as report:
            
    #         if hippocampal:
    #             SUVR_blocks = [
    #                     rc.Image(
    #                         cortical_SUVR,
    #                         label=f"Cortical {trc} SUVR",
    #                         extra_css="width: 900px; height: auto;",
    #                     ),
    #                     rc.Image(
    #                         plot_subcort(subject,session,bids_dir,qc_dir,ref_region,max_value,pvc_method,trc),
    #                         label=f"Subcortical {trc} SUVR",
    #                         extra_css="width: 900px; height: auto;",
    #                     ),
    #                     rc.Image(
    #                         plot_hippunfold(subject,session,bids_dir,qc_dir,max_value,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label=f"Hippocampal {trc} SUVR",
    #                         extra_css="width: 450px; height: auto;",
    #                     ) 
    #                 ]
    #             AI_blocks = [
    #                     # The `rc.Image()` blocks in the code are creating images to be displayed in the report.
    #                     # Each `rc.Image()` block specifies the path to an image file and provides a label for
    #                     # that image.
    #                     rc.Image(
    #                         plot_AI(subject,session,bids_dir,qc_dir, pial_left, pial_right,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label=f"Cortical {trc} SUVR AI"
    #                     ),
    #                     rc.Image(
    #                         plot_subcortical_AI(subject,session,bids_dir,ref_region,qc_dir,pvc_method,trc),
    #                         label=f"Subcortical {trc} SUVR AI"
    #                     ),
    #                     rc.Image(
    #                         plot_hippunfold_AI(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label=f"Hippocampal {trc} SUVR AI",
    #                     ),
                        
    #                 ]
    #         else:
    #             SUVR_blocks = [
    #                     rc.Image(
    #                         cortical_SUVR,
    #                         label=f"Cortical {trc} SUVR",
    #                         extra_css="width: 900px; height: auto;",
    #                     ),
    #                     rc.Image(
    #                         plot_subcort(subject,session,bids_dir,qc_dir,ref_region,max_value,pvc_method,trc),
    #                         label=f"Subcortical {trc} SUVR",
    #                         extra_css="width: 900px; height: auto;",
    #                     )
    #                 ]
    #             AI_blocks = [
    #                     # The `rc.Image()` blocks in the code are creating images to be displayed in the report.
    #                     # Each `rc.Image()` block specifies the path to an image file and provides a label for
    #                     # that image.
    #                     rc.Image(
    #                         plot_AI(subject,session,bids_dir,qc_dir, pial_left, pial_right,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label=f"Cortical {trc} SUVR AI"
    #                     ),
    #                     rc.Image(
    #                         plot_subcortical_AI(subject,session,bids_dir,ref_region,qc_dir,pvc_method,trc),
    #                         label=f"Subcortical {trc} SUVR AI"
    #                     ),       
    #                 ]

    #         view = rc.Block(
    #             rc.Heading(label="Standard Uptake Value Ratio (SUVR)"),
                
    #             rc.Select(
    #                 blocks=SUVR_blocks
    #             ),

    #             rc.Heading(label="Asymmetry Index (AI)"), 
    #                     # rc.Heading(label="(BLUE = Left < Right; RED = Right < Left)",level=3),
                
    #             rc.Select(
    #                 blocks=AI_blocks
    #             ),
    #             rc.Group(
    #                 rc.Metric(
    #                     heading="Asymmetry Index interpretation",
    #                     value="BLUE = Left < Right; RED = Right < Left",
    #                     label="AI = (L - R) / (0.5 * (L + R))"
    #                 ),
    #             ),
                
    #             rc.Select(
    #                 blocks=[
    #                     rc.DataTable(
    #                         parcel_stats(subject,session,bids_dir,subj_dir,qc_dir,space,mica_pet_derivatives,ref_region,trc,pvc_method),
    #                         label="Regional SUVR and Asymmetry Index Statistics",
    #                         index=False
    #                     )
    #                 ]
    #             ), 
    #             rc.Select(
    #                 blocks=[
    #                     rc.Image(
    #                         f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_SUVR_mosaic_screenshot.png",
    #                         label="PET-MRI Overlay",
    #                         extra_css="width: 1300px; height: auto;"
    #                     ),
    #                 ]
    #             )
    #         )

    # report.save(view, f"{qc_dir}/sub-{subject}_ses-{session}_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_report.html")

    rc(f"{bids_dir}",subject=f"sub-{subject}",session=f"ses-{session}",pvc=f"{pvc_method}",ref=f"{ref_region}")

    # Clean up display
    # Close all matplotlib figures and force-GC VTK render window objects so
    # their X connections are dropped before Xvfb is killed.  Without this,
    # display.stop() triggers a fatal XIO error from VTK; without stop() at all
    # the Xvfb process leaks and accumulates across runs.
    if display_flag:
        pltl.close('all')
        gc.collect()
        # display.stop()

    # remove derivatives tmp directory
    derivatives_tmp_files = f"{bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}/sub-{subject}/ses-{session}/tmp"
    utils.cleanup_tmp(derivatives_tmp_files)

    utils.print_time_stamp("Report completed.")

if __name__ == "__main__":
    """
        MICA-PET v0.6.7 for volumetric and surface based analysis of static PET imaging.

        Mandatory parameters:
        -----------------------------
            -subject        : Subject identification. (eg. PX001)
            -session        : Session. (eg. 01)
            -trc            : Tracer (eg. FDG, MK6240)
            -bids_dir       : Path to BIDS directory ( . or FULL PATH)
            -pvc_method     : PVC method used for PET image. Options: 'RBV-FS','MG-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'.
            -ref_region     : Reference regions to use for projection. eg. 'pons','cerebellarGM','cerebellum','composite','WM','GM'. Default: 'pons'.
            -psf            : Scanner PSF FWHM in mm (eg. 4.5).
            -fastsurfer_img : Path to FastSurfer .sif image.
            -hippunfold_img : Path to hippocampal unfold .sif image.
            
            -fs_license : Path to FreeSurfer license. (eg. license.txt) 
            
        Optional parameters:
        ----------------------------
            -subj_dir       : Specify path to FreeSurfer/FastSurfer subjects directory.
            -existing-freesurfer-dir : Path to existing FreeSurfer subject outputs directory (ex. /path/to/freesurfer/sub-01_ses-01). If provided, will create symlinks instead of running FastSurfer.
            -existing-hippunfold-dir : Path to existing HippUnfold subject outputs directory (ex. /path/to/hippunfold_v1.4.1/hippunfold/sub-01/ses-01). If provided, will create symlinks instead of running HippUnfold.
            -hippunfold-cache-dir : Path to hippunfold cache directory.
            -skip-hippunfold : Flag to skip HippUnfold processing. If set, will not run HippUnfold and will not require HippUnfold outputs.
            -edge-reg       : Flag to use edge-based registration method for PET to T1w registration rather than FreeSurfer mri_coreg.
            -nonlinear-coreg : Flag to perform nonlinear co-registration to MNI space. If set, will run lamareg nonlinear registration. 
            -smoothing      : (List of float) List of smoothing FWHM in mm for surface projection. eg. '-smoothing 5 10'. Default: 0 (no smoothing).
            -threads        : Number of threads to use (default 8)
            -force          : Force FastSurfer even if output exists.
            -tmpdir         : Path to temporary directory.

        Optional PETPVC parameters:
        -----------------------------
            -pvc_mask       : Optional custom mask to use for PETPVC. Must be a 4D NIfTI with one ROI per frame. Sum across timeframes must be 1 at each voxel. Must be in FreeSurfer/FastSurfer space (eg. orig.mgz). If not provided, a two tissue mask will be generated for MG PVC and a GM+WM+CSF+background mask will be generated for all others.
            -pvc-iterations : Number of iterations for iterative PVC methods (default 50).
            -pvc-n_iter     : Number of iterations for iterative PVC methods (IY) (default: 10).
            -pvc-n_deconv   : Number of iterations for deconvolution PVC methods (RL, VC) (default: 10).

        The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
        It is part of a larger pipeline for processing and analyzing neuroimaging data.
        This script is licensed under the MIT License. See the LICENSE file for details.
        Copyright (c) 2026 MICA-MNI
    """
    import argparse
    import os
    import glob
    import utils
    from utils import bcolors

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("-subject", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
    parser.add_argument("-session", type=str, required=True, help="(Str) Session (eg. '01')")
    parser.add_argument("-trc", dest="trc", type=str, required=True, help="Tracer (eg. FDG, MK6240).")
    parser.add_argument("-bids_dir", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
    parser.add_argument("-pvc_method", dest="pvc_method", required=True, type=str, default='RBV-FS', choices=['RBV-FS','MG-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'], help="(Str) PVC method used for PET image. Options: 'RBV-FS', 'MG','IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL' etc. Default: 'RBV-FS'.")
    parser.add_argument("-ref_region",dest="ref_region", type=str, default='pons',help="Specify reference region. Default: pons.")
    parser.add_argument("-smoothing", dest="smoothing", type=float, nargs='*', default=0, help="(List of float) List of smoothing FWHM in mm for surface projection. eg. '-smoothing 5 10'. Default: 0 (no smoothing).")
    parser.add_argument("-psf", dest="psf", type=float, required=True, help="Scanner PSF in mm. Ask your PET physicist if unknown.", default=4.5)
    parser.add_argument("-fastsurfer_img", dest="fastsurfer_img", type=str, help="(Str) Specify path to FastSurfer singularity image.")
    parser.add_argument("-fs_license", dest="fs_license", type=str, required=True, help="(Str) Specify path to FreeSurfer license.")
    parser.add_argument("-hippunfold_img", dest="hippunfold_img", type=str, help="(Str) Specify path to HippUnfold singularity image.")
    parser.add_argument("-existing-freesurfer-dir", dest="existing_freesurfer_dir", type=str, help="(Str) Specify path to existing FreeSurfer subject outputs directory (ex. /path/to/freesurfer/sub-01_ses-01). If provided, will create symlinks instead of running FastSurfer.")
    parser.add_argument("-existing-hippunfold-dir", dest="existing_hippunfold_dir", type=str, help="(Str) Specify path to existing HippUnfold subject outputs directory (ex. /path/to/hippunfold_v1.4.1/hippunfold/sub-01/ses-01). If provided, will create symlinks instead of running FastSurfer.")
    parser.add_argument("-hippunfold-cache-dir", dest="hippunfold_cache_dir", type=str, help="(Str) Specify path to hippunfold cache directory.")
    parser.add_argument("-skip-hippunfold", dest="skip_hippunfold", action='store_true', help="(Flag) Skip HippUnfold processing. If set, will not run HippUnfold and will not require HippUnfold outputs.")
    parser.add_argument("-edge-reg", dest="edge_reg", action='store_true', help="(Flag) Use edge-based registration method for PET to T1w registration rather than FreeSurfer mri_coreg.")
    parser.add_argument("-nonlinear-coreg", dest="nonlinear_coreg", action='store_true', help="(Flag) Perform nonlinear co-registration to MNI space. If set, will run lamareg nonlinear registration.")
    parser.add_argument("-threads", dest="threads", type=int, default=8, help="(Int) Number of threads to use (default 8).")
    parser.add_argument("-force", dest="force", action='store_true', help="(Flag) Force FastSurfer even if output exists.")
    parser.add_argument("-tmpdir", dest="tmpdir", type=str, help="(Str) Path to temporary directory.")
    parser.add_argument("-pvc_mask", dest="pvc_mask", type=str, help="(Str) Optional custom mask to use for PETPVC. Must be a 4D NIfTI with one ROI per frame. Sum across timeframes must be 1 at each voxel. Must be in FreeSurfer/FastSurfer space (eg. orig.mgz).If not provided, a two tissue mask will be generated for MG PVC and a GM+WM+CSF+background mask will be generated for all others.")
    parser.add_argument("-pvc_dir", dest="pvc_dir", type=str, help="(Str) Specify PETSurfer PVC output directory. (Default {subj_dir}/sub-{subject}_ses-{session}/gtmpvc.output)")
    parser.add_argument("-pvc_n_iter", dest="pvc_n_iter", type=int, default=10, help="(Int) Number of iterations for iterative PVC methods (IY). Default: 10.")
    parser.add_argument("-pvc_n_deconv", dest="pvc_n_deconv", type=int, default=10, help="(Int) Number of iterations for deconvolution PVC methods (RL, VC). Default: 10.")
    parser.add_argument("-output_dir", dest="output_dir", type=str, help="(Str) Specify output directory for MICA-PET derivatives. Default: {bids_dir}/derivatives/MICA-PET_{version}")
    args = parser.parse_args()


    # PIPELINE START
    print(f"\n{bcolors.RED}Starting MICA-PET {utils.MICA_PET_VERSION} pipeline for subject {args.subject}, session {args.session}, tracer {args.trc}...{bcolors.RESET}\n")

    # variables set up
    mica_pet_derivatives = f"{args.bids_dir}/derivatives/MICA-PET_{utils.MICA_PET_VERSION}"
    os.makedirs(mica_pet_derivatives, exist_ok=True)
    subj_dir = os.path.join(args.bids_dir, "derivatives", "fastsurfer")
    f_surf_dir = os.path.join(subj_dir, f"sub-{args.subject}_ses-{args.session}")

    # tmpdir 
    if args.tmpdir is None:
        tmpdir = os.path.join(mica_pet_derivatives,f"sub-{args.subject}",f"ses-{args.session}", "tmp")
        os.makedirs(tmpdir, exist_ok=True)
    else:
        tmpdir = args.tmpdir
        os.makedirs(tmpdir, exist_ok=True)


    ## FASTSURFER
    if args.existing_freesurfer_dir:
        if os.path.exists(f_surf_dir):
            # subject directory already exists in SUBJECTS_DIR
            print(f"Warning: Subject FreeSurfer/FastSurfer directory '{subj_dir}/sub-{args.subject}_ses-{args.session}' already exists. Skipping symlink creation.")
        elif not os.path.exists(args.existing_freesurfer_dir):
            # existing freesurfer dir not found
            raise FileNotFoundError(f"Existing FreeSurfer directory '{args.existing_freesurfer_dir}' does not exist.")
        else:
            target = subj_dir  # The target path for the symlink
            print(f"Setting up symlink from {args.existing_freesurfer_dir} to {f_surf_dir}")
            os.symlink(args.existing_freesurfer_dir, subj_dir, target_is_directory=True)
            
    else: 
        # Run FastSurfer

        # Check if fastsurfer img & license exist
        if not os.path.exists(args.fastsurfer_img) or not os.path.exists(args.fs_license):
            raise FileNotFoundError(f"FastSurfer image '{args.fastsurfer_img}' or FreeSurfer license '{args.fs_license}' does not exist.")
        
        fastsurfer(
            subject=args.subject,
            session=args.session,
            bids_dir=args.bids_dir,
            subj_dir=subj_dir,
            fastsurfer_img=args.fastsurfer_img,
            fs_license=args.fs_license,
            threads=args.threads,
            tmpdir=tmpdir,
            force=args.force
        )

    ## HIPPUNFOLD
    if args.skip_hippunfold:
        hippunfold_dir = None
        hippocampal = False
    else:
        hippunfold_dir = f"{args.bids_dir}/derivatives/hippunfold_v1.4.1/hippunfold"
        hippocampal = True
    
    if args.existing_hippunfold_dir:
        if os.path.exists(f"{hippunfold_dir}/sub-{args.subject}/ses-{args.session}"):
            # subject directory already exists in SUBJECTS_DIR
            print(f"Warning: Subject HippUnfold directory {hippunfold_dir}/sub-{args.subject}/ses-{args.session} already exists. Skipping symlink creation.")
        elif not os.path.exists(args.existing_hippunfold_dir):
            # existing hippunfold dir not found
            raise FileNotFoundError(f"Existing HippUnfold directory '{args.existing_hippunfold_dir}' does not exist.")
        else:
            target = f"{hippunfold_dir}/sub-{args.subject}/ses-{args.session}"  # The target path for the symlink
            print(f"Setting up symlink from {args.existing_hippunfold_dir} to {hippunfold_dir}/sub-{args.subject}/ses-{args.session}")
            os.symlink(args.existing_hippunfold_dir, f"{hippunfold_dir}/sub-{args.subject}/ses-{args.session}", target_is_directory=True)
    else: 
        if not args.skip_hippunfold:
            # Run HippUnfold

            # Check if hippunfold img exists
            if not os.path.exists(args.hippunfold_img):
                raise FileNotFoundError(f"HippUnfold image {args.hippunfold_img} does not exist.")
            hippunfold(
                subject=args.subject,
                session=args.session,
                bids_dir=args.bids_dir,
                hippunfold_img=args.hippunfold_img,
                hippunfold_dir=f"{args.bids_dir}/derivatives/hippunfold_v1.4.1",
                tmpdir=tmpdir,
                cachedir=args.hippunfold_cache_dir,
                threads=args.threads,
                force=args.force
            )
    
    # LINEAR COREG
    linear_coreg(
        subject=args.subject,
        session=args.session,
        trc=args.trc,
        bids_dir=args.bids_dir,
        subj_dir=subj_dir,
        edge_reg=args.edge_reg
    )

    # CORTICAL SURFACE
    cortical_surface(
        subject=args.subject,
        session=args.session,
        bids_dir=args.bids_dir,
        subj_dir=subj_dir
    )

    # NONLINEAR COREG
    if args.nonlinear_coreg:
        nonlinear_coreg(
            subject=args.subject,
            session=args.session,
            trc=args.trc,
            bids_dir=args.bids_dir,
            pvc_method=args.pvc_method,
            ref_region=args.ref_region
        )

    # GTMSEG
    gtm_seg(
        subject=args.subject,
        session=args.session,
        trc=args.trc,
        bids_dir=args.bids_dir,
        subj_dir=subj_dir,
        threads=args.threads
    )

    # PVC
    pvc(
        subject=args.subject,
        session=args.session,
        trc=args.trc,
        bids_dir=args.bids_dir,
        subj_dir=subj_dir,
        pvc_method=args.pvc_method,
        psf=args.psf,
        pvc_mask=args.pvc_mask,
        pvc_dir=args.pvc_dir,
        pvc_n_iter=args.pvc_n_iter,
        pvc_n_deconv=args.pvc_n_deconv
    )

    # SUVR
    suvr(
        subject=args.subject,
        session=args.session,
        trc=args.trc,
        bids_dir=args.bids_dir,
        subj_dir=subj_dir,
        pvc_method=args.pvc_method,
        ref_region=args.ref_region
    )

    # PROJECT PET DATA
    project_pet_data(
        subject=args.subject,
        session=args.session,
        trc=args.trc,
        bids_dir=args.bids_dir,
        subj_dir=subj_dir,
        pvc_method=args.pvc_method,
        ref_region=args.ref_region,
        tmpdir=tmpdir,
        hippunfold_dir=f"{args.bids_dir}/derivatives/hippunfold_v1.4.1",
        cortical=True,
        hippocampal=hippocampal,
        smoothing=args.smoothing
    )

    # SUBCORTICAL MAP
    subcortical_map(
        subject=args.subject,
        session=args.session,
        trc=args.trc,
        bids_dir=args.bids_dir,
        subj_dir=subj_dir,
        pvc_method=args.pvc_method,
        ref_region=args.ref_region
    )

    # REPORT
    report(
        subject=args.subject,
        session=args.session,
        trc=args.trc,
        bids_dir=args.bids_dir,
        subj_dir=subj_dir,
        pvc_method=args.pvc_method,
        ref_region=args.ref_region,
        hippocampal=hippocampal
    )

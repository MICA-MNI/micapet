#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for linear co-registration of PET to MRI.
The script requires the following arguments:
    -trc        : Tracer (eg. FDG, MK6240)
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -subj_dir : Specify path to FreeSurfer/FastSurfer subjects directory. (Default fastsurfer subdirectory in BIDS derivatives directory.)
    -pvc_method : PVC method used for PET image. Options: 'rbv', 'MG'. Default: 'rbv'.
    -pet        : (Optional) Specify path to PET nifti file. Default: sub-<sub>_ses-<ses>_trc-<trc>_pet.nii.gz in pet BIDS directory.
    -mri        : (Optional) Specify path to MRI nifti file. Default: sub-<sub>_ses-<ses>_T1w.nii.gz in anat BIDS directory.
    -out        : (Optional) Output directory. Default: BIDS directory.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import shutil
import sys
from datetime import datetime
import ants
import subprocess
# from nipype.interfaces.freesurfer import FSCommand
from nipype.interfaces.freesurfer import MRICoreg, ApplyVolTransform, FSCommand, MRIConvert
from nipype.interfaces import afni


# Load utilities functions from utils.py
import utils

# Set the working directory to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)

# Argument Parsing
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("-trc", type=str, dest='trc', default='FDG',choices=['FDG','MK6240'],help="(Str) Select tracer for analysis ('FDG','MK6240'). (Default 'FDG').")
parser.add_argument("-pvc_method", dest="pvc_method", type=str, default='rbv', choices=['rbv', 'MG','IY'], help="(Str) PVC method used for PET image. Options: 'rbv', 'MG', 'IY'. Default: 'rbv'.")
parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
parser.add_argument("-subj_dir", dest="subj_dir", type=str, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-pet", dest="pet", type=str, help="(Str) Path to PET nifti file. Default: sub-<sub>_ses-<ses>_trc-<trc>_pet.nii.gz in pet BIDS directory.")
parser.add_argument("-mri", dest="mri", type=str, help="(Str) Path to MRI nifti file. Default: sub-<sub>_ses-<ses>_T1w.nii.gz in mri BIDS directory.")
parser.add_argument("-output_dir", dest="output_dir", type=str, help="(Str) Specify output directory for MICA-PET derivatives. Default: {bids_dir}/derivatives/MICA-PET_{version}")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
    sys.exit(1)
    
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
        print("ERROR: FastSurfer directory does not exist. Please enter a valid -subj_dir.")
        sys.exit(1)
else:
    subj_dir = os.path.realpath(args.subj_dir)
    if not os.path.exists(subj_dir):
        print("ERROR: FreeSurfer/FastSurfer directory does not exist. Please enter a valid -subj_dir.")
        sys.exit(1)

mica_pet_version = os.environ['MICA_PET_VERSION']
# Support custom output_dir or default to bids_dir/derivatives
if args.output_dir is not None:
    mica_pet_derivatives = os.path.join(os.path.realpath(args.output_dir), f"MICA-PET_{mica_pet_version}")
else:
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"
    
pet = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_pet.nii.gz"
transmission = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_desc-transmission_pet.nii.gz"
mri = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"

# Create BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}")
    os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat")
    os.makedirs(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet")
if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}"):
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}")
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat")
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet")
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf")
    os.makedirs(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm")

# Check and copy PET and MRI files if provided
if args.pet == None:
    if not os.path.exists(pet):
        print("Error: PET file not found in the default location. Please provide the path using -pet argument.")
        sys.exit(1)
else:
    if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_pet.nii.gz"):
        shutil.copyfile(os.path.realpath(args.pet), pet)

if args.mri == None:
    if not os.path.exists(mri):
        print("Error: MRI file not found in the default location. Please provide the path using -mri argument.")
        sys.exit(1)
else:
    if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"):
        shutil.copyfile(os.path.realpath(args.mri), mri)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting PET to MRI co-registration for subject: {subject}, session: {session}.")

# 3d resample MRI to nativepro space
resample = afni.Resample()
resample.inputs.in_file = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
resample.inputs.orientation= 'LPI'
resample.inputs.outputtype = 'NIFTI_GZ'
resample.out_file = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
res = resample.run()

## MRICoreg
FSCommand.set_default_subjects_dir(subj_dir)
def mricoreg(pet,subject,session,subj_dir,mica_pet_derivatives,space,trc):
    print(f"Co-registering PET to {space}...")
    coreg = MRICoreg()
    coreg.inputs.source_file=pet
    if space == 'T1wFS': # use FreeSurfer mgz as reference
        coreg.inputs.subjects_dir=subj_dir
        coreg.inputs.subject_id=f"sub-{subject}_ses-{session}"
    else: # use rawdata mri
        coreg.inputs.reference_file=f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}__space-nativepro_T1w.nii.gz"
    coreg.inputs.out_lta_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-{space}_xfm.reg.lta'
    print(coreg.cmdline)
    coreg.run()
    
    applyreg = ApplyVolTransform()
    applyreg.inputs.source_file=pet
    applyreg.inputs.reg_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-{space}_xfm.reg.lta'
    if space == 'T1wFS':
        applyreg.inputs.fs_target=True
    else:
        applyreg.inputs.target_file=f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
    applyreg.inputs.transformed_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-none_trc-{trc}_pet.nii.gz'
    applyreg.run()

## ANTS

def ANTS_reg(transmission,pet,subject,session,subj_dir,mica_pet_derivatives,space,trc):
    if space == 'T1wFS': # use FreeSurfer mgz as reference
        mri = f"{subj_dir}/sub-{subject}_ses-{session}/mri/orig.nii.gz"
        if not os.path.exists(mri):
            mc = MRIConvert()
            mc.inputs.in_file = f"{subj_dir}/sub-{subject}_ses-{session}/mri/orig.mgz"
            mc.inputs.out_file = mri
            mc.inputs.out_type = 'niigz'
            mc.run()
    else: # use rawdata mri
        mri = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
        
    fixed = ants.image_read(mri)
    moving = ants.image_read(pet)
    if trc == 'MK6240':
        moving_transmission = ants.image_read(transmission)
    else:
        moving_transmission = moving
    
    mytx = ants.registration(
        fixed=fixed,
        moving=moving_transmission,
        type_of_transform='Rigid',
        outprefix=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from-pet_to-{space}_'
    )

    pet_in_mri = ants.apply_transforms(
        fixed=fixed, 
        moving=moving,
        transformlist=mytx['fwdtransforms'],
        interpolator='linear')

    ants.image_write(pet_in_mri, f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-none_trc-{trc}_pet.nii.gz')

    # os.environ["PATH"] += os.pathsep + '/opt/ants/bin'
    # FSCommand.set_default_subjects_dir(args.subj_dir)

    # # convert ANTS mat to ITK txt
    # ants_mat = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from-pet_to-T1w_0GenericAffine.mat'
    # itk_txt = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from_pet_to-T1w_xfm.txt'
    # out_lta = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-FDG_pet_to-T1w_xfm.reg.lta'
    # subprocess.call(['ConvertTransformFile', '3', 
    #     ants_mat,
    #     itk_txt])

    # convert ITK txt to FreeSurfer LTA
    # subprocess.call(['lta_convert',
    #     '--initk',itk_txt,
    #     '--outlta',out_lta,
    #     '--src',pet,
    #     '--trg',mri,
    #     '--subject',f"sub-{subject}_ses-{session}",
    #     '--ltavox2vox']) 


for space in ['T1wFS','T1wNativepro']:
    if pvc_method == 'rbv':
        mricoreg(pet,subject,session,subj_dir,mica_pet_derivatives,space,trc)
    else: 
        ANTS_reg(transmission,pet,subject,session,subj_dir,mica_pet_derivatives,space,trc)



print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] PET to MRI co-registration completed.")

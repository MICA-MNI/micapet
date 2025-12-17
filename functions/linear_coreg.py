#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for linear co-registration of PET to MRI.
The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -subj_dir : Specify path to FreeSurfer/FastSurfer subjects directory. (Default fastsurfer subdirectory in BIDS derivatives directory.)
    -pet        : (Optional) Specify path to PET nifti file. Default: sub-<sub>_ses-<ses>_trc-FDG_pet.nii.gz in pet BIDS directory.
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
from nipype.interfaces.freesurfer import MRICoreg, ApplyVolTransform, FSCommand

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
parser.add_argument("-subj_dir", dest="subj_dir", type=str, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-pet", dest="pet", type=str, help="(Str) Path to PET nifti file. Default: sub-<sub>_ses-<ses>_trc-FDG_pet.nii.gz in pet BIDS directory.")
parser.add_argument("-mri", dest="mri", type=str, help="(Str) Path to MRI nifti file. Default: sub-<sub>_ses-<ses>_T1w.nii.gz in mri BIDS directory.")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir]):
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
        print("ERROR: FastSurfer directory does not exist. Please enter a valid -subj_dir.")
        sys.exit(1)
else:
    subj_dir = os.path.realpath(args.subj_dir)
    if not os.path.exists(subj_dir):
        print("ERROR: FreeSurfer/FastSurfer directory does not exist. Please enter a valid -subj_dir.")
        sys.exit(1)

mica_pet_version = os.environ['MICA_PET_VERSION']
mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"
space = os.environ['PET_SPACE']

pet = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet.nii.gz"
if space == 'nativepro':
    mri = f"{subj_dir}/sub-{subject}_ses-{session}/mri/orig.mgz"
else:
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
    if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet.nii.gz"):
        shutil.copyfile(os.path.realpath(args.pet), pet)

if args.mri == None:
    if not os.path.exists(mri):
        print("Error: MRI file not found in the default location. Please provide the path using -mri argument.")
        sys.exit(1)
else:
    if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"):
        shutil.copyfile(os.path.realpath(args.mri), mri)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting PET to MRI co-registration for subject: {subject}, session: {session}.")

## ANTS
# fixed = ants.image_read(mri)
# moving = ants.image_read(pet)

# mytx = ants.registration(
#     fixed=fixed,
#     moving=moving,
#     type_of_transform='Rigid',
#     outprefix=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from-pet_to-T1w_'
# )

# pet_in_mri = ants.apply_transforms(
#     fixed=fixed, 
#     moving=moving,
#     transformlist=mytx['fwdtransforms'],
#     interpolator='linear')

# ants.image_write(pet_in_mri, f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-none_trc-FDG_pet.nii.gz')

# os.environ["PATH"] += os.pathsep + '/opt/ants/bin'
# FSCommand.set_default_subjects_dir(args.subj_dir)

# # # convert ANTS mat to ITK txt
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

## MRICoreg

FSCommand.set_default_subjects_dir(subj_dir)
def mricoreg(pet,subject,session,subj_dir,mica_pet_derivatives,space,ref_image):
    print(f"Co-registering PET to {ref_image} image...")
    coreg = MRICoreg()
    coreg.inputs.source_file=pet
    if ref_image == 'FS': # use FreeSurfer mgz as reference
        coreg.inputs.subjects_dir=subj_dir
        coreg.inputs.subject_id=f"sub-{subject}_ses-{session}"
    else: # use rawdata mri
        coreg.inputs.reference_file=f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
    coreg.inputs.out_lta_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from-pet_to-{space}_xfm.reg.lta'
    print(coreg.cmdline)
    coreg.run()

def apply_transform(pet,subject,session,mica_pet_derivatives,space,ref_image):
    applyreg = ApplyVolTransform()
    applyreg.inputs.source_file=pet
    applyreg.inputs.reg_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from-pet_to-{space}_xfm.reg.lta'
    if ref_image == 'FS':
        applyreg.inputs.fs_target=True
    else:
        applyreg.inputs.target_file=f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
    applyreg.inputs.transformed_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-none_trc-FDG_pet.nii.gz'
    applyreg.run()
    
if space == 'nativepro':
    # nativepro
    mricoreg(pet,subject,session,subj_dir,mica_pet_derivatives,'nativepro','FS')
    apply_transform(pet,subject,session,mica_pet_derivatives,'nativepro','FS')
    
    # T1w
    mricoreg(pet,subject,session,subj_dir,mica_pet_derivatives,'T1w','T1w')
    apply_transform(pet,subject,session,mica_pet_derivatives,'T1w','T1w')
    
else:
    mricoreg(pet,subject,session,subj_dir,mica_pet_derivatives,space,'T1w')
    apply_transform(pet,subject,session,mica_pet_derivatives,space,'T1w')

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] PET to MRI co-registration completed.")

## Nipype implementation (commented out)
# reg = RegistrationSynQuick()
# reg.inputs.fixed_image = mri
# reg.inputs.moving_image = pet
# reg.inputs.dimension = 3
# reg.inputs.transform_type = 'r'  # rigid
# reg.inputs.output_prefix = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet_to-T1w_'
# reg.inputs.num_threads = 6
# print(reg.cmdline)

# reg.run()

# at = ApplyTransforms()
# at.inputs.input_image = pet
# at.inputs.reference_image = mri
# at.inputs.transforms = [f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-FDG_pet_to-T1w_0GenericAffine.mat']
# at.inputs.dimension = 3
# at.inputs.interpolation = 'NearestNeighbor'
# at.inputs.num_threads = 6
# at.inputs.output_image = f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_trc-FDG_pet.nii.gz'
# print(at.cmdline)

# at.run()
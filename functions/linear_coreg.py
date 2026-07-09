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
    -pvc_method : PVC method used for PET image. Options: 'RBV-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'. Default: 'RBV-FS'.
    -edge_reg   : Uses edge-based registration method for PET to T1w registration rather than FreeSurfer mri_coreg.
    -pet        : (Optional) Specify path to PET nifti file. Default: sub-<sub>_ses-<ses>_trc-<trc>_pet.nii.gz in pet BIDS directory.
    -mri        : (Optional) Specify path to MRI nifti file. Default: sub-<sub>_ses-<ses>_T1w.nii.gz in anat BIDS directory.
    -out        : (Optional) Output directory. Default: BIDS directory.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import glob
import os
import shutil
import sys
from datetime import datetime
import ants
import numpy as np
import nibabel as nib

# from nipype.interfaces.freesurfer import FSCommand
from nipype.interfaces.freesurfer import MRICoreg, ApplyVolTransform, FSCommand, MRIConvert
from nipype.interfaces.freesurfer.utils import LTAConvert
from nipype.interfaces import afni

# Load utilities functions from utils.py
import utils

# Set the working directory to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)

# Argument Parsing
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("-trc", type=str, dest='trc', default='FDG',help="(Str) Select tracer for analysis ('FDG','MK6240'). (Default 'FDG').")
parser.add_argument("-pvc_method", dest="pvc_method", type=str, default='RBV-FS', choices=['RBV-FS', 'MG', 'IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL'], help="(Str) PVC method used for PET image. Options: 'RBV-FS', 'MG','IY', 'LABBE', 'RL', 'VC', 'RBV', 'LABBE+RBV', 'RBV+VC', 'RBV+RL', 'LABBE+RBV+VC', 'LABBE+RBV+RL', 'MTC', 'LABBE+MTC', 'MTC+VC', 'MTC+RL', 'LABBE+MTC+VC', 'LABBE+MTC+RL', 'IY+VC', 'IY+RL', 'MG+VC', 'MG+RL' etc. Default: 'RBV-FS'.")
parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
parser.add_argument("-subj_dir", dest="subj_dir", type=str, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-edge_reg", dest="edge_reg", action='store_true', help="Use edge-based registration method for PET to T1w registration rather than FreeSurfer mri_coreg.")
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
    
edge_reg = args.edge_reg

pet = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_trc-{trc}_pet.nii.gz"
transmission_list = sorted(glob.glob(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_*transmission*.nii.gz"))
if len(transmission_list) > 1:
    print(f"Warning: Multiple transmission scans found for subject {subject}, session {session}. Using the first one found: {transmission_list[0]}")
transmission = transmission_list[0] if len(transmission_list) > 0 else None
mri = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"

# Create BIDS directory structure
for directory in [
    # f"{bids_dir}/rawdata/sub-{subject}/ses-{session}",
    # f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat",
    # f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/pet",
    f"{mica_pet_derivatives}/sub-{subject}/ses-{session}",
    f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat",
    f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet",
    f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf",
    f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm",
    f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/qc",
]:
    os.makedirs(directory, exist_ok=True)

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
# remove nativepro MRI if present
nativepro_mri = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
if os.path.exists(nativepro_mri):
    print(f"Removing existing nativepro MRI: {nativepro_mri}")
    os.remove(nativepro_mri)
    

os.environ['AFNI_NIFTI_TYPE_WARN'] = "NO"
resample = afni.Resample()
resample.inputs.in_file = f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_T1w.nii.gz"
resample.inputs.orientation= 'LPI'
resample.inputs.outputtype = 'NIFTI_GZ'
resample.inputs.out_file = nativepro_mri
print(f"Resampling T1w MRI to nativepro space: {resample.cmdline}")
resample.run()

# Register T1wFS to nativepro space
print("Registering T1wFS to T1wNativepro")
coreg = MRICoreg()
coreg.inputs.source_file=f"{subj_dir}/sub-{subject}_ses-{session}/mri/orig.mgz"
coreg.inputs.reference_file=nativepro_mri
coreg.inputs.out_lta_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-T1wFS_to-T1wNativepro_xfm.reg.lta'
print(coreg.cmdline)
coreg.run()

## MRICoreg
FSCommand.set_default_subjects_dir(subj_dir)
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
    interpolator    : interpolation for final warp (default "nearestNeighbor")
 
    Returns
    -------
    nib.Nifti1Image  PET resampled into T1w space
    """
 
    # ------------------------------------------------------------------
    # Step 0 – load
    
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
    t1w_nib = nib.load(t1w_path)          # kept only for output header/affine
    pet = ants.image_read(pet_path)
    t1w = ants.image_read(t1w_path)
    output_prefix = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-{space}_"
 
    # ------------------------------------------------------------------
    # Step 1 – smooth  (fslmaths -s sigma)
    pet_smooth = ants.smooth_image(pet, smooth_sigma_mm, sigma_in_physical_coordinates=True)
    t1w_smooth = ants.smooth_image(t1w, smooth_sigma_mm, sigma_in_physical_coordinates=True)
 
    # ------------------------------------------------------------------
    # Step 2 – edge filter  (fslmaths -edge → gradient magnitude)
    def _edge(img):
        d, sp = img.numpy().astype(np.float64), np.array(img.spacing)
        g = [np.gradient(d, sp[i], axis=i) for i in range(3)]
        return img.new_image_like(np.sqrt(sum(gi**2 for gi in g)))
 
    pet_edge = _edge(pet_smooth)
    t1w_edge = _edge(t1w_smooth)
 
    # ------------------------------------------------------------------
    # Step 3 – affine registration on edge images
    # use_legacy_histogram_matching=True mirrors -j 1 in antsRegistrationSyN.sh
    reg = ants.registration(
        fixed             = t1w_edge,
        moving            = pet_edge,
        type_of_transform = "Affine",
        outprefix         = output_prefix,
        use_legacy_histogram_matching = True,
    )
 
    # ------------------------------------------------------------------
    # Step 4 – apply transform to original (unmodified) PET
    pet_warped = ants.apply_transforms(
        fixed         = t1w,
        moving        = pet,
        transformlist = reg["fwdtransforms"],
        interpolator  = interpolator,
    )
    
    # ------------------------------------------------------------------
    # Step 5 – convert .mat to .lta for FreeSurfer compatibility
    # Convert ANTs affine matrix to FreeSurfer LTA format
    tx = ants.read_transform(f"{output_prefix}0GenericAffine.mat")

    ants.write_transform(tx, f"{output_prefix}0GenericAffine.txt")

    lta_convert = LTAConvert()
    lta_convert.inputs.in_itk = f"{output_prefix}0GenericAffine.txt"
    lta_convert.inputs.out_lta = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-{space}_xfm.reg.lta"
    lta_convert.inputs.source_file = pet_path
    lta_convert.inputs.target_file = t1w_path
    lta_convert.cmdline
    lta_convert.run()
    
    # ------------------------------------------------------------------
    # Step 6 – save resampled PET in T1w space
     
    out = nib.Nifti1Image(pet_warped.numpy(), t1w_nib.affine, t1w_nib.header)

    nib.save(out, f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-none_trc-{trc}_pet.nii.gz")


for space in ['T1wFS','T1wNativepro']:
    if edge_reg:
        pet_to_t1w_edge_registration(
            pet_path=pet,
            subject=subject,
            session=session,
            subj_dir=subj_dir,
            mica_pet_derivatives=mica_pet_derivatives,
            space=space,
            trc=trc)
    else:
        mricoreg(transmission,
                 pet,
                 subject,
                 session,
                 subj_dir,
                 mica_pet_derivatives,
                 space,
                 trc)
    
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] PET to MRI co-registration completed.")

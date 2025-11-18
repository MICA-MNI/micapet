#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for converting MRI/PET DICOM data to BIDS compliant nifti format.
It processes MRI/PET images and organizes them into a BIDS-compliant directory structure.
The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -image_type : Type of image to convert (e.g.,   'pet', 'mri'). Default 'pet'.
    -dicom_dir  : Input directory with PET DICOMs.
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -series     : Specify DICOM series number to convert. For PET, select the attenuation corrected image. Default 12.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import glob
import sys
from datetime import datetime
import dcm2niixpy
# from nipype.interfaces.dcm2nii import Dcm2niix

# Load utilities functions from utils.py
# from utils import *

# Set the working directory to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)

# Argument Parsing
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
parser.add_argument("-image_type", type=str, choices=["pet","mri"], default = "pet", help="(Str) Type of image to convert (e.g., 'pet', 'mri'). Default = 'pet'")
parser.add_argument("-dicom_dir", type=str, required=True, help="(Str) DICOM directory")
parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
parser.add_argument("-series", type=int, default=12, help="(Int) Specify DICOM series number to convert (default: 12 for PET attenuation corrected images at McGill)")

args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.dicom_dir, args.bids_dir]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
    sys.exit(1)
    
# Normalize paths and variables
session = f"{args.ses.replace('ses-', '')}"
subject = f"{args.sub.replace('sub-', '')}"
dicom_dir = os.path.realpath(args.dicom_dir)
bids_dir = os.path.realpath(args.bids_dir)
pet_mri = args.image_type.lower()
if pet_mri == "mri":
    pet_mri = "anat"
series = args.series

print(f"Starting DICOM to NIfTI conversion for subject: {subject}, session: {session}, image type: {pet_mri}, series: {series}")

# Create BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/sub-{subject}/ses-{session}"):
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

if pet_mri == "pet":
    dcm2niix.filename = f"sub-{subject}_ses-{session}_trc-FDG_pet"
elif pet_mri == "anat":
    dcm2niix.filename = f"sub-{subject}_ses-{session}_T1w"

dcm2niix.convert(dicom_dir,output_path=f"{bids_dir}/rawdata/sub-{subject}/ses-{session}/{pet_mri}")

print("DICOM to NIfTI conversion completed successfully.")






# # DICOM to NIfTI conversion using nipype Dcm2niix
# converter = Dcm2niix()
# converter.inputs.source_dir = f"{dicom_dir}"
# converter.inputs.output_dir = f"{bids_dir}/sub-{subject}/ses-{session}/{pet_mri}"
# converter.inputs.compress = 'y'
# if pet_mri == "pet":
#     converter.inputs.out_filename = f"sub-{subject}_ses-{session}_trc-FDG_pet_%s"
#     modality = "trc-FDG_pet"
# elif pet_mri == "anat":
#     converter.inputs.out_filename = f"sub-{subject}_ses-{session}_T1w_%s"
#     modality = "T1w"
# # converter.inputs.series_numbers = [str(series)] #doesn't work
# converter.inputs.anon_bids = True

# converter.run()

# def remove_old_files(path):
#     wildcard_pattern = f"{path}_*"
#     for file_path in glob.glob(wildcard_pattern):
#         try:
#             os.remove(file_path)
#         except FileNotFoundError:
#             print(f"File not found: {file_path}")
#         except PermissionError:
#             print(f"Permission denied while deleting {file_path}")
#         except Exception as e:
#             print(f"An error occurred: {e}")

# # Rename files to remove series number from filename
# os.rename(f"{bids_dir}/sub-{subject}/ses-{session}/{pet_mri}/sub-{subject}_ses-{session}_{modality}_{series}.nii.gz",f"{bids_dir}/sub-{subject}/ses-{session}/{pet_mri}/sub-{subject}_ses-{session}_{modality}.nii.gz")
# os.rename(f"{bids_dir}/sub-{subject}/ses-{session}/{pet_mri}/sub-{subject}_ses-{session}_{modality}_{series}.json",f"{bids_dir}/sub-{subject}/ses-{session}/{pet_mri}/sub-{subject}_ses-{session}_{modality}.json")

# remove_old_files(f"{bids_dir}/sub-{subject}/ses-{session}/{pet_mri}/sub-{subject}_ses-{session}_{modality}")

# print("DICOM to NIfTI conversion completed successfully.")


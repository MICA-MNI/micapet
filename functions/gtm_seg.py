#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for geometric transfer matrix segmentation.
FreeSurfer or FastSurfer must have first been completed and segmentations verified.
The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -trc        : Tracer (eg. FDG, MK6240)
    -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory.
    -force      : (Optional) Force gtmseg even if output exists.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import sys
from datetime import datetime
# from nipype.interfaces.freesurfer.petsurfer import GTMSeg
from nipype.interfaces import freesurfer
from nipype.interfaces.freesurfer import MRICoreg, ApplyVolTransform

# Load utilities functions from utils.py
import utils
from workflow.rules.pet import subj_dir

# Set the working directory to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)

# Argument Parsing
parser = argparse.ArgumentParser(add_help=True)
parser.add_argument("-sub", type=str, required=True, help="(Str) Subject identifier (eg. '0001')")
parser.add_argument("-ses", type=str, required=True, help="(Str) Session (eg. '01')")
parser.add_argument("-bids", dest="bids_dir", type=str, required=True, help="(Str) Path to BIDS directory ( . or FULL PATH)")
parser.add_argument("-subj_dir", dest="subj_dir", type=str, required=True, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-output_dir", dest="output_dir", type=str, default=None, help="(Str) Output directory for MICA-PET derivatives. Default: {bids_dir}/derivatives.")
parser.add_argument("-force", action='store_true', help="Force gtmseg even if output exists.")
parser.add_argument("-threads", dest="threads", type=int, default=1, help="(Int) Number of threads to use. Default: 1")
parser.add_argument("-trc", type=str, dest='trc', default='FDG',help="(Str) Select tracer for analysis ('FDG','MK6240'). (Default 'FDG').")
args = parser.parse_args()

# Validate mandatory arguments
if not all([args.sub, args.ses, args.bids_dir, args.subj_dir]):
    print("Error: One or more mandatory arguments are missing.")
    parser.print_help()
    sys.exit(1)
    
# Normalize paths and variables
session = f"{args.ses.replace('ses-', '')}"
subject = f"{args.sub.replace('sub-', '')}"
bids_dir = os.path.realpath(args.bids_dir)
f_surf_dir = f"{os.path.realpath(args.subj_dir)}/sub-{subject}_ses-{session}"
trc = args.trc
force = args.force

# Determine segmentation type   
if os.path.exists(f'{f_surf_dir}/scripts/deep-seg.log'): #deep-seg only exists in fastsurfer
    seg_type = 'fastsurfer'
else:
    seg_type = 'freesurfer'


os.environ['SUBJECTS_DIR'] = os.path.realpath(args.subj_dir)
# Set OpenMP threads for FreeSurfer tools
os.environ['OMP_NUM_THREADS'] = str(args.threads)

mica_pet_version = os.environ['MICA_PET_VERSION']
if args.output_dir is not None:
    mica_pet_derivatives = os.path.join(os.path.realpath(args.output_dir), f"MICA-PET_{mica_pet_version}")
else:
    mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}"):
    print(f"BIDS derivatives directory for subject {subject}, session {session} does not exist. Creating directory structure...")
    # Create BIDS directory structure
    for directory in [
        f"{mica_pet_derivatives}/sub-{subject}/ses-{session}",
        f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat",
        f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/pet",
        f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf",
        f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm",
        f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/qc",
    ]:
        os.makedirs(directory, exist_ok=True)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting gtmseg for subject: {subject}, session: {session}.")

# check seg type
if seg_type == 'freesurfer':
    # check if gtmseg was run already
    if os.path.exists(f"{f_surf_dir}/mri/gtmseg.mgz") and force==False:
        print(f"GTMseg was run already for subject {subject}. Re-run with -force flag to rerun GTMseg.")
        
    else:
        gtmseg = freesurfer.GTMSeg()
        gtmseg.inputs.subject_id = f"sub-{subject}_ses-{session}"
        gtmseg.inputs.ctx_annot = ("aparc.DKTatlas.annot",1000,2000)
        if os.path.exists(f"{f_surf_dir}/mri/apas+head.mgz"):
            gtmseg.inputs.args = "--no-xcerseg"
        else:
            gtmseg.inputs.xcerseg = True
        # Try to set openmp if supported by nipype interface, or rely on OMP_NUM_THREADS
        try:
            gtmseg.inputs.openmp = args.threads
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
            ca_register = freesurfer.CARegister()
            ca_register.inputs.in_file=f"{f_surf_dir}/mri/norm.mgz"
            ca_register.inputs.out_file=f"{f_surf_dir}/mri/transforms/talairach.m3z"
            ca_register.inputs.template=f"{os.environ.get('FREESURFER_HOME')}/average/RB_all_2016-05-10.vc700.gca"
            ca_register.inputs.transform=f"{f_surf_dir}/mri/transforms/talairach.lta"
            ca_register.inputs.mask=f"{f_surf_dir}/mri/brainmask.mgz"
            ca_register.inputs.no_big_ventricles=True
            ca_register.inputs.align='after'

            ca_register.run()

            gtmseg = freesurfer.GTMSeg()
            gtmseg.inputs.subject_id = f"sub-{subject}_ses-{session}"
            gtmseg.inputs.ctx_annot = ("aparc.DKTatlas.annot",1000,2000)
            gtmseg.inputs.xcerseg = True
            # Try to set openmp if supported by nipype interface, or rely on OMP_NUM_THREADS
            try:
                gtmseg.inputs.openmp = args.threads
            except:
                pass
            gtmseg.run()
        else:
            gtmseg = freesurfer.GTMSeg()
            gtmseg.inputs.subject_id = f"sub-{subject}_ses-{session}"
            gtmseg.inputs.ctx_annot = ("aparc.DKTatlas.annot",1000,2000)
            if os.path.exists(f"{f_surf_dir}/mri/apas+head.mgz"):
                gtmseg.inputs.args = "--no-xcerseg"
            else:
                gtmseg.inputs.xcerseg = True
            # Try to set openmp if supported by nipype interface, or rely on OMP_NUM_THREADS
            try:
                gtmseg.inputs.openmp = args.threads
            except:
                pass
                
            print(gtmseg.cmdline)
            gtmseg.run()


# Resample GTMseg to T1w/nativepro space
def resample_gtmseg(gtm,mri,space,trc):
    print(f"Resampling GTMseg to {space} space...")
    applyreg = ApplyVolTransform()
    applyreg.inputs.source_file= gtm
    if space == 'T1wFS':
        applyreg.inputs.reg_header=True
    elif space == 'T1wNativepro':
        applyreg.inputs.reg_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/xfm/sub-{subject}_ses-{session}_from-T1wFS_to-T1wNativepro_xfm.reg.lta'
        
        if not os.path.exists(applyreg.inputs.reg_file):
            # Register T1wFS to nativepro space
            print("Registering T1wFS to T1wNativepro")
            coreg = MRICoreg()
            coreg.inputs.source_file=f"{subj_dir}/sub-{subject}_ses-{session}/mri/orig.mgz"
            coreg.inputs.reference_file=nativepro_mri
            coreg.inputs.out_lta_file=applyreg.inputs.reg_file
            print(coreg.cmdline)
            coreg.run()

    applyreg.inputs.interp = 'nearest'
    applyreg.inputs.target_file= mri
    applyreg.inputs.transformed_file=f'{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-{space}_desc-gtmseg.nii.gz'
    applyreg.run()
    
gtm = f'{f_surf_dir}/mri/gtmseg.mgz'

for space in ['T1wFS','T1wNativepro']:
    if space == 'T1wFS':
        mri = f"{f_surf_dir}/mri/orig.mgz"
    else: 
        mri = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/anat/sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"
    resample_gtmseg(gtm,mri,space,trc)


# resample_gtmseg(gtm,mri,'T1w')
# need to run T1w even if space is nativepro, for hippunfold compatibility

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] GTM segmentation completed.")

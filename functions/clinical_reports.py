#!/usr/bin/env python
# coding: utf-8
"""
This script is part of MICA-PET pipeline for mapping FreeSurfer/FastSurfer cortical surfaces to HCP.
FreeSurfer/FastSurfer must have been run first.

The script requires the following arguments:
    -sub        : Subject identification. (eg. PX001)
    -ses        : Session. (eg. 01)
    -bids       : Path to BIDS directory ( . or FULL PATH)
    -subj_dir   : Specify path to FreeSurfer/FastSurfer subjects directory.
    -ref_region : Reference regions to use. eg. ['pons','cerebellarGM','composite']. Default: ['pons'].
    -trc        : Tracer (eg. FDG, MK6240). Default: 'FDG'.
    -pvc_method : PVC method used for PET image. Options: 'rbv', 'MG'. Default: 'rbv'.
    -max_value  : (Optional) Maximum SUVR value for color scale. Default: 1.5 times the 85th percentile SUVR in the data.

The script is intended for use by researchers and developers working with PET imaging data, particularly in the context of the MICA lab at McGill University.
It is part of a larger pipeline for processing and analyzing neuroimaging data.
This script is licensed under the MIT License. See the LICENSE file for details.
Copyright (c) 2025 MICA-MNI
"""
import argparse
import os
import sys
from datetime import datetime
from nipype.interfaces.freesurfer import FSCommand, MRIConvert
import sys
import numpy as np
import nilearn
from nilearn import plotting
from brainstat.datasets import fetch_mask, fetch_template_surface
from brainspace.plotting import plot_hemispheres
import hippomaps as hm
import matplotlib.pyplot as pltl
import hippomaps as hm
import pandas as pd
from PIL import Image
import report_creator as rc
import nibabel as nib
from nibabel.processing import resample_from_to
import csv
from brainspace.mesh.mesh_io import read_surface
from brainspace.plotting.surface_plotting import plot_surf
from pathlib import Path
from typing import List, Union, Tuple, Literal
PathType = Union[str, os.PathLike]
Analysis = Literal["regional", "asymmetry"]

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
            if verbose:
                print("Warning: pyvirtualdisplay not available, plotting may fail in headless environment")

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
parser.add_argument("-subj_dir", dest="subj_dir", type=str, required=True, help="(Str) Specify path to FreeSurfer/FastSurfer subjects directory.")
parser.add_argument("-ref_region",dest="ref_region", type=str, choices=['pons','cerebellarGM','composite'], default='pons',help="Specify reference region. Default: pons.")
parser.add_argument("-trc", dest="trc", type=str, choices=['FDG','MK6240'], default='FDG', help="Tracer (eg. FDG, MK6240). Default: 'FDG'.")
parser.add_argument("-pvc_method", dest="pvc_method", type=str, choices=['rbv','MG'], default='rbv', help="PVC method used for PET image. Options: 'rbv', 'MG'. Default: 'rbv'.")
parser.add_argument("-max_value", dest="max_value", type=float, help="(Float) Maximum SUVR value for color scale. Default: 1.5 times the maximum SUVR value in the data.")


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
ref_region = args.ref_region
trc = args.trc
pvc_method = args.pvc_method
mica_pet_version = os.environ['MICA_PET_VERSION']
mica_pet_derivatives = f"{bids_dir}/derivatives/MICA-PET_{mica_pet_version}"
space='T1wFS'

if args.max_value is not None:
    max_value = args.max_value
else:
    max_value = None

FSCommand.set_default_subjects_dir(args.subj_dir)

# Check BIDS directory structure if it doesn't exist
if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS rawdata directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
if not os.path.exists(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}"):
    print(f"Error: BIDS derivatives directory for subject {subject}, session {session} does not exist.")
    sys.exit(1)
    
# Check if QC directory made    
qc_dir = f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/qc"
if not os.path.exists(qc_dir):
    print(f"Error: QC directory does not exist at {qc_dir}. Please create it first.")
    sys.exit(1)
    
print(f"Starting clinical report generation for subject: {subject}, session: {session} [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")

filename= f"/host/fladgate/local_raid/jack/FDG/sub-{subject}_ses-{session}_FDG_clinical_report.pdf"

pial_left, pial_right = fetch_template_surface("fslr32k",join=False)
mask = fetch_mask("fslr32k")

sctx_left = read_surface(f"/app/surfaces/sctx.L.surf.gii", itype="gii")
sctx_right = read_surface(f"/app/surfaces/sctx.R.surf.gii", itype="gii")
# sctx_left = read_surface(f"/host/fladgate/local_raid/jack/FDG/MICA-PET/scripts/surfaces/sctx.L.surf.gii", itype="gii")
# sctx_right = read_surface(f"/host/fladgate/local_raid/jack/FDG/MICA-PET/scripts/surfaces/sctx.R.surf.gii", itype="gii")
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
    tmp_pt_FDG_surf_L = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_smooth-10mm_trc-{trc}_pet.func.gii");
    tmp_pt_FDG_surf_R = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_smooth-10mm_trc-{trc}_pet.func.gii");

    to_plot = np.hstack((tmp_pt_FDG_surf_L,tmp_pt_FDG_surf_R))
    to_plot[~mask] = np.nan
    

    if max_value is None:
        max_value = np.percentile(to_plot[mask],85) *1.5
        
    img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_SUVR_clin_report.png"
    plot_hemispheres(pial_left,pial_right,to_plot,color_bar=True, 
                    cmap="jet",color_range=(0,max_value), embed_nb=False,transparent_bg=True,size=(900,200),nan_color=(1,1,1, 1),screenshot=True,filename=img_stream)
    return img_stream, max_value


# Plotting functions ------------------------------------------------------------

def plot_subcort(subject,session,bids_dir,qc_dir,ref_region,max_value,pvc_method,trc):
    # subcort_SUVR = pd.read_csv(f'{bids_dir}/qc/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_subcortical_means_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.csv',header=None).to_numpy()
    # to_plot = subcort_SUVR[1,:]
    
    data_lh, data_rh = _load_data_sctx(
    sctx_file=Path(f'{bids_dir}/qc/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_subcortical_means_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.csv'),
    analysis="regional"
)
    to_plot = np.hstack((data_lh, data_rh))

    img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_SUVR_subcortical_clin_report.png"

    plot_hemispheres(sctx_left,sctx_right,to_plot,color_bar='right', 
        cmap="jet",color_range=(0,max_value), embed_nb=False,transparent_bg=True,size=(900,200),nan_color=(1,1,1, 0),screenshot=True,filename=img_stream)

    return img_stream

def plot_hippunfold(subject,session,bids_dir,qc_dir,max_value,mica_pet_derivatives,ref_region,trc,pvc_method):
    tmp_hcsurf_L = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")

    tmp_hcsurf_R = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")             

    to_plot = np.hstack((np.expand_dims(tmp_hcsurf_L,axis=1),np.expand_dims(tmp_hcsurf_R,axis=1)))

    img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_SUVR_hippunfold_clin_report.png"

    hm.plotting.surfplot_canonical_foldunfold(to_plot,color_bar=True,color_range=(0,max_value),hemis=['L','R'],den='2mm',labels=['hipp'],embed_nb=False,transparent_bg=True,tighten_cwindow=True,screenshot=True,cmap='jet',  size=[350,300],filename=img_stream) #,color_range=(0,max_value)

    return img_stream

def plot_hippunfold_AI(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region,trc,pvc_method):
    tmp_hcsurf_L = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")

    tmp_hcsurf_R = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.func.gii")

    AI_L = (tmp_hcsurf_L - tmp_hcsurf_R)/(0.5 * (tmp_hcsurf_L+tmp_hcsurf_R))             

    to_plot = AI_L

    img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_AI_hippunfold_clin_report.png"

    hm.plotting.surfplot_canonical_foldunfold(to_plot,hemis=['L'],den='2mm',labels=['hipp'],embed_nb=False,color_bar='bottom',transparent_bg=True,tighten_cwindow=True,screenshot=True,cmap='bwr',color_range=(-0.5,0.5), size=[350,350],filename=img_stream)

    return img_stream

# Plotting asymmetry -------------------------------------------------------------
    
def plot_AI(subject,session,bids_dir,qc_dir,pial_left,pial_right,mica_pet_derivatives,ref_region,trc,pvc_method):
    tmp_pt_FDG_surf_L = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_smooth-10mm_trc-{trc}_pet.func.gii");
    tmp_pt_FDG_surf_R = nilearn.surface.load_surf_data(f"{mica_pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-{pvc_method}_ref-{ref_region}_smooth-10mm_trc-{trc}_pet.func.gii");

    AI_R = (tmp_pt_FDG_surf_R - tmp_pt_FDG_surf_L)/ (0.5 * (tmp_pt_FDG_surf_R + tmp_pt_FDG_surf_L))
    AI_L = (tmp_pt_FDG_surf_L - tmp_pt_FDG_surf_R)/ (0.5 * (tmp_pt_FDG_surf_R + tmp_pt_FDG_surf_L))

    to_plot = np.hstack((AI_L,np.zeros(32492)))
    to_plot[~mask] = np.nan

    img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_AI_surface_clin_report.png"
    
    plot_hemispheres(pial_left, pial_right,to_plot,color_bar='left',cmap="bwr",color_range=(-0.5,0.5),embed_nb=False,transparent_bg=True,size=(900,200),nan_color=(1,1,1,1),screenshot=True,filename=img_stream)
    
    # Crop the image in half lengthwise and keep the left side
    original_image_path = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_AI_surface_clin_report.png"
    cropped_image_path = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_AI_surface_clin_report_cropped.png"

    with Image.open(original_image_path) as img:
        width, height = img.size
        cropped_img = img.crop((0, 0, 500, height))  # Keep the left half
    
    cropped_img.save(cropped_image_path)

    return cropped_image_path

def plot_subcortical_AI(subject,session,bids_dir,ref_region,qc_dir,pvc_method,trc):
    
    data_lh, data_rh = _load_data_sctx(
    sctx_file=Path(f'{bids_dir}/qc/sub-{subject}/ses-{session}/sub-{subject}_ses-{session}_subcortical_means_pvc-{pvc_method}_ref-{ref_region}_trc-{trc}_pet.csv'),
    analysis="asymmetry")   
    
    to_plot = np.hstack((data_lh, data_rh))

    img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_AI_subcortical_clin_report.png"

    plot_hemispheres(sctx_left,sctx_right,to_plot,color_bar='left', 
        cmap="bwr",color_range=(-0.5,0.5), embed_nb=False,transparent_bg=True,size=(900,200),nan_color=(1,1,1, 0),screenshot=True,filename=img_stream)
        
    cropped_image_path = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_AI_subcortical_clin_report_cropped.png"

    with Image.open(img_stream) as img:
        width, height = img.size
        cropped_img = img.crop((0, 0, 475, height))  # Keep the left half
    
    cropped_img.save(cropped_image_path)

    return cropped_image_path

def plot_roi(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region,trc,pvc_method):
    pet_derivatives=f'{mica_pet_derivatives}'
    mri_derivatives=f'{bids_dir}/derivatives/fastsurfer'

    img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_SUVR_plot_roi_clin_report.png"

    plotting.plot_roi(f'{pet_derivatives}/sub-{subject}/ses-{session}/pet/sub-{subject}_ses-{session}_space-{space}_pvc-none_ref-{ref_region}_trc-{trc}_pet_desc-brainmask.nii.gz',bg_img=f'{mri_derivatives}/sub-{subject}_ses-{session}/mri/orig.mgz',display_mode='z',cut_coords=tuple(np.linspace(-75,75,15)),alpha=0.3,radiological=True, title=f'sub-{subject} ses-{session} FDG SUVR',dim=0,resampling_interpolation='continuous',output_file=img_stream)

    return img_stream

def max_hist(data, bins=50):
    data = data[~np.isnan(data)]  # Remove NaN values
    hist_values, bin_edges = np.histogram(data, bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    max_index = np.argmax(hist_values)
    max_value = bin_centers[max_index]
    return max_value

def plot_Zscore(subject,session,bids_dir,qc_dir,mica_pet_derivatives):
    pet_derivatives=f'{mica_pet_derivatives}'
    mri_derivatives=f'{bids_dir}/derivatives/fastsurfer'
    pvc = 'none'
    Z_score_threhold = 1.96

    # FDG_surf_ctrl_hist_norm_mean = np.genfromtxt(f'/host/fladgate/local_raid/jack/FDG/FDG_surf_ctrl_hist_norm_mean.csv', delimiter=',', missing_values='""', filling_values=np.nan)
    # FDG_surf_ctrl_hist_norm_std = np.genfromtxt(f'/host/fladgate/local_raid/jack/FDG/FDG_surf_ctrl_hist_norm_std.csv', delimiter=',', missing_values='""', filling_values=np.nan)
    FDG_surf_ctrl_hist_norm_mean = np.genfromtxt(f'/app/surfaces/FDG_surf_ctrl_hist_norm_mean.csv', delimiter=',', missing_values='""', filling_values=np.nan)
    FDG_surf_ctrl_hist_norm_std = np.genfromtxt(f'/app/surfaces/FDG_surf_ctrl_hist_norm_std.csv', delimiter=',', missing_values='""', filling_values=np.nan)
    
    tmp_L = nilearn.surface.load_surf_data(f'{pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-{pvc}_ref-{ref_region}_smooth-10mm_trc-{trc}_pet.func.gii');
    tmp_R = nilearn.surface.load_surf_data(f'{pet_derivatives}/sub-{subject}/ses-{session}/surf/sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-{pvc}_ref-{ref_region}_smooth-10mm_trc-{trc}_pet.func.gii');

    tmp = np.hstack((tmp_L,tmp_R))
    tmp[~mask] = np.nan
    norm_factor = max_hist(tmp)
    test_FDG_surf_pt = tmp / norm_factor

    Zscore = (test_FDG_surf_pt - FDG_surf_ctrl_hist_norm_mean)/ FDG_surf_ctrl_hist_norm_std

    to_plot = Zscore
    # to_plot = test_FDG_surf_pt
    to_plot[~mask] = np.nan   
    to_plot[(to_plot >= -Z_score_threhold) & (to_plot <= Z_score_threhold)] = 0 # Filter out values outside the range

    img_stream = f"{qc_dir}/sub-{subject}_ses-{session}_FDG_SUVR_plot_Zscore_clin_report.png"

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
    return df


cortical_SUVR, max_value = plot_SUVR(subject,session,bids_dir,qc_dir, pial_left, pial_right, mask,max_value,mica_pet_derivatives,ref_region,trc,pvc_method)

with rc.ReportCreator(
   title="MICA-PET Report",
   description=f"**Subject**: {subject} | **Session**: {session} | **Modality**: FDG PET",
   footer="Multimodal Imaging and Computational Anatomy (MICA) Lab - McGill University. For research use only.",
   logo=f"https://box.bic.mni.mcgill.ca/s/GbLcj26GmYWBfLL/download"
) as report:

   view = rc.Block(
    rc.Heading(label="Standard Uptake Value Ratio (SUVR)"),
    
    rc.Select(
        blocks=[
            rc.Image(
                cortical_SUVR,
                label="Cortical FDG SUVR",
                extra_css="width: 900px; height: auto;",
            )
        ]
    ),
    rc.Select(
        blocks=[
            rc.Image(
                plot_subcort(subject,session,bids_dir,qc_dir,ref_region,max_value,pvc_method,trc),
                label="Subcortical FDG SUVR",
                extra_css="width: 900px; height: auto;",
            ),
        ]
    ),
    rc.Select(
        blocks=[
            rc.Image(
                plot_hippunfold(subject,session,bids_dir,qc_dir,max_value,mica_pet_derivatives,ref_region,trc,pvc_method),
                label="Hippocampal FDG SUVR",
                extra_css="width: 450px; height: auto;",
            ),
        ]
    ),

    rc.Heading(label="Asymmetry Index (AI)"), 
            # rc.Heading(label="(BLUE = Left < Right; RED = Right < Left)",level=3),
    
    rc.Select(
        blocks=[
            # The `rc.Image()` blocks in the code are creating images to be displayed in the report.
            # Each `rc.Image()` block specifies the path to an image file and provides a label for
            # that image.
            rc.Image(
                plot_AI(subject,session,bids_dir,qc_dir, pial_left, pial_right,mica_pet_derivatives,ref_region,trc,pvc_method),
                label="Cortical FDG SUVR AI"
            ),
            rc.Image(
                plot_subcortical_AI(subject,session,bids_dir,ref_region,qc_dir,pvc_method,trc),
                label="Subcortical FDG SUVR AI"
            ),
            rc.Image(
                plot_hippunfold_AI(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region,trc,pvc_method),
                label="Hippocampal FDG SUVR AI",
            ),
            
        ],
        # label="(BLUE = Left < Right; RED = Right < Left)",
    ),
    rc.Group(
        rc.Metric(
            heading="Asymmetry Index interpretation",
            value="BLUE = Left < Right; RED = Right < Left",
            label="AI = (L - R) / (0.5 * (L + R))"
        ),
    ),
    
    rc.Heading(label="FDG PET Z score thresholded at |Z| > 1.96"), 
    
    rc.Select(
        blocks=[
            rc.Image(
                plot_Zscore(subject,session,bids_dir,qc_dir,mica_pet_derivatives,ref_region),
                label="FDG PET Z score",
                extra_css="width: 900px; height: auto;"
            ),
        ]
    ),
    rc.Select(
        blocks=[
            rc.DataTable(
                parcel_stats(subject,session,bids_dir,args.subj_dir,qc_dir,space,mica_pet_derivatives,ref_region,trc,pvc_method),
                label="Regional SUVR and Asymmetry Index Statistics",
                index=False
            )
        ]
    ), 
    rc.Select(
        blocks=[
            rc.Image(
                f"{qc_dir}/sub-{subject}_ses-{session}_SUVR_mosaic_screenshot.png",
                label="PET-MRI Overlay",
                extra_css="width: 1300px; height: auto;"
            ),
        ]
    )
)

report.save(view, f"{qc_dir}/sub-{subject}_ses-{session}_report.html")

# Clean up display
if display_flag:
    display.stop()
    del display

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] QC screenshots completed.")
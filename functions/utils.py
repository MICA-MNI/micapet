# utils.py - Python Utilities

import os
import sys
import json
import subprocess
from nilearn.image import load_img, mean_img
from nilearn.surface import load_surf_data
import nibabel as nib
import warnings 
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
warnings.filterwarnings("ignore", category=UserWarning, module="stopit")

MICA_PET_VERSION = 'v.beta.0.1'
os.environ['MICA_PET_VERSION'] = MICA_PET_VERSION

class bcolors:
    RED = '\033[91m'
    PURPLE = '\033[95m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    TEAL = '\033[38;5;37m'
    CIAN = '\033[38;5;45m'
    WARNING = '\033[38;5;220m' #yellow
    ERROR = '\033[38;5;1m' #red
    BOLD = '\033[1m'
    RESET = '\033[0m'


    def disable(self):
        self.INFO = ''
        self.RED = ''
        self.PURPLE = ''
        self.GREEN = ''
        self.BLUE = ''
        self.TEAL = ''
        self.CIAN = ''
        self.WARNING = ''
        self.ERROR = ''
        self.BOLD = ''
        self.RESET = ''

def info(message):
    print(f"{bcolors.CIAN}  Info ... {message}{bcolors.ENDC}\n")

def warning(message):
    print(f"\n{bcolors.WARNING}  Warning ... {message}{bcolors.ENDC}\n")

def error(message):
    print(f"{bcolors.ERROR}  Error ... {message}{bcolors.ENDC}\n")

def note(message):
    print(f"{bcolors.PURPLE}{message}{bcolors.ENDC}\n")

class BIDSpetName:
    def __init__(self, **kwargs):
        self.keys = ["sub", "ses", "task", "trc", "rec", "run", "desc"]
        self.values = kwargs
    
    def build(self):
        parts = []
        for key in self.keys:
            if key in self.values:
                parts.append(f"{key}-{self.values[key]}")
        parts.append("pet")
        return "_".join(parts)

class BIDSderivativeName:
    ALLOWED_SUFFIXES = ["pet", "T1w", "T1w_mask", "surf", "xfm", "mask"]
    def __init__(self, **kwargs):
        self.keys = ["sub", "ses", "hemi", "surf", "from", "to", "space", "label", "smooth", "pvc", "ref", "desc", "trc","suffix"]
        self.values = kwargs
    
    def build(self):
        parts = []
        for key in self.keys:
            if key in self.values:
                if key == "suffix":
                    # Directly append the suffix without a prefix "suffix-"
                    suffix = self.values[key]
                    if self.values[key] != "surf": #is not
                        parts.append(suffix)
                elif isinstance(self.values[key], str):
                    parts.append(f"{key}-{self.values[key]}")
                elif isinstance(self.values[key], int):
                    parts.append(f"{key}-{self.values[key]}")
        
        return "_".join(parts)

class BIDSName:
    # based on BIDS especifications v1.11.1
    ALLOWED_SUFFIXES = ["FLAIR", "PDT2", "PDw", "T1w", "T2starw", "T2w", "UNIT1", "angio", "inplaneT1", "inplaneT2",
                        "T2starmap", "inv-1_MP2RAGE", "inv-2_MP2RAGE", "T1map", "angio", "MTR", "MTRmap", "MTsat",
                        "sbref", "bold","dwi","asl","m0scan","noRF",
                         "epi, fieldmap", "magnitude","phase", "TB1DAM", "TB1EPI", "TB1AFI", "TB1RFM", "TBTFL", "TB1SRGE"] 
    
    # Entitites
    def __init__(self, **kwargs):
        self.keys = ["sub", "ses", "task", "acq", "ce", "rec","dir","run","mod","echo","mt", "part", "chunk", "suffix"]
        self.values = kwargs    
        # Validate suffix
        if 'suffix' in self.values and self.values['suffix'] not in self.ALLOWED_SUFFIXES:
            invalid_suffix = self.values['suffix']
            raise ValueError(f"Invalid suffix '{invalid_suffix}'. Must be one of {self.ALLOWED_SUFFIXES}")
    
    def build(self):
        parts = []
        for key in self.keys:
            if key in self.values:
                if key == "suffix":
                    # Directly append the suffix without a prefix "suffix-"
                    suffix = self.values[key]
                    parts.append(suffix)
                elif isinstance(self.values[key], str):
                    parts.append(f"{key}-{self.values[key]}")
                elif isinstance(self.values[key], int):
                    parts.append(f"{key}-{self.values[key]}")
        
        return "_".join(parts)

def check_bids_dir(bids_dir, subject, session):
    """
    Check if the provided directory is a valid BIDS dataset.
    
    Parameters
    ----------
    bids_dir : str
        Path to the BIDS dataset directory.
    
    subject : str
        Subject identification.
    session : str
        Session identification.
    """

    if not os.path.exists(f"{bids_dir}/rawdata/sub-{subject}/ses-{session}"):
        print(f"Error: BIDS rawdata directory for subject {subject}, session {session} does not exist.")
        sys.exit(1)

def print_time_stamp(message,colour="blue"):
    from datetime import datetime
    if colour == "blue":
        print(f"\n{bcolors.WARNING}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {bcolors.BLUE}{message}\n{bcolors.RESET}")
    elif colour == "green":
        print(f"\n{bcolors.WARNING}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {bcolors.GREEN}{message}\n{bcolors.RESET}")
    elif colour == "red":
        print(f"\n{bcolors.WARNING}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {bcolors.RED}{message}\n{bcolors.RESET}")
    elif colour == "purple":
        print(f"\n{bcolors.WARNING}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {bcolors.PURPLE}{message}\n{bcolors.RESET}")
    else:
        print(f"\n{bcolors.WARNING}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {bcolors.RESET}{message}\n")

def resample_to_nativepro(input, output, reference=None,interp='trilin'):

    """Resample raw T1w MRI to LPI orientation (nativepro space) using AFNI.
    
    Parameters:
    -----------
    input : str
        Path to the input T1w MRI file (NIfTI format).
    output : str
        Path to the output resampled T1w MRI file (NIfTI format).
    reference : str, optional
        Path to a reference image for resampling. If provided, the output will be resampled to match the reference image's space.
    interp : str, optional
        Interpolation method for resampling. Default is 'trilin'. Other options include 'nearest', 'cubic'
    """

    import os
    import nipype.interfaces.afni as afni
    from nipype.interfaces.freesurfer import ApplyVolTransform
    from pathlib import Path

    AFNI_dir = (Path(__file__).resolve().parent.parent / "resources" / "AFNI").resolve()

    if AFNI_dir not in os.environ["PATH"].split(os.pathsep):
        os.environ["PATH"] = f"{AFNI_dir}:{os.environ['PATH']}"

    # Disable AFNI warning about NIFTI datatypes
    os.environ['AFNI_NIFTI_TYPE_WARN'] = "NO"

    # Define output file path
    output = os.path.abspath(output)
    
    # Verify input exists before running
    if not os.path.exists(input):
        raise FileNotFoundError(f"Input image not found: {input}")

    # Configure AFNI Resample interface (3dresample)
    resample = afni.Resample()
    resample.inputs.in_file = input
    resample.inputs.orientation = 'LPI'
    resample.inputs.outputtype = 'NIFTI_GZ'
    resample.inputs.out_file = output

    # Print command execution details
    print(f"Resampling T1w MRI to nativepro space (LPI orientation)...")
    print(f"Command: {resample.cmdline}")

    # Execute interface
    resample.run()

    # Resample to reference if provided 
    if reference is not None:
        applyreg = ApplyVolTransform()
        applyreg.inputs.source_file= output
        applyreg.inputs.reg_header=True
        applyreg.inputs.interp = interp
        applyreg.inputs.target_file= reference
        applyreg.inputs.transformed_file=output
        applyreg.run()

    print(f"✓ Saved resampled image to: {output}\n")

    return output

def convert_array_to_gifti(input_array, output_path):
    import nibabel as nib
    import numpy as np
    """
    Convert a NumPy array to GIfTI format and save it.

    Parameters:
    - input_array: numpy.ndarray, the array to convert.
    - output_path: str, path to save the converted GIfTI file.
    """
    # Convert the NumPy array to GIfTI format
    data_32 = input_array.astype(np.float32)
    gifti_image = nib.gifti.GiftiImage(darrays=[nib.gifti.GiftiDataArray(data_32)])

    # Save as GIfTI
    nib.save(gifti_image, output_path)
    print(f"Saved GIfTI file to {output_path}")

def cleanup_tmp(tmp_dir):
    """
    Clean up temporary files in the specified directory.

    Parameters:
    - tmp_dir: str, path to the temporary directory to clean up.
    """
    import shutil
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
        print(f"Cleaned up temporary directory: {tmp_dir}")
    else:
        print(f"Temporary directory does not exist: {tmp_dir}")

subcortical_dict = {'Left-Accumbens-area': 26,
'Left-Amygdala': 18,
'Left-Caudate': 11,
'Left-Hippocampus': 17,
'Left-Pallidum': 13,
'Left-Putamen': 12,
'Left-Thalamus': 10,
'Right-Accumbens-area': 58,
'Right-Amygdala': 54,
'Right-Caudate': 50,
'Right-Hippocampus': 53,
'Right-Pallidum': 52,
'Right-Putamen': 51,
'Right-Thalamus': 49}
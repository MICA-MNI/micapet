import os
import nipype.interfaces.afni as afni
import argparse


def resample_to_nativepro(input_t1w, nativepro_mri):
    """Resample raw T1w MRI to LPI orientation (nativepro space) using AFNI.
    
    Parameters:
    -----------
    input_t1w : str
        Path to the input T1w MRI file (NIfTI format).
    nativepro_mri : str
        Path to the output resampled T1w MRI file (NIfTI format).
    """
    # Disable AFNI warning about NIFTI datatypes
    os.environ['AFNI_NIFTI_TYPE_WARN'] = "NO"

    # Define output file path
    nativepro_mri = os.path.abspath(nativepro_mri)
    
    # Verify input exists before running
    if not os.path.exists(input_t1w):
        raise FileNotFoundError(f"Input image not found: {input_t1w}")

    # Configure AFNI Resample interface (3dresample)
    resample = afni.Resample()
    resample.inputs.in_file = input_t1w
    resample.inputs.orientation = 'LPI'
    resample.inputs.outputtype = 'NIFTI_GZ'
    resample.inputs.out_file = nativepro_mri

    # Print command execution details
    print(f"Resampling T1w MRI to nativepro space (LPI orientation)...")
    print(f"Command: {resample.cmdline}")

    # Execute interface
    resample.run()
    print(f"✓ Saved resampled image to: {nativepro_mri}\n")

    return nativepro_mri


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Resample a T1w MRI to LPI orientation using AFNI."
    )
    parser.add_argument(
        "input_t1w",
        help="Input T1-weighted MRI (.nii or .nii.gz)"
    )
    parser.add_argument(
        "output_t1w",
        help="Output resampled MRI (.nii.gz)"
    )

    args = parser.parse_args()

    resample_to_nativepro(args.input_t1w, args.output_t1w)

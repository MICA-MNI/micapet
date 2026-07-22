import os
import nipype.interfaces.afni as afni
from nipype.interfaces.freesurfer import ApplyVolTransform
import argparse


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Resample a T1w MRI to LPI orientation using AFNI/FreeSurfer."
    )
    parser.add_argument(
        "input",
        help="Input T1-weighted MRI (.nii or .nii.gz)"
    )
    parser.add_argument(
        "output",
        help="Output resampled MRI (.nii.gz)"
    )
    parser.add_argument(
        "--reference",
        help="Optional reference image for space alignment (default: None)",
        default=None
    )
    parser.add_argument(
        "--interp",
        help="Interpolation method for resampling (default: 'trilinear')",
        default='trilinear',
        choices=['trilinear', 'cubic', 'nearest']
    )

    args = parser.parse_args()

    # Pass all CLI arguments into the function
    resample_to_nativepro(
        input=args.input,
        output=args.output,
        reference=args.reference,
        interp=args.interp
    )

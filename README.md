# MICA-PET Pipeline

MICA-PET is a neuroimaging workflow for processing PET data in a BIDS-compatible project. It runs anatomical reconstruction, PET-to-MRI registration, partial volume correction, surface projection, and report generation from a single entry point.

![MICA-PET workflow](https://github.com/MICA-MNI/micapet/blob/25541b11aca6798030e4b70ca56ac8193358c881/workflow.png)

## What this repository contains

- [run.py](run.py): main command-line entry point
- [workflow](workflow): Snakemake workflow definition
- [functions](functions): processing steps for anatomy, coregistration, PVC, SUVR, and QC
- [resources](resources): supporting files and templates
<!-- - [scripts](scripts): helper scripts for Singularity and cluster submission -->

## Requirements

Before running the pipeline, make sure you have:

- Python
- Conda
- Apptainer or Singularity installed on the host (if using containerized version)
- A valid [FreeSurfer license file](https://surfer.nmr.mgh.harvard.edu/registration.html)
- Container images for FastSurfer and HippUnfold 

## Installation

```bash
git clone <repo-url>
cd MICA-PET/scripts
conda env create -f environment.yml
conda activate micapet
chmod +x run.py
```

## Quick start

Run the workflow for one participant with:

```bash
./run.py /path/to/bids /path/to/output participant \
  --fastsurfer-img /path/to/fastsurfer.sif \
  --hippunfold-img /path/to/hippunfold.sif \
  --fs-license /path/to/license.txt \
  --psf {psf} \
  --ref_region {reference region} \
  --pvc_method {PVC method} \
  --smoothing {FWHM} \
  /path/to/bids /path/to/derivatives participant \
  --cores {# of cores or 'all'} \
  --participant-label {participant ID}
```

### Mandatory parameters

- `--psf`: PET PSF in mm
- `--ref-region`: SUVR reference region (`pons`, `cerebellarGM`, or `composite`)
- `--pvc-method`: PVC method such as: `RBV-FS`, `MG`, `IY`, `LABBE`, `RL`, `VC`, `RBV`, `LABBE+RBV`, `RBV+VC`, `RBV+RL`, `LABBE+RBV+VC`, `LABBE+RBV+RL`, `MTC`, `LABBE+MTC`, `MTC+VC`, `MTC+RL`, `LABBE+MTC+VC`, `LABBE+MTC+RL`, `IY+VC`, `IY+RL`, `MG+VC`, `MG+RL`.
- `--fs-license`: path to the FreeSurfer license file
- `--fastsurfer-img`: (if FastSurfer to be run) path to the FastSurfer Singularity image
- `--hippunfold-img`: (if HippUnfold to be run) path to the HippUnfold Singularity image
- `--existing-freesurfer-dir` : (if FastSurfer/FreeSurfer already run) Path to existing FreeSurfer subject outputs directory (ex. /path/to/freesurfer/sub-01_ses-01). If provided, will create symlinks instead of running FastSurfer.
- `--existing-hippunfold-dir` : (if HippUnfold already run) Path to existing HippUnfold subject outputs directory (ex. /path/to/hippunfold_v1.4.1). If provided, will create symlinks instead of running HippUnfold.

### Optional parameters
- `--hippunfold-cache-dir` : Path to hippunfold cache directory.
- `--skip-hippunfold` : Flag to skip HippUnfold processing. If set, will not run HippUnfold and will not require HippUnfold outputs.
- `--edge-reg`       : Flag to use edge-based registration method for PET to T1w registration rather than FreeSurfer mri_coreg.
- `--nonlinear-coreg` : Flag to perform nonlinear co-registration to MNI space. If set, will run lamareg nonlinear registration.
- `--smoothing`: one or more smoothing values for cortical surface projection
- `--threads`: number of CPU threads

### Optional PETPVC parameters
- `--pvc_mask`       : Optional custom mask to use for PETPVC. Must be a 4D NIfTI with one ROI per frame. Sum across timeframes must be 1 at each voxel. Must be in FreeSurfer/FastSurfer space (eg. orig.mgz). If not provided, a two tissue mask will be generated for MG PVC and a GM+WM+CSF+background mask will be generated for all others.
- `--pvc-iterations` : Number of iterations for iterative PVC methods (default 50).
- `--pvc-n_iter`     : Number of iterations for iterative PVC methods (IY) (default: 10).
- `--pvc-n_deconv`   : Number of iterations for deconvolution PVC methods (RL, VC) (default: 10).

## Typical outputs

The pipeline writes derivatives into the output directory, including:

- reference region masks
- partial volume corrected and normalized PET images
- registration transforms
- surface metrics in GIFTI format
- QC report images and HTML reports

## Repository layout

```text
.
├── config/
├── functions/
| ├── MICA_PET.py
| └── utils.py
├── resources/
| ├── AFNI/
| ├── lamareg/
| ├── mni_icbm152_t1_tal_nlin_sym_09a_parc.nii.gz
| └── mni_icbm152_t1_tal_nlin_sym_09a.nii.gz
├── workflow/
├── README.md
├── run.py
└── environment.yml
```
<!-- | | └── 3dresample

| | ├── synthseg_parc_2.0.h5
| | ├── synthseg_robust_2.0.h5
| | ├── synthseg_robust_2.0.h5.000
| | ├── synthseg_robust_2.0.h5.001
| | └── synthseg_robust_2.0.h5.002 -->

<!-- ## HPC usage

For cluster execution, the repository includes helper scripts under [scripts](scripts) for submitting jobs to PBS/Torque-style systems. For multi-subject runs, it is recommended to use a separate output directory per participant to avoid workflow configuration conflicts. -->

## Troubleshooting

- If the workflow fails with a config error, rerun with a per-subject output directory.
- If a previous job was interrupted, rerun with `--unlock` or clean the stale lock and then run it again.
- If FreeSurfer steps fail, verify that the license path and container bindings are correct.
- If you want to reuse prior outputs, pass the existing directory flags to skip expensive reruns.

## Notes

This repository is intended for research use and assumes a working neuroimaging software stack and container environment.

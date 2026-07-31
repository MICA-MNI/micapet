# MICA-PET Pipeline

MICA-PET is a neuroimaging workflow for processing PET data in a BIDS-compatible project. It runs anatomical reconstruction, PET-to-MRI registration, partial volume correction, surface projection, and report generation from a single entry point.

## What this repository contains

- [run.py](run.py): main command-line entry point
- [workflow](workflow): Snakemake workflow definition
- [functions](functions): processing steps for anatomy, coregistration, PVC, SUVR, and QC
- [resources](resources): supporting files and templates
- [scripts](scripts): helper scripts for Singularity and cluster submission

## Requirements

Before running the pipeline, make sure you have:

- Python 3.10+
- Conda or mamba
- Apptainer or Singularity installed on the host
- A valid FreeSurfer license file
- Container images for MICA-PET, FastSurfer, and HippUnfold

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
  --fs-license /path/to/license.txt
```

### Common options

- `--fastsurfer-img`: path to the FastSurfer Singularity image
- `--hippunfold-img`: path to the HippUnfold Singularity image
- `--fs-license`: path to the FreeSurfer license file
- `--psf`: PET PSF in mm
- `--ref-region`: SUVR reference region (`pons`, `cerebellarGM`, or `composite`)
- `--pvc-method`: PVC method such as `RBV-FS` or `MG`
- `--smoothing`: one or more smoothing values for cortical surface projection
- `--threads`: number of CPU threads
- `--skip-hippunfold`: skip HippUnfold processing when needed
- `--existing-freesurfer-dir`: reuse an existing FreeSurfer/FastSurfer subject directory
- `--existing-hippunfold-dir`: reuse an existing HippUnfold output directory

## Typical outputs

The pipeline writes derivatives into the output directory, including:

- anatomical and PET images
- registration transforms
- PVC and SUVR volumes
- surface metrics in GIFTI format
- QC report images and HTML reports

## Repository layout

```text
.
├── run.py
├── workflow/
├── functions/
├── resources/
├── scripts/
└── environment.yml
```

## HPC usage

For cluster execution, the repository includes helper scripts under [scripts](scripts) for submitting jobs to PBS/Torque-style systems. For multi-subject runs, it is recommended to use a separate output directory per participant to avoid workflow configuration conflicts.

## Troubleshooting

- If the workflow fails with a config error, rerun with a per-subject output directory.
- If a previous job was interrupted, rerun with `--unlock` or clean the stale lock.
- If FreeSurfer steps fail, verify that the license path and container bindings are correct.
- If you want to reuse prior outputs, pass the existing directory flags to skip expensive reruns.

## Notes

This repository is intended for research use and assumes a working neuroimaging software stack and container environment.

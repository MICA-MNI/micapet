# micapet (Snakebids Version)

[![version](https://img.shields.io/github/v/tag/jlam-nsx/micapet)](https://github.com/jlam-nsx/micapet)
[![Docker Image Version](https://img.shields.io/docker/v/micalab/micapet?color=blue&label=docker%20version)](https://hub.docker.com/r/micalab/micapet)
[![License: GPL v3](https://img.shields.io/github/license/jlam-nsx/micapet?color=blue)](https://www.gnu.org/licenses/gpl-3.0)
[![GitHub issues](https://img.shields.io/github/issues/jlam-nsx/micapet)](https://github.com/jlam-nsx/micapet/issues)
[![GitHub stars](https://img.shields.io/github/stars/jlam-nsx/micapet.svg?style=flat&label=⭐%EF%B8%8F%20stars&color=brightgreen)](https://github.com/jlam-nsx/micapet/stargazers)

MICA-PET is a pipeline for processing and analyzing PET imaging data, particularly in the context of the MICA lab at McGill University. This version uses [Snakebids](https://github.com/khanlab/snakebids) to manage the workflow.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/jlam-nsx/micapet
    cd micapet
    ```

2.  Create the Conda environment:
    ```bash
    conda env create -f environment.yml
    conda activate micapet
    # Ensure you also install snakebids if not in environment.yml
    pip install snakebids
    ```

## Usage

The pipeline is executed via the `run.py` script. It follows the BIDS-App standard.

```bash
./run.py <bids_dir> <output_dir> participant [OPTIONS]
```

### Required Arguments:

*   `<bids_dir>`: The root directory of the BIDS dataset.
*   `<output_dir>`: The output directory (unused by this pipeline structure as it writes to `<bids_dir>/derivatives`). You can pass `.` or any placeholder.
*   `participant`: Analysis level.

### Required Options (via Flags):
You must provide paths to the singularity images and license:
*   `--fastsurfer_img <path>`: Path to FastSurfer Singularity image (.sif).
*   `--hippunfold_img <path>`: Path to HippUnfold Singularity image (.sif).
*   `--fs_license <path>`: Path to FreeSurfer license.txt.

### Optional Arguments:

*   `--psf <float>`: Scanner PSF FWHM in mm (default: 4.5).
*   `--ref_region <region>`: Reference region (pons, cerebellarGM, composite, none) (default: pons).
*   `--threads <int>`: Number of threads per job (default: 8).
*   `--participant_label <label>`: Run only on specific subjects (e.g. `01` `02`). Do not include `sub-`.
*   `-n`: Dry-run (print what would be done).
*   `-c <cores>`: Number of cores to use for snakemake execution.

### Example Command

```bash
./run.py \
    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG \
    . \
    participant \
    --participant_label PX003 \
    --fastsurfer_img /path/to/fastsurfer.sif \
    --hippunfold_img /path/to/hippunfold.sif \
    --fs_license /path/to/license.txt \
    --psf 4.5 \
    -c 1
```

## Testing on Server

To test the pipeline on the server with the example subject:

1.  Navigate to the `micapet` directory.
2.  Ensure you have `snakebids` installed.
3.  Run the following command (adjust paths to SIF images):

```bash
./run.py \
    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG \
    . \
    participant \
    --participant_label PX003 \
    --fastsurfer_img /path/to/fastsurfer.sif \
    --hippunfold_img /path/to/hippunfold.sif \
    --fs_license /path/to/license.txt \
    -n
```

Remove `-n` to actually run the pipeline.

## Outputs

Derivatives are stored in `<bids_dir>/derivatives/`:
*   `fastsurfer`: Cortical segmentations.
*   `hippunfold_v1.4.1`: Hippocampal unfoldings.
*   `MICA-PET_v.alpha.0.3`: PET derivatives (coreg, pvc, suvr, surfaces).
*   `qc`: Subcortical maps and HTML reports.

## Pipeline Structure

*   `run.py`: Entry point.
*   `config/snakebids.yml`: Configuration file.
*   `workflow/Snakefile`: Main Snakemake workflow.
*   `workflow/rules/`: Snakemake rules (anatomy, pet, report).
*   `functions/`: Python scripts performing the actual processing steps.

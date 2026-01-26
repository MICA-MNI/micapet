# MICA-PET Pipeline

**Version:** v.alpha.0.3

## Overview
The **MICA-PET Pipeline** is a specialized neuroimaging processing workflow designed for PET data analysis. Built using the **Snakebids** framework, it orchestrates a comprehensive anatomical and functional processing stream, integrating state-of-the-art tools including **FastSurfer**, **HippUnfold**, and **GTMseg**.

This pipeline automates the entire process from raw BIDS input to surface-projected PET maps and subcortical statistics.

## Pipeline Steps
The pipeline consists of the following key stages:

1.  **Anatomical Processing:**
    *   **FastSurfer:** Rapid volumetric segmentation and cortical surface reconstruction.
    *   **HippUnfold:** Advanced hippocampal unfolding and subfield segmentation.
    *   **GTMseg:** Geometric Transfer Matrix segmentation for accurate partial volume correction (PVC).

2.  **PET Processing:**
    *   **Linear Coregistration:** Aligns PET images to T1-weighted anatomical images (both Native and FreeSurfer spaces).
    *   **Partial Volume Correction (PVC):** Applies Region-Based Voxel-wise (RBV) correction using GTM segmentation.
    *   **SUVR Calculation:** Computes Standardized Uptake Value Ratios relative to a reference region (default: Pons).

3.  **Projections & Sampling:**
    *   **Cortical Projection:** Maps PET data onto the `fsLR-32k` cortical surface.
    *   **Hippocampal Projection:** Maps PET data onto unfolded hippocampal surfaces.
    *   **Subcortical Statistics:** Extracts mean uptake values for subcortical structures.

4.  **Quality Control:**
    *   Generates visual reports for coregistration and segmentation quality.

## Requirements

### Software
*   **Python** >= 3.10
*   **Apptainer (Singularity)** (for running containerized tools like FastSurfer and HippUnfold)
*   **FreeSurfer License** (`license.txt`)

### Container Images
You must have the following Singularity/Apptainer images available locally:
*   MICA-PET FastSurfer Image (`.sif`)
*   MICA-PET HippUnfold Image (`.sif`)

## Installation

The project uses a Conda environment for dependency management.

1.  **Clone the repository:**
    ```bash
    git clone <repo_url>
    cd micapet
    ```

2.  **Create and activate the environment:**
    ```bash
    conda env create -f environment.yml
    conda activate micapet
    ```

3.  **Ensure script is executable:**
    ```bash
    chmod +x run.py
    ```

## Usage

 The pipeline is executed via the `run.py` script. It follows the BIDS App standard.

### Basic Command
```bash
./run.py <bids_dir> <output_dir> participant \
    --fastsurfer-img /path/to/fastsurfer.sif \
    --hippunfold-img /path/to/hippunfold.sif \
    --fs-license /path/to/license.txt
```

### Arguments

| Argument | Description | Required | Default |
| :--- | :--- | :---: | :---: |
| `bids_dir` | Path to the input BIDS dataset root directory. | Yes | - |
| `output_dir` | Directory where outputs will be stored. | Yes | - |
| `participant` | Analysis level (currently only `participant` is supported). | Yes | - |
| `--fastsurfer-img` | Path to FastSurfer Apptainer/Singularity image. | **Yes** | - |
| `--hippunfold-img` | Path to HippUnfold Apptainer/Singularity image. | **Yes** | - |
| `--fs-license` | Path to FreeSurfer `license.txt` file. | **Yes** | - |
| `--psf` | Scanner Point Spread Function (FWHM in mm). | No | `4.5` |
| `--ref-region` | Reference region for SUVR (`pons`, `cerebellarGM`, `composite`, `none`). | No | `pons` |
| `--threads` | Number of threads for multithreaded steps. | No | `8` |

### Example
```bash
./run.py /data/bids_input /data/derivatives participant \
    --fastsurfer-img /opt/images/fastsurfer_v2.sif \
    --hippunfold-img /opt/images/hippunfold_v1.4.1.sif \
    --fs-license /opt/freesurfer/license.txt \
    --ref-region cerebellarGM \
    --threads 16
```

## Input / Output Structure

### Input (BIDS)
The input directory must follow the BIDS structure, containing at least:
*   `anat/`: T1-weighted images (`_T1w.nii.gz`)
*   `pet/`: PET images (`_pet.nii.gz`) with corresponding JSON sidecars.

### Output
The output directory will be structured as follows:

```
output_dir/
├── fastsurfer/                  # FastSurfer processing outputs
├── hippunfold_v1.4.1/           # HippUnfold processing outputs
├── MICA-PET_v.alpha.0.3/        # Main pipeline derivatives
│   └── sub-<ID>/
│       └── ses-<ID>/
│           ├── pet/             # Processed PET files (Coreg, PVC, SUVR)
│           ├── surf/            # Surface projected maps (func.gii)
│           ├── xfm/             # Registration transform files (.lta)
│           └── anat/            # Anatomical references
├── qc/                          # Quality control reports and CSV stats
└── logs/                        # Processing logs
```

## Troubleshooting
*   **Missing Dependencies:** Ensure all conda packages are installed and the environment is active.
*   **Container Errors:** Verify paths to `.sif` images are correct and accessible.
*   **License Errors:** Ensure the FreeSurfer license file is valid.

## Containerization (Singularity / Apptainer)

The pipeline is designed to run via **Singularity (Apptainer)**, which is the standard for high-performance computing (HPC) environments.

### 1. Build the Singularity Image
You must first build the Docker image and then convert it to a Singularity Image File (`.sif`).

```bash
# Step 1: Build Docker Image
docker build -t micalab/micapet .

# Step 2: Convert to Singularity (.sif)
# Note: You can run this on your personal machine and scp the .sif to the server
apptainer build micapet.sif docker-daemon://micalab/micapet:latest
```

### 2. Run using Singularity
To run the pipeline, you need to bind the necessary paths. The container has `apptainer` installed inside it, allowing it to Execute nested containers for FastSurfer and HippUnfold.

**Crucial Bindings:**
*   **BIDS Data & Output:** Bind your data storage locations (e.g., `-B /host:/host`).
*   **Code Overlay (Optional but Recommended):** You can bind your local code into the container to test changes without rebuilding:
    *   `-B /path/to/micapet/functions:/app/functions`
    *   `-B /path/to/micapet/workflow:/app/workflow`

**Example Command:**

```bash
# Define paths
SIF_PATH="/path/to/micapet.sif"
BIDS_DIR="/path/to/bids_dataset"
OUTPUT_DIR="/path/to/output_directory"
FS_LICENSE="/path/to/license.txt"

# External Containers
FASTSURFER_SIF="/path/to/fastsurfer.sif"
HIPPUNFOLD_SIF="/path/to/hippunfold.sif"

# Run
singularity run --cleanenv \
    -B /host:/host \
    -B /export03:/export03 \
    "$SIF_PATH" \
    "$BIDS_DIR" \
    "$OUTPUT_DIR" \
    participant \
    --participant_label PX001 \
    --fastsurfer-img "$FASTSURFER_SIF" \
    --hippunfold-img "$HIPPUNFOLD_SIF" \
    --fs-license "$FS_LICENSE" \
    --cores 16
```

**Note:** The `--cleanenv` flag is important to prevent host environment variables from conflicting with the container.

## Maintainers
*   Current Code Maintainer: [Your Name/Team]

# MICA-PET Pipeline

**Version:** v.alpha.0.3

## Overview

The **MICA-PET Pipeline** is a neuroimaging processing workflow for FDG-PET data analysis. Built on the **Snakebids** framework, it orchestrates a complete anatomical and functional processing stream using **FastSurfer**, **HippUnfold**, and **GTMseg**.

The pipeline takes raw BIDS input and produces surface-projected PET maps, subcortical statistics, and a visual QC report.

## Pipeline Steps

1. **Anatomical Processing**
   - **FastSurfer** — cortical surface reconstruction and volumetric segmentation
   - **HippUnfold** — hippocampal unfolding and subfield segmentation
   - **GTMseg** — Geometric Transfer Matrix segmentation for PVC

2. **PET Processing**
   - **Linear Coregistration** — aligns PET to T1w in Native and FreeSurfer spaces
   - **Partial Volume Correction (PVC)** — RBV-FS (default) or any PETPVC method
   - **SUVR Calculation** — normalises uptake relative to a reference region

3. **Surface Projections & Sampling**
   - **Cortical Projection** — PET mapped to `fsLR-32k` and `fsLR-5k` surfaces with configurable smoothing
   - **Hippocampal Projection** — PET mapped to unfolded hippocampal surfaces
   - **Subcortical Statistics** — mean uptake per subcortical structure (CSV)

4. **Quality Control**
   - Per-subject HTML report with SUVR maps, asymmetry index, Z-score maps, and a PET–MRI overlay mosaic

## Requirements

### Software
- **Python** ≥ 3.10
- **Singularity / Apptainer** — required on the host to run the MICA-PET container
- **FreeSurfer license** (`license.txt`)

### Container Images
- **MICA-PET `.sif`** — built from this repo (see [Build](#build-the-singularity-image))
- **FastSurfer `.sif`** — tested with `fastsurfer-cpu-v2.4.2.sif`
- **HippUnfold `.sif`** — tested with `hippunfold_v1.4.1.sif`

## Installation

```bash
git clone <repo_url>
cd micapet
conda env create -f environment.yml
conda activate micapet
chmod +x run.py
```

## Usage

The pipeline follows the BIDS App convention:

```
run.py <bids_dir> <output_dir> participant [options]
```

### Minimal example

```bash
./run.py /data/bids /data/out participant \
    --fastsurfer-img /opt/fastsurfer.sif \
    --hippunfold-img /opt/hippunfold.sif \
    --fs-license /opt/license.txt
```

### Full argument reference

#### Positional (required)

| Argument | Description |
| :--- | :--- |
| `bids_dir` | Path to the input BIDS dataset root |
| `output_dir` | Directory where all outputs are written |
| `participant` | Analysis level — only `participant` is supported |

#### Container paths

| Argument | Description | Required | Default |
| :--- | :--- | :---: | :---: |
| `--fastsurfer-img` | Path to FastSurfer Singularity image | No | — |
| `--hippunfold-img` | Path to HippUnfold Singularity image | No | — |
| `--fs-license` | Path to FreeSurfer `license.txt` | **Yes** | — |

#### Processing parameters

| Argument | Description | Required | Default |
| :--- | :--- | :---: | :---: |
| `--psf` | Scanner PSF FWHM in mm | No | `4.5` |
| `--ref-region` | SUVR reference region: `pons`, `cerebellarGM`, `composite`, `none` | No | `pons` |
| `--pvc-method` | PVC method (see below) | No | `RBV-FS` |
| `--pvc-mask` | Custom 4D NIfTI mask for PETPVC (GM+WM+CSF+BG; FS space) | No | auto-generated |
| `--pvc-n_iter` | Iterations for iterative PETPVC methods (IY) | No | `10` |
| `--pvc-n_deconv` | Iterations for deconvolution PETPVC methods (RL, VC) | No | `10` |
| `--smoothing` | Surface smoothing FWHM(s) in mm, space-separated | No | `10` |
| `--threads` | Threads for multithreaded steps | No | `8` |

**PVC methods** — `--pvc-method`:
- FreeSurfer RBV: `RBV-FS` *(default)*
- PETPVC: `MG`, `IY`, `RL`, `VC`, `RBV`, `LABBE`, `MTC`, and combinations (`LABBE+RBV`, `RBV+VC`, `IY+VC`, `MG+VC`, `LABBE+MTC`, etc.)

#### Optional inputs (skip heavy steps)

| Argument | Description | Default |
| :--- | :--- | :---: |
| `--existing-freesurfer-dir` | Path to an existing FastSurfer/FreeSurfer derivatives folder. Symlinks are created instead of re-running FastSurfer. | — |
| `--existing-hippunfold-dir` | Path to an existing HippUnfold derivatives folder. Symlinks are created instead of re-running HippUnfold. | — |
| `--skip-hippunfold` | Skip all HippUnfold steps entirely (flag) | `false` |
| `--hippunfold-cache-dir` | Pre-downloaded HippUnfold model cache directory | — |

#### Snakemake pass-through options

Any snakemake argument can be appended directly:

| Option | Description |
| :--- | :--- |
| `--cores N` | Number of CPU cores (default: all) |
| `--rerun-incomplete` | Re-run any jobs that were interrupted |
| `-n` / `--dry-run` | Print rules without executing |
| `--unlock` | Remove a stale snakemake lock |
| `--participant-label ID` | Process only the listed participant(s) |

### Extended example

```bash
./run.py /data/bids /data/out participant \
    --fastsurfer-img /opt/fastsurfer.sif \
    --hippunfold-img /opt/hippunfold.sif \
    --fs-license /opt/license.txt \
    --existing-freesurfer-dir /data/derivatives/fastsurfer \
    --skip-hippunfold \
    --psf 3.3 \
    --ref-region pons \
    --pvc-method RBV-FS \
    --smoothing 5 10 \
    --cores 16 \
    --participant-label PX003
```

## Input / Output Structure

### Input (BIDS)
```
bids_dir/
└── rawdata/
    └── sub-<ID>/
        └── ses-<ID>/
            ├── anat/   sub-<ID>_ses-<ID>_T1w.nii.gz
            └── pet/    sub-<ID>_ses-<ID>_trc-FDG_pet.nii.gz
                        sub-<ID>_ses-<ID>_trc-FDG_pet.json
```

### Output
```
output_dir/
├── fastsurfer/                        # FastSurfer outputs
├── hippunfold_v1.4.1/                 # HippUnfold outputs
├── MICA-PET_v.alpha.0.3/              # Main pipeline derivatives
│   └── sub-<ID>/
│       └── ses-<ID>/
│           ├── pet/                   # PET volumes (coreg, PVC, SUVR)
│           ├── surf/                  # Surface-projected maps (.func.gii)
│           ├── xfm/                   # Registration transforms (.lta)
│           └── anat/                  # Anatomical reference files
├── qc/                                # QC reports and stats
│   └── sub-<ID>/
│       └── ses-<ID>/
│           ├── sub-<ID>_ses-<ID>_..._report.html
│           └── sub-<ID>_ses-<ID>_..._subcortical_means_*.csv
└── logs/                              # Per-step logs
```

## Containerisation (Singularity / Apptainer)

### Build the Singularity image

```bash
# 1. Build Docker image from the repo
docker build -t micalab/micapet .

# 2. Convert to SIF (can be done on a local machine and SCP'd to the cluster)
apptainer build micapet.sif docker-daemon://micalab/micapet:latest
```

### Run via Singularity (single subject)

The container includes Apptainer internally to launch nested FastSurfer/HippUnfold containers.

```bash
SIF="/path/to/micapet.sif"
BIDS="/path/to/bids"
OUT="/path/to/output"
PROJECT="/path/to/micapet_repo"   # for live code overlay

singularity run --cleanenv \
    -B /host:/host \
    -B /export03:/export03 \
    -B "$PROJECT/functions:/app/functions" \
    -B "$PROJECT/workflow:/app/workflow" \
    -B "$PROJECT/config:/app/config" \
    -B "$PROJECT/run.py:/app/run.py" \
    --env XDG_CACHE_HOME="$OUT/.cache" \
    --env PYTHONUNBUFFERED=1 \
    "$SIF" \
    "$BIDS" "$OUT" participant \
    --participant-label PX001 \
    --fastsurfer-img /path/to/fastsurfer.sif \
    --hippunfold-img /path/to/hippunfold.sif \
    --fs-license /path/to/license.txt \
    --cores 16
```

> `--cleanenv` prevents host environment variables from conflicting with the container.
> The code-overlay bindings (`-B $PROJECT/...:/app/...`) let you test code changes without rebuilding the SIF.

## HPC Batch Submission (PBS/Torque)

Two scripts in `scripts/` handle multi-subject cluster submission.

### Key design: per-subject output directories

When many jobs share one output directory, Snakebids writes all merged configs to the same `<output_dir>/config/snakebids.yml` file simultaneously, causing an intermittent `WorkflowError: Config file must be given as JSON or YAML with keys at top level` crash. The fix is to give each subject job its own output directory so config files never collide.

### Submit a batch of subjects

```bash
# Submit any number of participants in one call
bash scripts/submit_participants.sh PX003 PX012 PX017 PX020

# Or read from a file
bash scripts/submit_participants.sh $(cat my_participants.txt)
```

Each subject is queued as a separate PBS job (`micapet_<SUBJECT>`) and writes to:
```
/export03/data/enning/micapet/micapet_output/sub-<SUBJECT>/
```

### Customise `scripts/qsub_subject.sh`

Edit the top of `qsub_subject.sh` to set your cluster paths:

| Variable | Description |
| :--- | :--- |
| `HOST_ROOT` | Base directory for outputs and SIF |
| `BIDS_DIR` | Path to your BIDS dataset |
| `SIF_PATH` | Path to the MICA-PET `.sif` file |
| `FASTSURFER_SIF` | Path to FastSurfer `.sif` |
| `HIPPUNFOLD_SIF` | Path to HippUnfold `.sif` |
| `FS_LICENSE` | Path to FreeSurfer `license.txt` |
| `CORES` | CPU cores per job (default: 16) |
| `#PBS -l walltime` | Max walltime per job (default: 24h) |

## Troubleshooting

| Problem | Solution |
| :--- | :--- |
| `WorkflowError: Config file must be given as JSON or YAML` | Race condition from concurrent jobs sharing one output dir. Use `scripts/submit_participants.sh` (per-subject output dirs) or re-run the failed job. |
| `LockException: Directory cannot be locked` | A previous job was killed mid-run. Re-run with `--unlock` flag, then run again normally. |
| `MissingOutputException` after a rule completes | Filesystem latency. Add `--latency-wait 30` to the singularity run call. |
| Pipeline hangs / no output | Check `logs/<rule>/sub-<ID>_ses-<ID>.log` for the failing step. |
| FreeSurfer errors | Verify `--fs-license` path and that the file is a valid FreeSurfer license. |
| Container can't find nested SIF | Ensure `/host` or the relevant storage partition is bound with `-B`. |
| Slow run without re-using existing data | Use `--existing-freesurfer-dir` and/or `--existing-hippunfold-dir` to symlink existing outputs and skip those steps. |

## Maintainers

- Current Code Maintainer: MICA Lab

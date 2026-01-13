# MICA-PET Pipeline (Snakebids Version)# micapet (Snakebids Version)



[![version](https://img.shields.io/github/v/tag/jlam-nsx/micapet)](https://github.com/jlam-nsx/micapet)[![version](https://img.shields.io/github/v/tag/jlam-nsx/micapet)](https://github.com/jlam-nsx/micapet)

[![Docker Image Version](https://img.shields.io/docker/v/micalab/micapet?color=blue&label=docker%20version)](https://hub.docker.com/r/micalab/micapet)[![Docker Image Version](https://img.shields.io/docker/v/micalab/micapet?color=blue&label=docker%20version)](https://hub.docker.com/r/micalab/micapet)

[![License: GPL v3](https://img.shields.io/github/license/jlam-nsx/micapet?color=blue)](https://www.gnu.org/licenses/gpl-3.0)[![License: GPL v3](https://img.shields.io/github/license/jlam-nsx/micapet?color=blue)](https://www.gnu.org/licenses/gpl-3.0)

[![GitHub issues](https://img.shields.io/github/issues/jlam-nsx/micapet)](https://github.com/jlam-nsx/micapet/issues)[![GitHub issues](https://img.shields.io/github/issues/jlam-nsx/micapet)](https://github.com/jlam-nsx/micapet/issues)

[![GitHub stars](https://img.shields.io/github/stars/jlam-nsx/micapet.svg?style=flat&label=⭐%EF%B8%8F%20stars&color=brightgreen)](https://github.com/jlam-nsx/micapet/stargazers)[![GitHub stars](https://img.shields.io/github/stars/jlam-nsx/micapet.svg?style=flat&label=⭐%EF%B8%8F%20stars&color=brightgreen)](https://github.com/jlam-nsx/micapet/stargazers)



MICA-PET is a pipeline for processing and analyzing PET imaging data, particularly in the context of the MICA lab at McGill University. This version uses [Snakebids](https://github.com/khanlab/snakebids) to manage the workflow as a BIDS App.MICA-PET is a pipeline for processing and analyzing PET imaging data, particularly in the context of the MICA lab at McGill University. This version uses [Snakebids](https://github.com/khanlab/snakebids) to manage the workflow.



## Features## Installation



- **FastSurfer** segmentation and cortical reconstruction1.  Clone the repository:

- **HippUnfold** hippocampal segmentation and surface extraction    ```bash

- **PET coregistration** to T1w anatomical images    git clone https://github.com/jlam-nsx/micapet

- **Partial Volume Correction (PVC)** using RBV method    cd micapet

- **SUVR calculation** with configurable reference regions    ```

- **Surface-based PET projection** to cortical and hippocampal surfaces

- **Subcortical ROI extraction**2.  Create the Conda environment:

- **Clinical report generation**    ```bash

    conda env create -f environment.yml

## Installation    conda activate micapet

    # Ensure you also install snakebids if not in environment.yml

### Prerequisites    pip install snakebids

    ```

- Python 3.10+

- Conda or Mamba## Usage

- Singularity (for running FastSurfer and HippUnfold containers)

- FreeSurfer license fileThe pipeline is executed via the `run.py` script. It follows the BIDS-App standard.



### Setup```bash

./run.py <bids_dir> <output_dir> participant [OPTIONS]

1. Clone the repository:```

   ```bash

   git clone https://github.com/jlam-nsx/micapet### Required Arguments:

   cd micapet

   git checkout 3-snakebidsify  # Use the snakebids branch*   `<bids_dir>`: The root directory of the BIDS dataset.

   ```*   `<output_dir>`: The output directory (unused by this pipeline structure as it writes to `<bids_dir>/derivatives`). You can pass `.` or any placeholder.

*   `participant`: Analysis level.

2. Create and activate the Conda environment:

   ```bash### Required Options (via Flags):

   conda env create -f environment.ymlYou must provide paths to the singularity images and license:

   conda activate micapet*   `--fastsurfer_img <path>`: Path to FastSurfer Singularity image (.sif).

   ```*   `--hippunfold_img <path>`: Path to HippUnfold Singularity image (.sif).

*   `--fs_license <path>`: Path to FreeSurfer license.txt.

3. Ensure snakebids is installed:

   ```bash### Optional Arguments:

   pip install snakebids

   ```*   `--psf <float>`: Scanner PSF FWHM in mm (default: 4.5).

*   `--ref_region <region>`: Reference region (pons, cerebellarGM, composite, none) (default: pons).

## Usage*   `--threads <int>`: Number of threads per job (default: 8).

*   `--participant_label <label>`: Run only on specific subjects (e.g. `01` `02`). Do not include `sub-`.

The pipeline follows the [BIDS App](https://bids-apps.neuroimaging.io/) standard and is executed via the `run.py` script.*   `-n`: Dry-run (print what would be done).

*   `-c <cores>`: Number of cores to use for snakemake execution.

### Basic Usage

### Example Command

```bash

./run.py <bids_dir> <output_dir> participant [OPTIONS]```bash

```./run.py \

    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG \

### Required Arguments    . \

    participant \

| Argument | Description |    --participant_label PX003 \

|----------|-------------|    --fastsurfer_img /path/to/fastsurfer.sif \

| `bids_dir` | Path to the BIDS dataset root directory |    --hippunfold_img /path/to/hippunfold.sif \

| `output_dir` | Path to the output directory for derivatives |    --fs_license /path/to/license.txt \

| `participant` | Analysis level (currently only `participant` is supported) |    --psf 4.5 \

    -c 1

### Required Options```



| Option | Description |## Testing on Server

|--------|-------------|

| `--fastsurfer-img PATH` | Path to FastSurfer Singularity image (.sif) |To test the pipeline on the server with the example subject:

| `--hippunfold-img PATH` | Path to HippUnfold Singularity image (.sif) |

| `--fs-license PATH` | Path to FreeSurfer license.txt file |1.  Navigate to the `micapet` directory.

2.  Ensure you have `snakebids` installed.

### Optional Arguments3.  Run the following command (adjust paths to SIF images):



| Option | Default | Description |```bash

|--------|---------|-------------|./run.py \

| `--participant-label LABEL` | All subjects | Process only this subject |    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG \

| `--psf FLOAT` | 4.5 | Scanner PSF FWHM in mm |    . \

| `--ref-region REGION` | pons | Reference region for SUVR (pons, cerebellarGM, composite, none) |    participant \

| `--threads INT` | 8 | Number of threads for parallel processing |    --participant_label PX003 \

| `--hippunfold-cache-dir PATH` | - | Path to HippUnfold cache directory |    --fastsurfer_img /path/to/fastsurfer.sif \

    --hippunfold_img /path/to/hippunfold.sif \

### Snakemake Options    --fs_license /path/to/license.txt \

    -n

All standard Snakemake options are supported. Common ones include:```



| Option | Description |Remove `-n` to actually run the pipeline.

|--------|-------------|

| `-n, --dry-run` | Show what would be done without executing |## Outputs

| `-j, --cores N` | Number of cores to use |

| `--forceall` | Force re-execution of all rules |Derivatives are stored in `<bids_dir>/derivatives/`:

| `--rerun-incomplete` | Re-run incomplete jobs |*   `fastsurfer`: Cortical segmentations.

*   `hippunfold_v1.4.1`: Hippocampal unfoldings.

### Example*   `MICA-PET_v.alpha.0.3`: PET derivatives (coreg, pvc, suvr, surfaces).

*   `qc`: Subcortical maps and HTML reports.

```bash

# Dry run for a single subject## Pipeline Structure

./run.py \

    /path/to/bids \*   `run.py`: Entry point.

    /path/to/output \*   `config/snakebids.yml`: Configuration file.

    participant \*   `workflow/Snakefile`: Main Snakemake workflow.

    --participant-label PX003 \*   `workflow/rules/`: Snakemake rules (anatomy, pet, report).

    --fastsurfer-img /path/to/fastsurfer.sif \*   `functions/`: Python scripts performing the actual processing steps.

    --hippunfold-img /path/to/hippunfold.sif \
    --fs-license /path/to/license.txt \
    -n

# Actual run
./run.py \
    /path/to/bids \
    /path/to/output \
    participant \
    --participant-label PX003 \
    --fastsurfer-img /path/to/fastsurfer.sif \
    --hippunfold-img /path/to/hippunfold.sif \
    --fs-license /path/to/license.txt \
    --threads 8
```

## Project Structure

```
micapet/
├── run.py                    # Main entry point (BIDS App CLI)
├── config/
│   └── snakebids.yml        # Snakebids configuration
├── workflow/
│   ├── Snakefile            # Main Snakemake workflow
│   └── rules/
│       ├── anatomy.smk      # FastSurfer, HippUnfold, cortical surface rules
│       ├── pet.smk          # PET processing rules
│       └── report.smk       # Report generation rules
├── functions/               # Processing scripts called by rules
│   ├── fastsurfer.py
│   ├── hippunfold.py
│   ├── cortical_surface.py
│   ├── gtm_seg.py
│   ├── linear_coreg.py
│   ├── pvc.py
│   ├── suvr.py
│   ├── project_pet_data.py
│   ├── subcortical_map.py
│   ├── clinical_reports.py
│   └── utils.py
├── surfaces/                # Reference surface files
├── tests/                   # Test suite
│   └── test_snakebids_config.py
├── environment.yml          # Conda environment specification
├── test_pipeline.sh         # Server test script
└── README.md
```

## Pipeline Steps

The pipeline executes the following steps:

1. **FastSurfer** (`rule fastsurfer`)
   - Runs FastSurfer for cortical reconstruction
   - Outputs: surfaces, segmentations, norm.mgz, etc.

2. **HippUnfold** (`rule hippunfold`)
   - Runs HippUnfold for hippocampal surface extraction
   - Outputs: hippocampal midthickness surfaces

3. **Cortical Surface** (`rule cortical_surface`)
   - Converts FreeSurfer surfaces to fsLR space
   - Outputs: fsLR-32k surfaces

4. **GTM Segmentation** (`rule gtm_seg`)
   - Creates geometric transfer matrix segmentation
   - Outputs: gtmseg.mgz

5. **Linear Coregistration** (`rule linear_coreg`)
   - Registers PET to T1w anatomical image
   - Outputs: transformation files, coregistered PET

6. **Partial Volume Correction** (`rule pvc`)
   - Applies RBV partial volume correction
   - Outputs: PVC-corrected PET images

7. **SUVR Calculation** (`rule suvr`)
   - Calculates Standardized Uptake Value Ratio
   - Outputs: SUVR images

8. **Project PET Data** (`rule project_pet_data`)
   - Projects PET data to cortical and hippocampal surfaces
   - Outputs: .func.gii surface data files

9. **Subcortical Map** (`rule subcortical_map`)
   - Extracts mean values from subcortical ROIs
   - Outputs: CSV files with ROI values

10. **Clinical Report** (`rule clinical_report`)
    - Generates HTML report with visualizations
    - Outputs: HTML report

## Testing

### Run Local Tests

```bash
# Run pytest (requires pytest and pyyaml)
pytest tests/test_snakebids_config.py -v
```

### Run Server Test Script

On the BIC server (login.bic.mni.mcgill.ca):

```bash
# Activate conda environment
conda activate snakebids

# Navigate to project directory
cd ~/Documents/micapet

# Pull latest changes
git pull

# Run dry run
./test_pipeline.sh

# Run actual pipeline
./test_pipeline.sh --run
```

## Input Data Requirements

The pipeline expects BIDS-formatted data with:

- **T1w anatomical images**: `sub-<label>/ses-<label>/anat/sub-<label>_ses-<label>_T1w.nii.gz`
- **FDG PET images**: `sub-<label>/ses-<label>/pet/sub-<label>_ses-<label>_trc-FDG_pet.nii.gz`

## Output Structure

Outputs are organized under the output directory:

```
output_dir/
├── fastsurfer/              # FastSurfer outputs
├── hippunfold_v1.4.1/       # HippUnfold outputs
├── MICA-PET_v.alpha.0.3/    # MICA-PET derivatives
│   └── sub-<label>/
│       └── ses-<label>/
│           ├── pet/         # Processed PET images
│           └── surf/        # Surface projections
├── qc/                      # Quality control outputs
│   └── sub-<label>_ses-<label>_report.html
└── logs/                    # Processing logs
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the tests
5. Submit a pull request

## References

- [Snakebids](https://github.com/khanlab/snakebids) - BIDS App framework
- [Snakemake](https://snakemake.readthedocs.io/) - Workflow management
- [FastSurfer](https://github.com/Deep-MI/FastSurfer) - Fast cortical reconstruction
- [HippUnfold](https://github.com/khanlab/hippunfold) - Hippocampal unfolding

## License

This project is licensed under the GPL v3 License - see the [LICENSE](LICENSE) file for details.

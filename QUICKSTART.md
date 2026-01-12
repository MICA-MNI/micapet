# MICAPET Snakebids Pipeline - Quick Start Guide

## ✅ Path Verification Complete!

All required paths have been verified on the server:
- ✓ BIDS Directory
- ✓ FastSurfer Image
- ✓ HippUnfold Image  
- ✓ FreeSurfer License
- ✓ HippUnfold Cache
- ✓ Example Subject (PX003)

## Running the Pipeline

### 1. Activate the environment
```bash
conda activate micapet
```

### 2. Install snakebids (if not already installed)
```bash
pip install snakebids
```

### 3. Test with Dry Run (recommended first)
```bash
./test_pipeline.sh
```

This will run with the `-n` flag to show what would be executed without actually running it.

### 4. Run the Pipeline for Real

Edit `test_pipeline.sh` and remove the `-n` flag from line 38, or run directly:

```bash
./run.py \
    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG \
    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG/derivatives \
    participant \
    --participant_label PX003 \
    --fastsurfer_img /host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif \
    --hippunfold_img /host/verges/tank/data/jack/hippunfold_v1.4.1.sif \
    --fs_license /host/verges/tank/data/jack/license.txt \
    --hippunfold_cache_dir /host/verges/tank/data/jack/hippunfold_tmp \
    --psf 4.5 \
    --ref_region pons \
    -c 1
```

### 5. Run with More Cores (recommended for production)
```bash
./run.py \
    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG \
    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG/derivatives \
    participant \
    --participant_label PX003 \
    --fastsurfer_img /host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif \
    --hippunfold_img /host/verges/tank/data/jack/hippunfold_v1.4.1.sif \
    --fs_license /host/verges/tank/data/jack/license.txt \
    --hippunfold_cache_dir /host/verges/tank/data/jack/hippunfold_tmp \
    --psf 4.5 \
    --ref_region pons \
    -c 8
```

### 6. Process Multiple Subjects
```bash
./run.py \
    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG \
    /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG/derivatives \
    participant \
    --participant_label PX003 PX004 PX005 \
    --fastsurfer_img /host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif \
    --hippunfold_img /host/verges/tank/data/jack/hippunfold_v1.4.1.sif \
    --fs_license /host/verges/tank/data/jack/license.txt \
    --hippunfold_cache_dir /host/verges/tank/data/jack/hippunfold_tmp \
    --psf 4.5 \
    --ref_region pons \
    -c 16
```

## Expected Output

The pipeline will generate:
- `derivatives/fastsurfer/` - Cortical surface reconstructions
- `derivatives/hippunfold_v1.4.1/` - Hippocampal surfaces
- `derivatives/MICA-PET_v.alpha.0.3/` - PET derivatives (coregistration, PVC, SUVR)
- `qc/` - Quality control reports (HTML)

## Troubleshooting

If you encounter errors:
1. Check the log files in the `logs/` directory
2. Verify Snakemake is running: `snakemake --version`
3. Ensure snakebids is installed: `pip show snakebids`
4. Run with verbose mode: add `--verbose` flag

## Notes

- The first run will take the longest (FastSurfer ~1-2 hours per subject)
- Subsequent runs will skip completed steps (Snakemake dependency tracking)
- Use SLURM for production runs with many subjects

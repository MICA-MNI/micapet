# Test Scripts for MICA-PET

This directory contains test scripts designed to be run on the BIC server, specifically in `/export03` directories (not in home).

## Server Access

```bash
ssh eyang@login.bic.mni.mcgill.ca
ssh bb-compxg-01
cd /export03/data/enning/micapet
```

## Test Scripts

### `test_redirect.sh`

Tests the redirect/symbolic link feature for using existing FreeSurfer and HippUnfold outputs without rerunning them.

**Purpose:** Handle cases like the MICs dataset where FreeSurfer and HippUnfold have already been run, and we want to use those existing outputs.

**Before running:**
1. Update the paths for `EXISTING_FREESURFER_DIR` and `EXISTING_HIPPUNFOLD_DIR`
2. Verify the paths to the MICs dataset
3. Ensure the singularity image exists at the specified location

**Usage:**
```bash
cd /export03/data/enning/micapet
bash test_script/test_redirect.sh
```

## Implementation Notes

The redirect feature will work by:
1. Creating symbolic links from the pipeline's expected output directories to existing outputs
2. Snakemake will detect that the output files already exist and skip those steps
3. The pipeline will continue with only the PET processing steps that are needed

## Directory Structure

All test outputs should go to `/export03` (not home directory) to ensure proper storage allocation and performance.

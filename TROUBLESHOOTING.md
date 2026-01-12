# Fix for Python 2.7 Environment Issue

Your current `micapet` conda environment is using Python 2.7 instead of Python 3.10 as specified in `environment.yml`.

## Solution: Recreate the environment

Run these commands on the server:

```bash
# Remove the old environment
conda deactivate
conda env remove -n micapet

# Recreate with the correct Python version
conda env create -f environment.yml

# Activate the new environment
conda activate micapet

# Verify Python version (should be 3.10.x)
python --version

# Verify snakebids is installed
python -c "import snakebids; print(snakebids.__version__)"
```

## Why this happened

The existing `micapet` environment was created with Python 2.7, possibly from an older version of the `environment.yml` file. Conda doesn't automatically update the Python version when you update the environment file.

## After recreating the environment

You can then run the pipeline:

```bash
./test_pipeline.sh
```

Or directly:

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

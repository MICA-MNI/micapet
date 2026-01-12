#!/bin/bash

# Hardcoded paths based on the provided information
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"
FASTSURFER_IMG="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_IMG="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"
HIPP_CACHE="/host/verges/tank/data/jack/hippunfold_tmp"
SUBJECT_LABEL="PX003" # Example subject

# Verify basic existence (Note: This only works if mounted locally. 
# If running on a different node/container, these paths must be accessible there.)
echo "Checking paths..."
for path in "$BIDS_DIR" "$FASTSURFER_IMG" "$HIPPUNFOLD_IMG" "$FS_LICENSE" "$HIPP_CACHE"; do
    if [ ! -e "$path" ]; then
        echo "WARNING: Path does not exist locally: $path"
        echo "Ensure you are running this script on the server where these paths are valid or inside the appropriate container bound to these paths."
    else
        echo "Found: $path"
    fi
done

echo "Running micapet pipeline (Dry Run)..."

# Run snakebids app
# We use -n for dry-run. Remove it to actually execute.
./run.py \
    "$BIDS_DIR" \
    "$BIDS_DIR/derivatives" \
    participant \
    --participant_label "$SUBJECT_LABEL" \
    --fastsurfer_img "$FASTSURFER_IMG" \
    --hippunfold_img "$HIPPUNFOLD_IMG" \
    --fs_license "$FS_LICENSE" \
    --hippunfold_cache_dir "$HIPP_CACHE" \
    --psf 4.5 \
    --ref_region pons \
    -n

echo "---------------------------------------------------"
echo "To run the pipeline for real, remove '-n' from the command above."
echo "If you are running this on the login node or via slurm, ensure appropriate resources are allocated."

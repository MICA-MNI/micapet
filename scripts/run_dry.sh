#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Dry Run (SIF)
# ============================================================================
# Tests the pipeline logic without running heavy processing (-n flag).

# --- 1. Define Paths ---
# Inputs
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_PET_test"

# Outputs (Snakebids app requires an output directory argument)
# MOVED to Enning's space for write access
OUTPUT_DIR="/host/cassio/export03/data/enning/micapet/micapet_output"
HIPP_CACHE="/host/cassio/export03/data/enning/micapet/hippunfold_cache"

# Container Images
SIF_PATH="/host/cassio/export03/data/enning/micapet_snakebids.sif"
FASTSURFER_SIF="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"

# Parameters
PARTICIPANT_LABEL="MCH001"

echo "Running Snakebids DRY RUN..."
echo "SIF Image: $SIF_PATH"
echo "BIDS Dir:  $BIDS_DIR"
echo "Output:    $OUTPUT_DIR"
echo "Cache:     $HIPP_CACHE"
echo "---------------------------------------------------------"

# --- 2. Run Singularity ---
# Runs the SIF as an executable (BIDS App format)
singularity run --cleanenv \
    -B /host:/host \
    "$SIF_PATH" \
    "$BIDS_DIR" \
    "$OUTPUT_DIR" \
    participant \
    --participant_label "$PARTICIPANT_LABEL" \
    --fastsurfer-img "$FASTSURFER_SIF" \
    --hippunfold-img "$HIPPUNFOLD_SIF" \
    --fs-license "$FS_LICENSE" \
    --hippunfold-cache-dir "$HIPP_CACHE" \
    --psf 4.5 \
    --ref-region pons \
    -n  # <--- DRY RUN FLAG

echo "---------------------------------------------------------"
echo "Dry run complete."
echo "If the rule listing looks correct, run './run_wet.sh' to execute."

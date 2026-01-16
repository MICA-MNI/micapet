#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Dry Run (SIF)
# ============================================================================
# Tests the pipeline logic without running heavy processing (-n flag).

# --- 1. Define Paths ---
# ROOT PATH: Moving all data/images here for speed
DATA_ROOT="/export03/data/enning/micapet"

# Inputs
BIDS_DIR="$DATA_ROOT/BIDS_PET_test"

# Outputs
OUTPUT_DIR="$DATA_ROOT/micapet_output"
HIPP_CACHE="$DATA_ROOT/hippunfold_cache"

# Container Images & License
SIF_PATH="$DATA_ROOT/micapet_snakebids.sif"
FASTSURFER_SIF="$DATA_ROOT/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="$DATA_ROOT/hippunfold_v1.4.1.sif"
FS_LICENSE="$DATA_ROOT/license.txt"

# Parameters
PARTICIPANT_LABEL="MCH001"

echo "Running Snakebids DRY RUN..."
echo "Data Root: $DATA_ROOT"
echo "SIF Image: $SIF_PATH"
echo "BIDS Dir:  $BIDS_DIR"
echo "Output:    $OUTPUT_DIR"
echo "Cache:     $HIPP_CACHE"
echo "---------------------------------------------------------"

# --- 2. Run Singularity ---
# Runs the SIF as an executable (BIDS App format)
# Note: Binding /export03 to access data files
# Note: Binding $HOME to write snakemake cache
singularity run --cleanenv \
    -B /export03:/export03 \
    -B $HOME \
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

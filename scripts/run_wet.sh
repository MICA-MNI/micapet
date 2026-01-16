#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Wet Run (Execution)
# ============================================================================
# Executes the pipeline on the server.

# --- 1. Define Paths ---
# HOST_ROOT: The actual path on the server
HOST_ROOT="/export03/data/enning/micapet"

# Inputs
BIDS_DIR="$HOST_ROOT/BIDS_PET_test"

# Outputs
OUTPUT_DIR="$HOST_ROOT/micapet_output"
HIPP_CACHE="$HOST_ROOT/hippunfold_cache"

# Container Images & License
SIF_PATH="$HOST_ROOT/micapet_snakebids.sif"
FASTSURFER_SIF="$HOST_ROOT/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="$HOST_ROOT/hippunfold_v1.4.1.sif"
FS_LICENSE="$HOST_ROOT/license.txt"

# Parameters
PARTICIPANT_LABEL="MCH001"
CORES=8

echo "STARTING PIPELINE EXECUTION..."
echo "Root:    $HOST_ROOT"
echo "BIDS:    $BIDS_DIR"
echo "Output:  $OUTPUT_DIR"
echo "---------------------------------------------------------"

# Verify existence
if [ ! -d "$BIDS_DIR" ]; then
    echo "ERROR: BIDS Directory not found at $BIDS_DIR"
    exit 1
fi

# --- 2. Run Singularity ---
# STRATEGY: Bind the parent /export03 directly to /export03.
singularity run --cleanenv \
    -B /export03:/export03 \
    --env XDG_CACHE_HOME="$HOST_ROOT/.cache" \
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
    --cores $CORES

echo "---------------------------------------------------------"
echo "Pipeline finished."

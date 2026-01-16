#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Dry Run (SIF)
# ============================================================================
# Tests the pipeline logic without running heavy processing (-n flag).

# --- 1. Define Paths ---
# HOST_ROOT: The directory on the server containing your data
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

echo "Running Snakebids DRY RUN..."
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
# This mimics the working 'jack' setup (-B /host:/host) but scoped to your data.
# This prevents path confusion or symlink issues inside the container.

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
    -n  # <--- DRY RUN FLAG

echo "---------------------------------------------------------"
echo "Dry run complete."
echo "If the rule listing looks correct, run './run_wet.sh' to execute."

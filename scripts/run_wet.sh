#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Wet Run (Execution)
# ============================================================================
# Executes the pipeline on the server.

# --- 1. Define Paths ---
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_PET_test"

# Outputs (Moved to Enning's space for write access)
OUTPUT_DIR="/host/cassio/export03/data/enning/micapet/micapet_output"
HIPP_CACHE="/host/cassio/export03/data/enning/micapet/hippunfold_cache"

SIF_PATH="/host/cassio/export03/data/enning/micapet_snakebids.sif"
FASTSURFER_SIF="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"

# Parameters
PARTICIPANT_LABEL="MCH001"
CORES=8

echo "STARTING PIPELINE EXECUTION..."
echo "SIF Image: $SIF_PATH"
echo "BIDS Dir:  $BIDS_DIR"
echo "Output:    $OUTPUT_DIR"
echo "Cache:     $HIPP_CACHE"
echo "---------------------------------------------------------"

# --- 2. Run Singularity ---
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
    --cores $CORES

echo "---------------------------------------------------------"
echo "Pipeline finished."

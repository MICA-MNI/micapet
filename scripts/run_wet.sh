#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Wet Run (Execution)
# ============================================================================
# Executes the pipeline on the server.

# --- 1. Define Paths ---
# HOST_ROOT: Using the FULL PHYSICAL PATH to avoid symlink binding issues
HOST_ROOT="/host/cassio/export03/data/enning/micapet"

# CONTAINER_ROOT: Where we mount it inside the image
# (Using a simple path avoids symlink/mount issues)
CONT_ROOT="/micapet_data"

# Inputs (Inside Container)
BIDS_DIR="$CONT_ROOT/BIDS_PET_test"

# Outputs (Inside Container)
OUTPUT_DIR="$CONT_ROOT/micapet_output"
HIPP_CACHE="$CONT_ROOT/hippunfold_cache"

# Container Images & License (Inside Container)
SIF_NAME="micapet_snakebids.sif"
FASTSURFER_SIF="$CONT_ROOT/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="$CONT_ROOT/hippunfold_v1.4.1.sif"
FS_LICENSE="$CONT_ROOT/license.txt"

# Parameters
PARTICIPANT_LABEL="MCH001"
CORES=8

echo "STARTING PIPELINE EXECUTION..."
echo "Host Root:      $HOST_ROOT"
echo "Container Root: $CONT_ROOT"
echo "BIDS Dir:       $BIDS_DIR"
echo "Output:         $OUTPUT_DIR"
echo "---------------------------------------------------------"

# --- 2. Run Singularity ---
# Bind $HOST_ROOT -> $CONT_ROOT
# Pass arguments using $CONT_ROOT paths
singularity run --cleanenv \
    -B "$HOST_ROOT:$CONT_ROOT" \
    --env XDG_CACHE_HOME="$CONT_ROOT/.cache" \
    "$HOST_ROOT/$SIF_NAME" \
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

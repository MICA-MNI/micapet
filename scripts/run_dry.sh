#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Dry Run (SIF)
# ============================================================================
# Tests the pipeline logic without running heavy processing (-n flag).

# --- 1. Define Paths ---
# HOST_ROOT: The directory on the server containing your data
HOST_ROOT="/export03/data/enning/micapet"

# Inputs (Using Jack's shared data for reliability)
# Note: We use Jack's BIDS directory and Container Images as they represent a known-good state.
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"

# Outputs (Stored in your user directory)
OUTPUT_DIR="$HOST_ROOT/micapet_output"
HIPP_CACHE="$HOST_ROOT/hippunfold_cache"

# Container Images & License
# We use the Snakebids image you built, but external tools (FastSurfer/HippUnfold) from Jack's path
SIF_PATH="$HOST_ROOT/micapet_snakebids.sif"
FASTSURFER_SIF="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"

# Parameters
# Using a subject known to exist in Jack's dataset (e.g. PX003)
PARTICIPANT_LABEL="PX003"

echo "Running Snakebids DRY RUN..."
echo "Root:    $HOST_ROOT"
echo "BIDS:    $BIDS_DIR"
echo "Output:  $OUTPUT_DIR"
echo "---------------------------------------------------------"

# Verify existence
if [ ! -d "$BIDS_DIR" ]; then
    echo "ERROR: BIDS Directory not found at $BIDS_DIR"
    echo "Please ensure /host is mounted and accessible."
    exit 1
fi

# --- 2. Run Singularity ---
# STRATEGY: 
#   - Bind /host:/host to reach Jack's data, and /export03 for your data.
#   - Bind the host's singularity/apptainer binary into the container so nested
#     container calls (hippunfold, fastsurfer) can work.

# Find the singularity or apptainer executable on the host
SINGULARITY_BIN=$(which singularity 2>/dev/null || which apptainer 2>/dev/null || echo "")
if [ -z "$SINGULARITY_BIN" ]; then
    echo "ERROR: Neither singularity nor apptainer found on host!"
    exit 1
fi
SINGULARITY_DIR=$(dirname "$SINGULARITY_BIN")
echo "Found Singularity/Apptainer at: $SINGULARITY_BIN"

# Also need to bind the libexec directory for singularity helpers
SINGULARITY_LIBEXEC=""
if [ -d "/usr/libexec/singularity" ]; then
    SINGULARITY_LIBEXEC="-B /usr/libexec/singularity:/usr/libexec/singularity"
elif [ -d "/usr/libexec/apptainer" ]; then
    SINGULARITY_LIBEXEC="-B /usr/libexec/apptainer:/usr/libexec/apptainer"
fi

singularity run --cleanenv \
    -B /host:/host \
    -B /export03:/export03 \
    -B "$SINGULARITY_DIR:$SINGULARITY_DIR" \
    $SINGULARITY_LIBEXEC \
    --env PATH="$SINGULARITY_DIR:\$PATH" \
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

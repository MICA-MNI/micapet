#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Wet Run (Execution)
# ============================================================================
# Executes the pipeline on the server.

# --- 1. Define Paths ---
# HOST_ROOT: The actual path on the server
HOST_ROOT="/export03/data/enning/micapet"

# Inputs (Using Jack's shared data for reliability)
# Note: We use Jack's BIDS directory and Container Images as they represent a known-good state.
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"

# Outputs (Stored in your user directory)
OUTPUT_DIR="$HOST_ROOT/micapet_output"
# Use Jack's hippunfold cache (already has downloaded models)
HIPP_CACHE="/host/verges/tank/data/jack/hippunfold_tmp"

# Container Images & License
# We use the Snakebids image you built, but external tools (FastSurfer/HippUnfold) from Jack's path
SIF_PATH="$HOST_ROOT/micapet_snakebids.sif"
FASTSURFER_SIF="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"

# Parameters
PARTICIPANT_LABEL="PX003"
# Use more cores to allow parallel jobs
# FastSurfer uses ~8 threads, HippUnfold uses ~8 threads
# With 16+ cores, both can run in parallel
CORES=32

echo "STARTING PIPELINE EXECUTION..."
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

# Create required output directories (prevents mount errors inside nested containers)
mkdir -p "$OUTPUT_DIR"
mkdir -p "$HIPP_CACHE"
mkdir -p "$HOST_ROOT/.cache"

# --- 2. Run Singularity ---
# STRATEGY: 
#   - Bind /host:/host to reach Jack's data, and /export03 for your data.
#   - apptainer is already installed inside the container at /usr/local/bin/apptainer
#   - so nested container calls will work without binding host binaries

echo "Launching container..."

# Get the project root on the host (where we pulled the latest code)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Script dir:    $SCRIPT_DIR"
echo "Project root:  $PROJECT_ROOT"
echo "Binding:       $PROJECT_ROOT/functions -> /app/functions"

# Verify functions directory exists
if [ ! -d "$PROJECT_ROOT/functions" ]; then
    echo "ERROR: Functions directory not found at $PROJECT_ROOT/functions"
    exit 1
fi

singularity run --cleanenv \
    -B /host:/host \
    -B /export03:/export03 \
    -B "$PROJECT_ROOT/functions:/app/functions" \
    -B "$PROJECT_ROOT/workflow:/app/workflow" \
    -B "$PROJECT_ROOT/config:/app/config" \
    -B "$PROJECT_ROOT/run.py:/app/run.py" \
    --env XDG_CACHE_HOME="$HOST_ROOT/.cache" \
    --env PYTHONUNBUFFERED=1 \
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
    --cores $CORES \
    --rerun-incomplete \
    --printshellcmds \
    --reason

echo "---------------------------------------------------------"
echo "Pipeline finished."

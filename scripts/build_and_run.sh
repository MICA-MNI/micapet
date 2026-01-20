#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Build & Run Legacy (Direct Script Execution)
# ============================================================================
# This script builds the SIF image and runs the pipeline using the "legacy" 
# direct execution method (01_master.py) instead of Snakebids.
# It mimics the workflow used by Jack but points inputs/outputs to the correct locations.

# --- Configuration ---
IMAGE_NAME="micapet_original"
TAG="latest"
SIF_NAME="micapet_original.sif"
export DOCKER_CONTENT_TRUST=0

# PATHS
# Use /export03/data/enning/micapet as the workspace
HOST_STORAGE="/export03/data/enning/micapet"
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"
OUTPUT_DIR="$HOST_STORAGE/micapet_output_legacy"

# RESOURCES (Jack's Paths)
FASTSURFER_SIF="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"
HIPP_CACHE="/host/verges/tank/data/jack/hippunfold_tmp"

# Location of the FreeSurfer tarball required for Docker build
FS_TAR_PATH="/host/fladgate/local_raid/jack/FDG/MICA-PET/scripts/freesurfer-linux-centos7_x86_64-7.4.1.tar.gz"
FS_TAR_NAME="freesurfer-linux-centos7_x86_64-7.4.1.tar.gz"

# --- 1. Build SIF Image ---
echo "=========================================="
echo "Step 1: Building Docker Image..."
echo "=========================================="

# Check if FS tarball exists locally, if not symlink it from Jack's path
if [ ! -f "$FS_TAR_NAME" ]; then
    if [ -f "$FS_TAR_PATH" ]; then
        echo "Symlinking FreeSurfer tarball from Jack's path..."
        ln -sf "$FS_TAR_PATH" .
    else
        echo "ERROR: FreeSurfer tarball not found at $FS_TAR_PATH"
        echo "The Docker build requires this file."
        exit 1
    fi
fi

docker build -t $IMAGE_NAME:$TAG .

# Clean up the large tarball link after build
rm "$FS_TAR_NAME"

echo "=========================================="
echo "Step 2: Converting to SIF..."
echo "=========================================="
# Remove old SIF if exists to ensure we use the new one
rm -f "$HOST_STORAGE/$SIF_NAME"

# Build SIF from Docker daemon
singularity build "$HOST_STORAGE/$SIF_NAME" "docker-daemon://$IMAGE_NAME:$TAG"

# --- 2. Prepare Directories ---
echo "=========================================="
echo "Step 3: Preparing Directories..."
echo "=========================================="
mkdir -p "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/fastsurfer"
mkdir -p "$OUTPUT_DIR/hippunfold"
mkdir -p "$OUTPUT_DIR/micapet"
mkdir -p "$OUTPUT_DIR/tmp"
mkdir -p "$HOST_STORAGE/.cache"

echo "Output Directory: $OUTPUT_DIR"

# --- 3. Run Pipeline ---
echo "=========================================="
echo "Step 4: Running Pipeline (Legacy Mode)..."
echo "=========================================="

# We use 'singularity exec' to bypass the 'run.py' entrypoint and run '01_master.py' directly.
# We also bind the local 'functions/' directory so the container runs the latest python code
# (specifically the version with the new -out_dir argument).
#time the running process
start_time=$(date +%s)

singularity exec --cleanenv \
    -B /host:/host \
    -B /export03:/export03 \
    -B "$(pwd)/functions:/app/functions" \
    --env FS_LICENSE="$FS_LICENSE" \
    --env PYTHONUNBUFFERED=1 \
    --env XDG_CACHE_HOME="$HOST_STORAGE/.cache" \
    "$HOST_STORAGE/$SIF_NAME" \
    conda run -n mica-pet python /app/functions/01_master.py \
    -sub PX003 \
    -ses 01 \
    -bids "$BIDS_DIR" \
    -out_dir "$OUTPUT_DIR/micapet" \
    -fastsurfer_img "$FASTSURFER_SIF" \
    -fs_license "$FS_LICENSE" \
    -hippunfold_img "$HIPPUNFOLD_SIF" \
    -hippunfold_dir "$OUTPUT_DIR/hippunfold" \
    -subj_dir "$OUTPUT_DIR/fastsurfer" \
    -tmpdir "$OUTPUT_DIR/tmp" \
    -cachedir "$HIPP_CACHE" \
    -psf 4.5 \
    -ref_region pons \
    -force

end_time=$(date +%s)
elapsed=$(( end_time - start_time ))
echo "Pipeline completed in $elapsed seconds."
echo "=========================================="
echo "Pipeline Finished."
echo "=========================================="

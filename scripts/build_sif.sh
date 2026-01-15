#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Build SIF Image
# ============================================================================
# This script builds the Docker image and then converts it to a Singularity (SIF)
# image, ensuring the Singularity cache is located on large storage to avoid
# "disk quota exceeded" errors.

# --- Configuration ---
IMAGE_NAME="micapet_snakebids"
TAG="latest"
SIF_NAME="micapet_snakebids.sif"

# PATHS: Adjust these to your large storage location
# UPDATED: Using faster storage path
HOST_STORAGE="/export03/data/enning/micapet"
EXPORT_DIR="$HOST_STORAGE"  # Where to save the final .sif
CACHE_DIR="$HOST_STORAGE/singularity_cache"
TMP_DIR="$HOST_STORAGE/singularity_tmp"

# Helper to find project root regardless of where script is run
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "====================================================================="
echo "1. Building Docker Image..."
echo "====================================================================="
# Builds the image tagged 'micapet_snakebids:latest' from the Dockerfile in project root
docker build -t ${IMAGE_NAME}:${TAG} "$PROJECT_ROOT"


echo ""
echo "====================================================================="
echo "2. Setting up Singularity Cache on Host..."
echo "====================================================================="
# Create directories if they don't exist
mkdir -p "$EXPORT_DIR" "$CACHE_DIR" "$TMP_DIR"

# Export variables to redirect Singularity's cache usage
export SINGULARITY_CACHEDIR="$CACHE_DIR"
export SINGULARITY_TMPDIR="$TMP_DIR"

echo "Using Cache Dir: $SINGULARITY_CACHEDIR"
echo "Using Tmp Dir:   $SINGULARITY_TMPDIR"


echo ""
echo "====================================================================="
echo "3. Building Singularity SIF..."
echo "====================================================================="
SIF_PATH="$EXPORT_DIR/$SIF_NAME"

# Clean up previous build if exists
if [ -f "$SIF_PATH" ]; then
    echo "Found old SIF, removing: $SIF_PATH"
    rm "$SIF_PATH"
fi

echo "Converting docker-daemon://${IMAGE_NAME}:${TAG} -> $SIF_PATH"
singularity build "$SIF_PATH" docker-daemon://${IMAGE_NAME}:${TAG}

echo ""
echo "====================================================================="
echo "SUCCESS! SIF Image is ready: $SIF_PATH"
echo "====================================================================="

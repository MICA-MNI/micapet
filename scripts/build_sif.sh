#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Build SIF Image
# ============================================================================
# Usage: ./build_sif.sh [--skip-docker]
#
# This script builds the Docker image and then converts it to a Singularity (SIF)
# image. Use --skip-docker to only rebuild the SIF from an existing Docker image.

# --- Argument Parsing ---
SKIP_DOCKER=false
if [[ "$1" == "--skip-docker" ]]; then
    SKIP_DOCKER=true
fi

# --- Configuration ---
# Fix for "remote trust data does not exist" error
export DOCKER_CONTENT_TRUST=0

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

if [ "$SKIP_DOCKER" = true ]; then
    echo "Skipping Docker build (--skip-docker was set)."
else
    echo "====================================================================="
    echo "1. Building Docker Image..."
    echo "====================================================================="
    # Builds the image tagged 'micapet_snakebids:latest' from the Dockerfile in project root
    docker build -t ${IMAGE_NAME}:${TAG} "$PROJECT_ROOT"
fi


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

# STRATEGY CHANGE: 
# The Docker daemon on the server seems to run out of space in /export01/docker/tmp
# when attempting a direct stream to Singularity (docker-daemon://).
# Workaround: Save to a tarball on the large partition (/export03) first.

TAR_PATH="$EXPORT_DIR/${IMAGE_NAME}.tar"

echo "1. Saving Docker image to tarball on large storage..."
echo "   Path: $TAR_PATH"
docker save "${IMAGE_NAME}:${TAG}" -o "$TAR_PATH"

echo "2. Converting docker-archive tarball -> SIF..."
singularity build "$SIF_PATH" "docker-archive://$TAR_PATH"

echo "3. Cleaning up tarball..."
rm "$TAR_PATH"

echo ""
echo "====================================================================="
echo "SUCCESS! SIF Image is ready: $SIF_PATH"
echo "====================================================================="

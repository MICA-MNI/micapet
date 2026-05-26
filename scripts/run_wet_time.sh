#!/bin/bash
set -e

# --- Configuration ---
IMAGE_NAME="micapet_original"
TAG="latest"
SIF_NAME="micapet_original.sif"
export DOCKER_CONTENT_TRUST=0

# PATHS
HOST_STORAGE="/export03/data/enning/micapet"
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"
OUTPUT_DIR="$HOST_STORAGE/micapet_output_wet_optmization"

# --- 1. Prepare Output Directory ---

# --- 2. Run Pipeline with Timing ---
echo "=========================================="
echo "Step 1: Running Pipeline (Wet Mode, Timed)..."
echo "=========================================="

start_time=$(date +%s)

bash scripts/run_wet.sh "$OUTPUT_DIR" 

end_time=$(date +%s)
elapsed=$(( end_time - start_time ))
echo "Pipeline completed in $elapsed seconds." | tee -a "$OUTPUT_DIR/pipeline_run.log"
echo $elapsed > "$OUTPUT_DIR/elapsed_seconds.txt"
echo "=========================================="
echo "Pipeline Finished. Time recorded in $OUTPUT_DIR/elapsed_seconds.txt"
echo "=========================================="

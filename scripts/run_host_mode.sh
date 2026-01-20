#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Run WITHOUT the outer container (Host Mode)
# ============================================================================
# This script runs the pipeline directly on the host using a conda environment,
# avoiding the "nested container" problem entirely.
#
# REQUIREMENTS:
#   - Conda installed on the server
#   - The 'micapet' conda environment (will be created if missing)
#   - Singularity/Apptainer available on the host
# ============================================================================

# --- 1. Define Paths ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Data paths
HOST_ROOT="/export03/data/enning/micapet"
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"
OUTPUT_DIR="$HOST_ROOT/micapet_output"
HIPP_CACHE="$HOST_ROOT/hippunfold_cache"

# External container images (from Jack's shared location)
FASTSURFER_SIF="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"

# Parameters
PARTICIPANT_LABEL="PX003"
CORES=8

# --- 2. Check/Create Conda Environment ---
ENV_NAME="micapet"

echo "====================================================================="
echo "MICA-PET: Host Mode Execution"
echo "====================================================================="
echo "Project Root: $PROJECT_ROOT"
echo "BIDS Dir:     $BIDS_DIR"
echo "Output Dir:   $OUTPUT_DIR"
echo "---------------------------------------------------------------------"

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "ERROR: Conda not found. Please install or load conda first."
    exit 1
fi

# Check if environment exists, create if not
if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo "Creating conda environment '$ENV_NAME'..."
    conda env create -n "$ENV_NAME" -f "$PROJECT_ROOT/environment.yml"
fi

# --- 3. Run the Pipeline ---
echo ""
echo "Activating conda environment and running pipeline..."
echo "---------------------------------------------------------------------"

# Use conda run to execute in the environment
conda run -n "$ENV_NAME" python "$PROJECT_ROOT/run.py" \
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
    --cores "$CORES"

echo ""
echo "====================================================================="
echo "Pipeline finished."
echo "====================================================================="

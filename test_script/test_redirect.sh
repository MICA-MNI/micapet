#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Test Script for Redirect/Symbolic Link Feature
# ============================================================================
# This script tests the ability to use existing FreeSurfer and HippUnfold
# outputs without rerunning them, by using the --existing-* parameters.
#
# Run on server:
#   ssh eyang@login.bic.mni.mcgill.ca
#   ssh bb-compxg-01
#   cd /export03/data/enning/micapet
#   bash test_script/test_redirect.sh

# --- 1. Define Paths ---
# HOST_ROOT: The actual path on the server (in /export03, not home)
HOST_ROOT="/export03/data/enning/micapet"

# Inputs - Using MICs dataset with existing FreeSurfer/HippUnfold outputs
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"

# EXISTING OUTPUTS (UPDATE THESE PATHS)
# Example: If you have existing outputs from a previous run or different pipeline
EXISTING_FREESURFER_DIR=""  # e.g., "/path/to/MICs/derivatives/fastsurfer"
EXISTING_HIPPUNFOLD_DIR=""  # e.g., "/path/to/MICs/derivatives/hippunfold_v1.4.1"

# Outputs (Test output directory in /export03)
OUTPUT_DIR="$HOST_ROOT/test_redirect_output"

# Container Images & License
SIF_PATH="$HOST_ROOT/micapet_snakebids.sif"
FASTSURFER_SIF="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"

# Test Parameters
PARTICIPANT_LABEL="PX001"  # Use a subject with existing outputs
CORES=16

echo "=========================================="
echo "MICA-PET: Testing Redirect Feature"
echo "=========================================="
echo "Root:              $HOST_ROOT"
echo "BIDS:              $BIDS_DIR"
echo "Output:            $OUTPUT_DIR"
echo "Existing FS:       $EXISTING_FREESURFER_DIR"
echo "Existing HippU:    $EXISTING_HIPPUNFOLD_DIR"
echo "=========================================="

# --- 2. Verify Existence ---
if [ ! -d "$BIDS_DIR" ]; then
    echo "ERROR: BIDS Directory not found at $BIDS_DIR"
    exit 1
fi

if [ -z "$EXISTING_FREESURFER_DIR" ] && [ -z "$EXISTING_HIPPUNFOLD_DIR" ]; then
    echo "WARNING: No existing output paths provided."
    echo "Set EXISTING_FREESURFER_DIR and/or EXISTING_HIPPUNFOLD_DIR to test redirect feature."
    echo ""
fi

# Verify existing output directories if provided
if [ -n "$EXISTING_FREESURFER_DIR" ] && [ ! -d "$EXISTING_FREESURFER_DIR" ]; then
    echo "ERROR: Existing FreeSurfer directory not found at $EXISTING_FREESURFER_DIR"
    exit 1
fi

if [ -n "$EXISTING_HIPPUNFOLD_DIR" ] && [ ! -d "$EXISTING_HIPPUNFOLD_DIR" ]; then
    echo "ERROR: Existing HippUnfold directory not found at $EXISTING_HIPPUNFOLD_DIR"
    exit 1
fi

# --- 3. Create Output Directory Structure ---
mkdir -p "$OUTPUT_DIR"

# --- 4. Build Command with Redirect Parameters ---
echo ""
echo "Building pipeline command..."

REDIRECT_ARGS=""
if [ -n "$EXISTING_FREESURFER_DIR" ]; then
    REDIRECT_ARGS="$REDIRECT_ARGS --existing-freesurfer-dir $EXISTING_FREESURFER_DIR"
    echo "  Using existing FreeSurfer outputs: $EXISTING_FREESURFER_DIR"
fi

if [ -n "$EXISTING_HIPPUNFOLD_DIR" ]; then
    REDIRECT_ARGS="$REDIRECT_ARGS --existing-hippunfold-dir $EXISTING_HIPPUNFOLD_DIR"
    echo "  Using existing HippUnfold outputs: $EXISTING_HIPPUNFOLD_DIR"
fi

# --- 5. Run Pipeline ---
echo ""
echo "Launching pipeline..."
echo "Expected behavior: Pipeline should use existing outputs and skip rerunning FastSurfer/HippUnfold"
echo ""

# Get the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Run with dry-run first to see what would be executed
echo "Running dry-run to show execution plan..."
singularity run --cleanenv \
    -B /host:/host \
    -B /export03:/export03 \
    -B "$PROJECT_ROOT/functions:/app/functions" \
    -B "$PROJECT_ROOT/workflow:/app/workflow" \
    -B "$PROJECT_ROOT/config:/app/config" \
    -B "$PROJECT_ROOT/run.py:/app/run.py" \
    "$SIF_PATH" \
    "$BIDS_DIR" \
    "$OUTPUT_DIR" \
    participant \
    --participant_label "$PARTICIPANT_LABEL" \
    --fastsurfer-img "$FASTSURFER_SIF" \
    --hippunfold-img "$HIPPUNFOLD_SIF" \
    --fs-license "$FS_LICENSE" \
    $REDIRECT_ARGS \
    --cores $CORES \
    --dry-run \
    --printshellcmds \
    --reason

echo ""
echo "=========================================="
echo "Dry-run completed."
echo "Review the output above to verify that:"
echo "  1. Symbolic links were created successfully"
echo "  2. FastSurfer/HippUnfold steps are marked as 'already done'"
echo "  3. Only PET processing steps will be executed"
echo ""
echo "To run the actual pipeline, remove the --dry-run flag above."
echo "=========================================="

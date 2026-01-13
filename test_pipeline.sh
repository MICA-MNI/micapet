#!/bin/bash
set -e

# ============================================================================
# MICA-PET Pipeline Test Script
# ============================================================================
# This script tests the MICA-PET snakebids pipeline on the server.
#
# Usage:
#   ./test_pipeline.sh         # Dry run (default)
#   ./test_pipeline.sh --run   # Actual run
#
# Prerequisites:
#   - SSH access to login.bic.mni.mcgill.ca
#   - Conda environment 'snakebids' activated
#   - All paths below must be accessible
# ============================================================================

# --- Configuration ---
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"
OUTPUT_DIR="/host/cassio/export03/data/enning/micapet_output"
FASTSURFER_IMG="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_IMG="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"
HIPP_CACHE="/host/verges/tank/data/jack/hippunfold_tmp"
SUBJECT_LABEL="PX003"

# Parse command line arguments
DRY_RUN="-n"  # Default to dry run
if [ "$1" == "--run" ]; then
    DRY_RUN=""
    echo "*** ACTUAL RUN MODE - Pipeline will execute! ***"
else
    echo "*** DRY RUN MODE - Use --run to execute ***"
fi

# --- Verify paths exist ---
echo ""
echo "Checking paths..."
MISSING=0
for path in "$BIDS_DIR" "$FASTSURFER_IMG" "$HIPPUNFOLD_IMG" "$FS_LICENSE" "$HIPP_CACHE"; do
    if [ ! -e "$path" ]; then
        echo "ERROR: Path does not exist: $path"
        MISSING=1
    else
        echo "Found: $path"
    fi
done

if [ $MISSING -eq 1 ]; then
    echo ""
    echo "ERROR: Some required paths are missing!"
    echo "Ensure you are running this script on the server where these paths are valid."
    exit 1
fi

# --- Create output directory ---
if [ ! -d "$OUTPUT_DIR" ]; then
    echo ""
    echo "Creating output directory: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
else
    echo ""
    echo "Output directory exists: $OUTPUT_DIR"
fi

# --- Run pipeline ---
echo ""
echo "=============================================="
if [ -z "$DRY_RUN" ]; then
    echo "Running MICA-PET pipeline (ACTUAL RUN)..."
else
    echo "Running MICA-PET pipeline (DRY RUN)..."
fi
echo "=============================================="
echo ""
echo "Subject: $SUBJECT_LABEL"
echo "BIDS Dir: $BIDS_DIR"
echo "Output Dir: $OUTPUT_DIR"
echo ""

# Run the snakebids app with the new CLI format
python ./run.py \
    "$BIDS_DIR" \
    "$OUTPUT_DIR" \
    participant \
    --participant-label "$SUBJECT_LABEL" \
    --fastsurfer-img "$FASTSURFER_IMG" \
    --hippunfold-img "$HIPPUNFOLD_IMG" \
    --fs-license "$FS_LICENSE" \
    --hippunfold-cache-dir "$HIPP_CACHE" \
    --psf 4.5 \
    --ref-region pons \
    --threads 8 \
    $DRY_RUN

echo ""
echo "=============================================="
echo "Pipeline completed!"
if [ -z "$DRY_RUN" ]; then
    echo "Check outputs in: $OUTPUT_DIR"
else
    echo "This was a DRY RUN. Use --run to execute."
fi
echo "=============================================="
echo "To run the pipeline for real, remove '-n' from the command above."
echo "If you are running this on the login node or via slurm, ensure appropriate resources are allocated."

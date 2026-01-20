#!/bin/bash
set -e

# ============================================================================
# MICA-PET: Nightly Build & Run
# ============================================================================
# usage: bash scripts/nightly_build_and_run.sh
# 
# This script will:
# 1. Update the repository
# 2. Rebuild the Singularity/Apptainer image
# 3. Execute the full pipeline (wet run)
# ============================================================================

LOG_FILE="nightly_run_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================================="
echo " NIGHTLY JOB STARTED: $(date)"
echo " Log file: $LOG_FILE"
echo "========================================================="

echo ""
echo "--- STEP 1: GLT PULL ---"
git pull

echo ""
echo "--- STEP 2: BUILD SIF IMAGE ---"
# Check if build script exists
if [ -f "scripts/build_sif.sh" ]; then
    # Pass all arguments (like --skip-docker) to the build script
    bash scripts/build_sif.sh "$@"
else
    echo "ERROR: scripts/build_sif.sh not found!"
    exit 1
fi

echo ""
echo "--- STEP 3: EXECUTE PIPELINE (WET RUN) ---"
# Check if run script exists
if [ -f "scripts/run_wet.sh" ]; then
    bash scripts/run_wet.sh
else
    echo "ERROR: scripts/run_wet.sh not found!"
    exit 1
fi

echo ""
echo "========================================================="
echo " NIGHTLY JOB COMPLETED: $(date)"
echo "========================================================="

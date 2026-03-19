#!/bin/bash
# ============================================================================
# MICA-PET: Per-Subject PBS/qsub Job Script
# ============================================================================
# Usage (called by submit_participants.sh — do not run directly):
#   qsub -v PARTICIPANT=PX003 qsub_subject.sh
#
# Fix for race condition: each subject gets its own output directory,
# so snakebids writes config/snakebids.yml to a unique path per job
# instead of all jobs sharing the same <output_dir>/config/snakebids.yml.
# ============================================================================
#PBS -N micapet
#PBS -l nodes=1:ppn=16
#PBS -l walltime=24:00:00
#PBS -j oe
#PBS -o /export03/data/enning/micapet/logs

set -e

# --- Validate input ---
if [ -z "$PARTICIPANT" ]; then
    echo "ERROR: PARTICIPANT variable not set."
    echo "  Use: qsub -v PARTICIPANT=PX003 qsub_subject.sh"
    exit 1
fi

echo "============================================"
echo "MICA-PET Job Starting"
echo "  Participant : $PARTICIPANT"
echo "  Host        : $(hostname)"
echo "  Date        : $(date)"
echo "============================================"

# --- Paths ---
HOST_ROOT="/export03/data/enning/micapet"
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"

# KEY FIX: per-participant output directory avoids shared config/snakebids.yml.
# Snakebids writes merged config to <output_dir>/config/snakebids.yml.
# When all jobs share one output dir, concurrent writes corrupt that file.
OUTPUT_DIR="$HOST_ROOT/micapet_output/sub-${PARTICIPANT}"

HIPP_CACHE="/host/verges/tank/data/jack/hippunfold_tmp"
SIF_PATH="$HOST_ROOT/micapet_snakebids.sif"
FASTSURFER_SIF="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_SIF="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"
CORES=16

# --- Thread limits (prevent nested tools from over-subscribing cores) ---
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# --- Resolve project root from this script's location ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# --- Pre-flight checks ---
if [ ! -d "$BIDS_DIR" ]; then
    echo "ERROR: BIDS dir not found: $BIDS_DIR"
    exit 1
fi
if [ ! -f "$SIF_PATH" ]; then
    echo "ERROR: SIF not found: $SIF_PATH"
    exit 1
fi
if [ ! -d "$PROJECT_ROOT/functions" ]; then
    echo "ERROR: functions dir not found: $PROJECT_ROOT/functions"
    exit 1
fi

# --- Create directories ---
mkdir -p "$OUTPUT_DIR"
mkdir -p "$HIPP_CACHE"
mkdir -p "$HOST_ROOT/.cache"
mkdir -p "$HOST_ROOT/logs"

echo "Output dir  : $OUTPUT_DIR"
echo "Project root: $PROJECT_ROOT"
echo "--------------------------------------------"

# --- Run pipeline ---
singularity run --cleanenv \
    -B /host:/host \
    -B /export03:/export03 \
    -B "$PROJECT_ROOT/functions:/app/functions" \
    -B "$PROJECT_ROOT/workflow:/app/workflow" \
    -B "$PROJECT_ROOT/config:/app/config" \
    -B "$PROJECT_ROOT/run.py:/app/run.py" \
    -B "$PROJECT_ROOT/resources/AFNI/3dresample:/usr/local/bin/3dresample" \
    --env XDG_CACHE_HOME="$HOST_ROOT/.cache" \
    --env PYTHONUNBUFFERED=1 \
    "$SIF_PATH" \
    "$BIDS_DIR" \
    "$OUTPUT_DIR" \
    participant \
    --participant_label "$PARTICIPANT" \
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

echo "============================================"
echo "MICA-PET Job Finished: $PARTICIPANT"
echo "  Date: $(date)"
echo "============================================"

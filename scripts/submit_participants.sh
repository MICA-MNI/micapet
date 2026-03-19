#!/bin/bash
# ============================================================================
# MICA-PET: Batch qsub Submission Script
# ============================================================================
# Submits one qsub job per participant, each with its own isolated output
# directory to prevent snakebids config race conditions.
#
# Usage:
#   bash submit_participants.sh PX003 PX126 PX200 ...
#   bash submit_participants.sh $(cat participants.txt)
# ============================================================================
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
JOB_SCRIPT="$SCRIPT_DIR/qsub_subject.sh"
LOG_DIR="/export03/data/enning/micapet/logs"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <participant1> [participant2] ..."
    echo "  e.g. $0 PX003 PX126 PX200"
    exit 1
fi

mkdir -p "$LOG_DIR"

echo "Submitting $# participant(s)..."
echo ""

for PARTICIPANT in "$@"; do
    JOB_ID=$(qsub \
        -v PARTICIPANT="$PARTICIPANT" \
        -N "micapet_${PARTICIPANT}" \
        -o "$LOG_DIR/micapet_${PARTICIPANT}.log" \
        -j oe \
        "$JOB_SCRIPT")
    echo "  Submitted $PARTICIPANT -> Job $JOB_ID"
done

echo ""
echo "All jobs submitted. Monitor with:"
echo "  qstat -u \$USER"
echo "  tail -f $LOG_DIR/micapet_<PARTICIPANT>.log"

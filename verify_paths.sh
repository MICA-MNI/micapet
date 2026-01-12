#!/bin/bash
# Script to verify all required paths exist on the server
# Run this on login.bic.mni.mcgill.ca

echo "======================================================"
echo "Verifying MICAPET Pipeline Paths"
echo "======================================================"
echo ""

# Paths to check
BIDS_DIR="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG"
FASTSURFER_IMG="/host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif"
HIPPUNFOLD_IMG="/host/verges/tank/data/jack/hippunfold_v1.4.1.sif"
FS_LICENSE="/host/verges/tank/data/jack/license.txt"
HIPP_CACHE="/host/verges/tank/data/jack/hippunfold_tmp"

# Also check for the example subject
EXAMPLE_SUBJECT_PATH="/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_MICs_FDG/derivatives/MICA-PET_v.alpha.0.3/sub-PX003/ses-01"

all_exist=true

echo "1. Checking BIDS Directory..."
if [ -d "$BIDS_DIR" ]; then
    echo "   ✓ FOUND: $BIDS_DIR"
    # List some contents to verify
    echo "   Contents preview:"
    ls -lh "$BIDS_DIR" | head -5
else
    echo "   ✗ NOT FOUND: $BIDS_DIR"
    all_exist=false
fi
echo ""

echo "2. Checking FastSurfer Singularity Image..."
if [ -f "$FASTSURFER_IMG" ]; then
    echo "   ✓ FOUND: $FASTSURFER_IMG"
    ls -lh "$FASTSURFER_IMG"
else
    echo "   ✗ NOT FOUND: $FASTSURFER_IMG"
    echo "   Searching for fastsurfer images in /host/verges/tank/data/jack/..."
    find /host/verges/tank/data/jack/ -name "*fastsurfer*.sif" 2>/dev/null || echo "   No fastsurfer images found"
    all_exist=false
fi
echo ""

echo "3. Checking HippUnfold Singularity Image..."
if [ -f "$HIPPUNFOLD_IMG" ]; then
    echo "   ✓ FOUND: $HIPPUNFOLD_IMG"
    ls -lh "$HIPPUNFOLD_IMG"
else
    echo "   ✗ NOT FOUND: $HIPPUNFOLD_IMG"
    echo "   Searching for hippunfold images in /host/verges/tank/data/jack/..."
    find /host/verges/tank/data/jack/ -name "*hippunfold*.sif" 2>/dev/null || echo "   No hippunfold images found"
    all_exist=false
fi
echo ""

echo "4. Checking FreeSurfer License..."
if [ -f "$FS_LICENSE" ]; then
    echo "   ✓ FOUND: $FS_LICENSE"
    ls -lh "$FS_LICENSE"
else
    echo "   ✗ NOT FOUND: $FS_LICENSE"
    echo "   Searching for license files in /host/verges/tank/data/jack/..."
    find /host/verges/tank/data/jack/ -name "license.txt" 2>/dev/null || echo "   No license.txt found"
    all_exist=false
fi
echo ""

echo "5. Checking HippUnfold Cache Directory..."
if [ -d "$HIPP_CACHE" ]; then
    echo "   ✓ FOUND: $HIPP_CACHE"
    ls -lh "$HIPP_CACHE" | head -5
else
    echo "   ✗ NOT FOUND: $HIPP_CACHE"
    echo "   This directory may be created automatically on first run."
    # Don't set all_exist to false for cache dir as it can be created
fi
echo ""

echo "6. Checking Example Subject (PX003)..."
if [ -d "$EXAMPLE_SUBJECT_PATH" ]; then
    echo "   ✓ FOUND: $EXAMPLE_SUBJECT_PATH"
else
    echo "   ✗ NOT FOUND: $EXAMPLE_SUBJECT_PATH"
    echo "   Checking if subject exists in rawdata..."
    RAW_SUBJECT="$BIDS_DIR/rawdata/sub-PX003/ses-01"
    if [ -d "$RAW_SUBJECT" ]; then
        echo "   ✓ Found in rawdata: $RAW_SUBJECT"
        echo "   Listing contents:"
        find "$RAW_SUBJECT" -type f | head -10
    else
        echo "   ✗ Not found in rawdata either"
        echo "   Searching for PX003..."
        find "$BIDS_DIR" -name "*PX003*" -type d 2>/dev/null | head -5
    fi
fi
echo ""

echo "======================================================"
if [ "$all_exist" = true ]; then
    echo "✓ All critical paths verified!"
    echo "You can proceed with running the pipeline."
else
    echo "✗ Some paths are missing!"
    echo "Please update test_pipeline.sh with the correct paths."
fi
echo "======================================================"

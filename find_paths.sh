#!/bin/bash
# Script to FIND the correct paths on the server
# Run this on login.bic.mni.mcgill.ca

echo "======================================================"
echo "Searching for MICAPET Pipeline Files"
echo "======================================================"
echo ""

echo "Searching for BIDS directories containing 'FDG' or 'MICA-PET'..."
find /host -type d -name "*BIDS*" -o -name "*FDG*" -o -name "*MICA*" 2>/dev/null | grep -i pet | head -20
echo ""

echo "Searching for FastSurfer .sif files..."
find /host -type f -name "*fastsurfer*.sif" 2>/dev/null | head -10
echo ""

echo "Searching for HippUnfold .sif files..."
find /host -type f -name "*hippunfold*.sif" 2>/dev/null | head -10
echo ""

echo "Searching for FreeSurfer license files..."
find /host -type f -name "license.txt" 2>/dev/null | head -10
echo ""

echo "Searching for subject PX003..."
find /host -type d -name "*PX003*" 2>/dev/null | head -10
echo ""

echo "======================================================"
echo "Alternative: Check Jack's common directories"
echo "======================================================"
echo "Checking /host/fladgate/..."
ls -la /host/fladgate/ 2>/dev/null || echo "Cannot access /host/fladgate/"
echo ""
echo "Checking /host/verges/..."
ls -la /host/verges/ 2>/dev/null || echo "Cannot access /host/verges/"
echo ""

echo "Checking if /data_ exists..."
ls -la /data_ 2>/dev/null || echo "Cannot access /data_"
echo ""

echo "======================================================"
echo "Please paste this output back so I can update the paths!"
echo "======================================================"

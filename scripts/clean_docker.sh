#!/bin/bash
set -e

# ============================================================================
# Docker Cleanup Script
# ============================================================================
# Frees up space on the Docker partition (/export01) by removing unused data.

echo "====================================================================="
echo "DISK USAGE BEFORE CLEANING (/export01)"
echo "====================================================================="
df -h /export01 || echo "Could not run df on /export01"

echo ""
echo "====================================================================="
echo "1. Pruning Docker Builder Cache (Usually the largest consumer)..."
echo "====================================================================="
# Removes build cache from previous builds
docker builder prune --all --force

echo ""
echo "====================================================================="
echo "2. Pruning Stopped Containers..."
echo "====================================================================="
# Removes containers that are not running
docker container prune --force

echo ""
echo "====================================================================="
echo "3. Pruning Dangling Images..."
echo "====================================================================="
# Removes images that are not tagged (often intermediate build layers)
docker image prune --force

echo ""
echo "====================================================================="
echo "DISK USAGE AFTER CLEANING"
echo "====================================================================="
df -h /export01 || echo "Could not run df on /export01"

echo ""
echo "Done. Try running the build script again."

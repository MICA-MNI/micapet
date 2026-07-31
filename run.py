#!/usr/bin/env python3
"""
MICA-PET Pipeline - Snakebids BIDS App

This script provides the command-line interface for running the MICA-PET
neuroimaging pipeline using the Snakebids framework.

Usage:
    ./run.py <bids_dir> <output_dir> participant [options]
    ./run.py --help

Example:
    ./run.py /path/to/bids /path/to/output participant \
        --fastsurfer-img /path/to/fastsurfer.sif \
        --hippunfold-img /path/to/hippunfold.sif \
        --fs-license /path/to/license.txt
"""
from pathlib import Path
from snakebids import bidsapp, plugins
import warnings
import os
import sys
scripts_dir = os.path.dirname(os.path.abspath(__file__))
functions_dir = os.path.abspath(os.path.join(scripts_dir,"functions"))
if functions_dir not in sys.path:
    sys.path.insert(0, functions_dir)

from functions import utils

warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")

def main():
    """Main entry point for the MICA-PET pipeline."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()

    # Create the snakebids app with the SnakemakeBidsApp plugin
    app = bidsapp.app(
        [
            plugins.SnakemakeBidsApp(script_dir),
        ]
    )
    
    # Run the app
    app.run()


if __name__ == "__main__":
    main()

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
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["PYTHONWARNINGS"] = "ignore::FutureWarning:google.api_core"  # Suppress specific FutureWarnings from google.api_core

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

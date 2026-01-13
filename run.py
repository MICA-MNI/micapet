#!/usr/bin/env python3
from snakebids.app import SnakeBidsApp
from pathlib import Path

def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    app = SnakeBidsApp(
        snakemake_dir=script_dir / "workflow",
        configfile_path=script_dir / "config" / "snakebids.yml",
    )
    app.run_snakemake()

if __name__ == "__main__":
    main()

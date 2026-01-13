#!/usr/bin/env python3
from snakebids.app import SnakeBidsApp

def main():
    app = SnakeBidsApp(
        snakemake_dir="workflow",
        configfile_path="config/snakebids.yml",
    )
    app.run_snakemake()

if __name__ == "__main__":
    main()

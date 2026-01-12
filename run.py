#!/usr/bin/env python3
import os
from snakebids.app import SnakeBidsApp

def main():
    app = SnakeBidsApp(
        "micapet",
        script_dir=os.path.dirname(os.path.abspath(__file__)),
        configfile_path="config/snakebids.yml",
        snakefile_path="workflow/Snakefile",
    )
    app.run()

if __name__ == "__main__":
    main()

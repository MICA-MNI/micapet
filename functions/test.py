#!/usr/bin/env python
# coding: utf-8

import os

script_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.dirname(script_dir)

print(script_dir)
print(f'{repo_dir}/surfaces/fsLR-')


# import fsqc

# fsqc.run_fsqc(subjects_dir='/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS/derivatives/fastsurfer',        
#               output_dir='/host/fladgate/local_raid/jack/FDG/MICA-PET/qc',
#               subjects=['sub-PXtt169_ses-01'],
#               screenshots=True,
#               surfaces=True,
#               fastsurfer=True
#               )

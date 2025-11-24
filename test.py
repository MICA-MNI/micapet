#!/usr/bin/env python
# coding: utf-8

# Import the report_creator module
import fsqc

fsqc.run_fsqc(subjects_dir='/host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS/derivatives/fastsurfer',        
              output_dir='/host/fladgate/local_raid/jack/FDG/MICA-PET/qc',
              subjects=['sub-PXtt169_ses-01'],
              screenshots=True,
              surfaces=True,
              fastsurfer=True
              )

# !/bin/bash

docker build -t micalab/micapet:v.alpha.0.1 .

docker run -it --privileged --user $(id -u):$(id -g)  --security-opt seccomp=unconfined --security-opt apparmor=unconfined --env HOME=/tmp  --env SINGULARITY_TMPDIR=/tmp --env SINGULARITY_CACHEDIR=/tmp -v /host:/host   -v /home:/home   -v /data/mica1/01_programs/fastsurfer:/data/mica1/01_programs/fastsurfer -v /data:/data micalab/micapet:v.alpha.0.1 -sub PX2002001     -ses pre     -bids /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_20251111TLE_TZ_test  -fastsurfer_img /data/mica1/01_programs/fastsurfer/fastsurfer-cpu-v2.4.2.sif     -fs_license /data/mica1/01_programs/freesurfer-7.4.1/license.txt     -hippunfold_img /data/mica1/01_programs/singularity/hippunfold_v1.4.1.sif -psf 4.5
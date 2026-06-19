#!/bin/sh
# Docker build container

MICAPET_version=$1 #v.alpha.0.3

cd /host/fladgate/local_raid/jack/FDG/MICA-PET/scripts

docker image prune

export DOCKER_BUILDKIT=1
export DOCKER_CONTENT_TRUST=0
export SINGULARITY_TMPDIR=/export02/data/jack/tmp
export SINGULARITY_CACHEDIR=/export02/data/jack/tmp

# export SINGULARITY_TMPDIR=/host/verges/tank/data/jack/tmpdir
# export SINGULARITY_CACHEDIR=/host/verges/tank/data/jack/tmpdir

docker build -t micalab/micapet:${MICAPET_version} .

singularity build micapet_${MICAPET_version}.sif docker-daemon://micalab/micapet:${MICAPET_version}
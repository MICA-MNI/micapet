# !/bin/bash
echo "root:x:0:0:root:/root:/bin/bash" > passwd.fake
echo "user:x:$(id -u):$(id -g):User,,,:/tmp:/bin/bash" >> passwd.fake
echo "root:x:0:" > group.fake
echo "user:x:$(id -g):" >> group.fake
# --- Fastest + most stable way to run Singularity inside Docker ---
GROUP_ARGS=""
for gid in $(id -G); do
    GROUP_ARGS="$GROUP_ARGS --group-add $gid"
done

docker run -it --privileged \
    --user "$(id -u):$(id -g)" \
    $GROUP_ARGS \
    --security-opt seccomp=unconfined \
    --security-opt apparmor=unconfined \
    --env HOME=/tmp \
    --env APPTAINER_TMPDIR=/tmp \
    --env APPTAINER_CACHEDIR=/tmp \
    --env APPTAINER_NO_MOUNT_HOME=1 \
    --env APPTAINER_NO_MOUNT_TMP=1 \
    -v /host:/host \
    -v "$(pwd)/passwd.fake":/etc/passwd:ro \
    -v "$(pwd)/group.fake":/etc/group:ro \
    micalab/micapet:v.alpha.0.2 \
        -sub PX2002001 \
        -ses pre \
        -bids /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_20251111TLE_TZ_test/ \
        -fastsurfer_img /host/verges/tank/data/jack/fastsurfer-cpu-v2.4.2.sif \
        -fs_license /host/verges/tank/data/jack/license.txt \
        -hippunfold_img /host/verges/tank/data/jack/hippunfold_v1.4.1.sif \
        -psf 4.5 -force


    # --memory=16g --memory-swap=16g \
    # -v /home:/home \
    # -v /data:/data \
    # -v /data/mica1/01_programs/fastsurfer:/data/mica1/01_programs/fastsurfer \


# # Generate local user files for Singularity mapping
# # This fixes the "unknown userid" error by providing a passwd file that includes the current user
# echo "root:x:0:0:root:/root:/bin/bash" > passwd.fake
# echo "user:x:$(id -u):$(id -g):User,,,:/tmp:/bin/bash" >> passwd.fake
# echo "root:x:0:" > group.fake
# echo "user:x:$(id -g):" >> group.fake

# # Prepare group arguments to pass all user groups to Docker
# # This ensures access to files permitted via secondary groups
# GROUP_ARGS=""
# for gid in $(id -G); do
#     GROUP_ARGS="$GROUP_ARGS --group-add $gid"
# done

# docker run -it --privileged \
#     --user "$(id -u):$(id -g)" \
#     $GROUP_ARGS \
#     --security-opt seccomp=unconfined \
#     --security-opt apparmor=unconfined \
#     --memory=16g --memory-swap=16g \
#     --env HOME=/tmp \
#     --env SINGULARITY_TMPDIR=/tmp \
#     --env SINGULARITY_CACHEDIR=/tmp \
#     -v /host:/host \
#     -v /home:/home \
#     -v /data/mica1/01_programs/fastsurfer:/data/mica1/01_programs/fastsurfer \
#     -v /data:/data \
#     -v "$(pwd)/passwd.fake":/etc/passwd:ro \
#     -v "$(pwd)/group.fake":/etc/group:ro \
#     micalab/micapet:v.alpha.0.1 \
#     -sub PX001 \
#     -ses 01 \
#     -bids /host/fladgate/local_raid/jack/FDG/MICA-PET/BIDS_PET_test \
#     -fastsurfer_img /data/mica1/01_programs/fastsurfer/fastsurfer-cpu-v2.4.2.sif \
#     -fs_license /data/mica1/01_programs/freesurfer-7.4.1/license.txt \
#     -hippunfold_img /data/mica1/01_programs/singularity/hippunfold_v1.4.1.sif \
#     -psf 4.5 -force

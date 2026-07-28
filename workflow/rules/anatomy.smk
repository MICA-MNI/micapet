# Anatomy processing rules: FastSurfer, HippUnfold, Cortical Surface mappings

from functions.MICA_PET import fastsurfer, hippunfold, cortical_surface
import sys
import os

if not config.get("existing_freesurfer_dir", ""): 
    rule fastsurfer:
        input:
            t1 = inputs['T1w'].path
        output:
            pial_lh = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "lh.pial"),
            pial_rh = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "rh.pial"),
            white_lh = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "lh.white"),
            white_rh = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "rh.white"),
            sphere_lh = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "lh.sphere.reg"),
            sphere_rh = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "rh.sphere.reg"),
            norm = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "norm.mgz"),
            talairach = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "transforms", "talairach.lta"),
            brainmask = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "brainmask.mgz"),
            aparc_aseg = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "aparc+aseg.mgz"),
        params:
            bids_dir = config["bids_dir"],
            fs_license = config.get("fs_license"),
            img = config.get("fastsurfer_img"),
            # FastSurfer uses -subj_dir to specify where to write outputs
            subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
            # Required tmpdir argument
            tmpdir = "/tmp",
            log_dir = os.path.join(root, "logs", "fastsurfer"),
            force = config.get("force", False),
        log:
            os.path.join(root, "logs", "fastsurfer", "sub-{subject}_ses-{session}.log")
        threads: config.get("threads", 8)
        run:
            # Create log directory if it doesn't exist
            os.makedirs(os.path.dirname(log[0]), exist_ok=True)
            with open(log[0], "w") as f:
                sys.stdout = f
                sys.stderr = f
                fastsurfer(
                    subject=wildcards.subject,
                    session=wildcards.session,
                    bids_dir=params.bids_dir,
                    subj_dir=params.subj_dir,
                    fastsurfer_img=params.img,
                    fs_license=params.fs_license,
                    threads=threads,
                    tmpdir=params.tmpdir,
                    force=params.force
                )

if not config.get("skip_hippunfold", False) and not config.get("existing_hippunfold_dir", ""): #runs hippunfold if flag not set and existing dir not specified, skip hippunfold if flag set or if existing dir specified
    rule hippunfold:
        input:
            t1 = inputs['T1w'].path
        output:
            hipp_lh = os.path.join(root, HIPPUNFOLD_DIR_NAME, "hippunfold", "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_space-T1w_den-2mm_label-hipp_midthickness.surf.gii"),
            hipp_rh = os.path.join(root, HIPPUNFOLD_DIR_NAME, "hippunfold", "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_space-T1w_den-2mm_label-hipp_midthickness.surf.gii"),
        params:
            bids_dir = config["bids_dir"],
            img = config.get("hippunfold_img"),
            # hippunfold.py uses -hippunfold_dir NOT -output_dir
            hippunfold_dir = os.path.join(root, HIPPUNFOLD_DIR_NAME),
            cachedir_arg = lambda wildcards: f"-cachedir {config['hippunfold_cache_dir']}" if config.get("hippunfold_cache_dir") else "",
            log_dir = os.path.join(root, "logs", "hippunfold"),
            tmpdir = "/tmp",
            force = config.get("force", False),
        log:
            os.path.join(root, "logs", "hippunfold", "sub-{subject}_ses-{session}.log")
        threads: config.get("threads", 8)
        run:
            # Create log directory if it doesn't exist
            os.makedirs(os.path.dirname(log[0]), exist_ok=True)
            with open(log[0], "w") as f:
                sys.stdout = f
                sys.stderr = f
                hippunfold(
                    subject=wildcards.subject,
                    session=wildcards.session,
                    bids_dir=params.bids_dir,
                    hippunfold_img=params.img,
                    hippunfold_dir=params.hippunfold_dir,
                    tmpdir=params.tmpdir,
                    cachedir=params.cachedir_arg,
                    threads=threads,
                    force=params.force
                )

def get_cortical_surface_inputs(wildcards):
    """Get cortical surface inputs - mark as ancient if using existing outputs."""
    base_paths = {
        "pial_lh": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "lh.pial"),
        "pial_rh": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "rh.pial"),
        "white_lh": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "lh.white"),
        "white_rh": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "rh.white"),
        "sphere_lh": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "lh.sphere.reg"),
        "sphere_rh": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "rh.sphere.reg"),
        "norm": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "norm.mgz"),
        "talairach": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "transforms", "talairach.lta"),
        "brainmask": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "brainmask.mgz"),
        "aparc_aseg": os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "aparc+aseg.mgz"),
    }
    
    # # If using existing FreeSurfer dir, mark files as ancient (don't trigger fastsurfer rule)
    if config.get("existing_freesurfer_dir", ""):
        return {k: ancient(v) for k, v in base_paths.items()}
    return base_paths

rule cortical_surface:
    input:
        unpack(get_cortical_surface_inputs)
    output:
        # Expected outputs from cortical_surface
        fsLR_32k_L = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_space-T1wFS_surf-fsLR-32k_label-midthickness.surf.gii"),
        fsLR_32k_R = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_space-T1wFS_surf-fsLR-32k_label-midthickness.surf.gii"),
        # fsnative
        fsnative_L = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-fsnative_label-midthickness.surf.gii"),
        fsnative_R = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-fsnative_label-midthickness.surf.gii"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "cortical_surface"),
        fs_license = config.get("fs_license"),
    log:
        os.path.join(root, "logs", "cortical_surface", "sub-{subject}_ses-{session}.log")
    run:
        # Create log directory if it doesn't exist
        os.makedirs(os.path.dirname(log[0]), exist_ok=True)
        with open(log[0], "w") as f:
            sys.stdout = f
            sys.stderr = f
            cortical_surface(
                subject=wildcards.subject,
                session=wildcards.session,
                bids_dir=params.bids_dir,
                subj_dir=params.subj_dir
            )
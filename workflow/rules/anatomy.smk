# Anatomy processing rules: FastSurfer, HippUnfold, Cortical Surface mappings

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
    log:
        os.path.join(root, "logs", "fastsurfer", "sub-{subject}_ses-{session}.log")
    threads: config.get("threads", 8)
    shell:
        """
        mkdir -p {params.log_dir}
        python -u {workflow.basedir}/../functions/fastsurfer.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -threads {threads} \
            -fastsurfer_img {params.img} \
            -subj_dir {params.subj_dir} \
            -tmpdir {params.tmpdir} \
            -fs_license {params.fs_license} \
            -force \
            > {log} 2>&1
        """

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
        log:
            os.path.join(root, "logs", "hippunfold", "sub-{subject}_ses-{session}.log")
        threads: config.get("threads", 8)
        shell:
            """
            mkdir -p {params.log_dir}
            python -u {workflow.basedir}/../functions/hippunfold.py \
                -sub {wildcards.subject} \
                -ses {wildcards.session} \
                -bids {params.bids_dir} \
                -hippunfold_img {params.img} \
                -hippunfold_dir {params.hippunfold_dir} \
                -threads {threads} \
                {params.cachedir_arg} \
                > {log} 2>&1
            """

def get_cortical_surface_inputs(wildcards):
    """Get cortical surface inputs - mark as ancient if using existing outputs."""
    base_paths = {
        "pial_lh": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "surf", "lh.pial"),
        "white_lh": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "surf", "lh.white"),
        "sphere_lh": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "surf", "lh.sphere.reg"),
        "pial_rh": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "surf", "rh.pial"),
        "white_rh": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "surf", "rh.white"),
        "sphere_rh": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "surf", "rh.sphere.reg"),
    }
    
    # # If using existing FreeSurfer dir, mark files as ancient (don't trigger fastsurfer rule)
    # if config.get("existing_freesurfer_dir", ""):
    #     return {k: ancient(v) for k, v in base_paths.items()}
    return base_paths

rule cortical_surface:
    input:
        # unpack(get_cortical_surface_inputs)
        rules.fastsurfer.output.pial_lh,
        rules.fastsurfer.output.white_lh,
        rules.fastsurfer.output.sphere_lh,
        rules.fastsurfer.output.pial_rh,
        rules.fastsurfer.output.white_rh,
        rules.fastsurfer.output.sphere_rh,
    output:
        # Expected outputs from cortical_surface.py
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
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/opt/freesurfer-7.4.1
        export FS_LICENSE={params.fs_license}
        source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
        mkdir -p {params.log_dir}
        echo "=== Starting cortical_surface.py at $(date) ===" > {log} 2>&1
        echo "FS_LICENSE=$FS_LICENSE" >> {log} 2>&1
        python -u {workflow.basedir}/../functions/cortical_surface.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            >> {log} 2>&1
        """

def get_gtm_seg_inputs(wildcards):
    """Get GTM seg inputs - mark as ancient if using existing outputs."""
    base_paths = {
        "norm": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "norm.mgz"),
        "talairach": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "transforms", "talairach.lta"),
        "brainmask": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "brainmask.mgz"),
    }
    # if config.get("existing_freesurfer_dir", ""):
    #     return {k: ancient(v) for k, v in base_paths.items()}
    return base_paths

rule gtm_seg:
    input:
        # unpack(get_gtm_seg_inputs)
        rules.fastsurfer.output.norm,
        rules.fastsurfer.output.talairach,
        rules.fastsurfer.output.brainmask,
    output:
        # gtmseg = protected(os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "gtmseg.mgz")),
        gtmseg_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "anat", "sub-{subject}_ses-{session}_space-T1wFS_desc-gtmseg.nii.gz"),
        gtmseg_nativepro = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "anat", "sub-{subject}_ses-{session}_space-T1wNativepro_desc-gtmseg.nii.gz"),
        # protected(os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "apas+head.mgz")),
    params:
        bids_dir = config["bids_dir"],
        # gtm_seg.py uses -subj_dir
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        log_dir = os.path.join(root, "logs", "gtm_seg"),
        fs_license = config.get("fs_license"),
    log:
        os.path.join(root, "logs", "gtm_seg", "sub-{subject}_ses-{session}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/opt/freesurfer-7.4.1
        export FS_LICENSE={params.fs_license}
        source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
        mkdir -p {params.log_dir}
        echo "=== Starting gtm_seg.py at $(date) ===" > {log} 2>&1
        python -u {workflow.basedir}/../functions/gtm_seg.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            >> {log} 2>&1
        """

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
        python {workflow.basedir}/../functions/fastsurfer.py \
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
        python {workflow.basedir}/../functions/hippunfold.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -hippunfold_img {params.img} \
            -hippunfold_dir {params.hippunfold_dir} \
            -threads {threads} \
            {params.cachedir_arg} \
            -force \
            > {log} 2>&1
        """

rule cortical_surface:
    input:
        pial_lh = rules.fastsurfer.output.pial_lh,
        white_lh = rules.fastsurfer.output.white_lh,
        sphere_lh = rules.fastsurfer.output.sphere_lh,
        pial_rh = rules.fastsurfer.output.pial_rh,
        white_rh = rules.fastsurfer.output.white_rh,
        sphere_rh = rules.fastsurfer.output.sphere_rh,
    output:
        # Expected outputs from cortical_surface.py
        fsLR_32k_L = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_space-T1w_surf-fsLR-32k_label-midthickness.surf.gii"),
        fsLR_32k_R = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_space-T1w_surf-fsLR-32k_label-midthickness.surf.gii"),
        # fsnative
        fsnative_L = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-fsnative_label-midthickness.surf.gii"),
        fsnative_R = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-fsnative_label-midthickness.surf.gii"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "cortical_surface"),
    log:
        os.path.join(root, "logs", "cortical_surface", "sub-{subject}_ses-{session}.log")
    shell:
        """
        export FREESURFER_HOME=/opt/freesurfer-7.4.1
        source $FREESURFER_HOME/SetUpFreeSurfer.sh
        mkdir -p {params.log_dir}
        python {workflow.basedir}/../functions/cortical_surface.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            > {log} 2>&1
        """

rule gtm_seg:
    input:
        norm = rules.fastsurfer.output.norm,
        talairach = rules.fastsurfer.output.talairach,
        brainmask = rules.fastsurfer.output.brainmask,
    output:
        gtmseg = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "gtmseg.mgz"),
    params:
        bids_dir = config["bids_dir"],
        # gtm_seg.py uses -subj_dir
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        seg_type = "fastsurfer",
        log_dir = os.path.join(root, "logs", "gtm_seg"),
    log:
        os.path.join(root, "logs", "gtm_seg", "sub-{subject}_ses-{session}.log")
    shell:
        """
        export FREESURFER_HOME=/opt/freesurfer-7.4.1
        source $FREESURFER_HOME/SetUpFreeSurfer.sh
        mkdir -p {params.log_dir}
        python {workflow.basedir}/../functions/gtm_seg.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -seg_type {params.seg_type} \
            -force \
            > {log} 2>&1
        """

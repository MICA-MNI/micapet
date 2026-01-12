# Anatomy processing rules: FastSurfer, HippUnfold, Cortical Surface mappings

rule fastsurfer:
    input:
        t1 = inputs.T1w.path
    output:
        pial_lh = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/surf/lh.pial",
        pial_rh = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/surf/rh.pial",
        white_lh = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/surf/lh.white",
        white_rh = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/surf/rh.white",
        sphere_lh = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/surf/lh.sphere.reg",
        sphere_rh = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/surf/rh.sphere.reg",
        norm = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/mri/norm.mgz",
        talairach = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/mri/transforms/talairach.lta",
        brainmask = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/mri/brainmask.mgz",
        aparc_aseg = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/mri/aparc+aseg.mgz",
    params:
        bids_dir = config["bids_dir"],
        fs_license = config.get("fs_license"),
        img = config.get("fastsurfer_img"),
        threads = config.get("threads", 8),
        tmpdir = directory(f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/tmp")
    log:
        "logs/fastsurfer/sub-{subject}_ses-{session}.log"
    threads: 8
    shell:
        """
        python functions/fastsurfer.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -threads {threads} \
            -fastsurfer_img {params.img} \
            -tmpdir {params.tmpdir} \
            -fs_license {params.fs_license} \
            > {log} 2>&1
        """

rule hippunfold:
    input:
        t1 = inputs.T1w.path
    output:
        hipp_lh = f"derivatives/{HIPPUNFOLD_DIR_NAME}/hippunfold/sub-{{subject}}/ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-L_space-T1w_den-2mm_label-hipp_midthickness.surf.gii",
        hipp_rh = f"derivatives/{HIPPUNFOLD_DIR_NAME}/hippunfold/sub-{{subject}}/ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-R_space-T1w_den-2mm_label-hipp_midthickness.surf.gii"
    params:
        bids_dir = config["bids_dir"],
        img = config.get("hippunfold_img"),
        cachedir_arg = f"-cachedir {config['hippunfold_cache_dir']}" if config.get("hippunfold_cache_dir") else "",
        tmpdir = directory(f"derivatives/{HIPPUNFOLD_DIR_NAME}/tmp/sub-{{subject}}_ses-{{session}}")
    log:
        "logs/hippunfold/sub-{subject}_ses-{session}.log"
    threads: 8
    shell:
        """
        python functions/hippunfold.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -hippunfold_img {params.img} \
            -tmpdir {params.tmpdir} \
            {params.cachedir_arg} \
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
        # Expected outputs from cortical_surface.py (based on list_of_tests.txt and script logic)
        # Note: script seems to use 'fsLR-{res}' where res is hardcoded/defaulted
        # It seems it outputs both fsLR-32k and possibly fsLR-164k/5k?
        # Checked cortical_surface.py: it loops through resolutions ['32k','164k']
        fsLR_32k_L = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-L_space-T1w_surf-fsLR-32k_label-midthickness.surf.gii",
        fsLR_32k_R = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-R_space-T1w_surf-fsLR-32k_label-midthickness.surf.gii",
        # fsnative
        fsnative_L = f"derivatives/fastsurfer/sub-{{subject}}_ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-L_surf-fsnative_label-midthickness.surf.gii",
        fsnative_R = f"derivatives/fastsurfer/sub-{{subject}}_ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-R_surf-fsnative_label-midthickness.surf.gii"
    params:
        bids_dir = config["bids_dir"],
        subj_dir = f"derivatives/{FASTSURFER_DIR_NAME}"
    log:
        "logs/cortical_surface/sub-{subject}_ses-{session}.log"
    shell:
        """
        python functions/cortical_surface.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            > {log} 2>&1
        """

rule gtm_seg:
    input:
        norm = rules.fastsurfer.output.norm,
        talairach = rules.fastsurfer.output.talairach,
        brainmask = rules.fastsurfer.output.brainmask,
        # Requires $FREESURFER_HOME/average/RB_all_2016-05-10.vc700.gca (usually assumed present in environment/container)
    output:
        gtmseg = f"derivatives/{FASTSURFER_DIR_NAME}/sub-{{subject}}_ses-{{session}}/mri/gtmseg.mgz"
    params:
        bids_dir = config["bids_dir"],
        subj_dir = f"derivatives/{FASTSURFER_DIR_NAME}",
        seg_type = "fastsurfer"
    log:
        "logs/gtm_seg/sub-{subject}_ses-{session}.log"
    shell:
        """
        python functions/gtm_seg.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -seg_type {params.seg_type} \
            > {log} 2>&1
        """

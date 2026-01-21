# PET processing rules: Linear Coreg, PVC, SUVR, Project PET, Subcortical Map

# Helper to get reference region from config
def get_ref_region():
    return config.get("ref_region", "pons")

rule linear_coreg:
    input:
        pet = inputs['pet'].path,
        t1 = inputs['T1w'].path,
        # Ensure fastsurfer completed
        fs_check = rules.fastsurfer.output.norm,
    output:
        # Reg lta files - Note: Python outputs to /xfm/ subdirectory with _from-pet_to-{space}_xfm.reg.lta naming
        reg_lta_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", "sub-{subject}_ses-{session}_from-pet_to-T1wFS_xfm.reg.lta"),
        reg_lta_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", "sub-{subject}_ses-{session}_from-pet_to-T1wNative_xfm.reg.lta"),
        # Coregistered PET
        pet_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-none_ref-none_trc-FDG_pet.nii.gz"),
        pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNative_pvc-none_ref-none_trc-FDG_pet.nii.gz"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "linear_coreg"),
        fs_license = config.get("fs_license"),
    log:
        os.path.join(root, "logs", "linear_coreg", "sub-{subject}_ses-{session}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/opt/freesurfer-7.4.1
        export FS_LICENSE={params.fs_license}
        source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
        mkdir -p {params.log_dir}
        echo "=== Starting linear_coreg.py at $(date) ===" > {log} 2>&1
        echo "FREESURFER_HOME=$FREESURFER_HOME" >> {log} 2>&1
        echo "FS_LICENSE=$FS_LICENSE" >> {log} 2>&1
        echo "SUBJECTS_DIR=${{SUBJECTS_DIR:-not_set}}" >> {log} 2>&1
        which mri_coreg >> {log} 2>&1 || echo "mri_coreg not found in PATH" >> {log} 2>&1
        echo "Running python script..." >> {log} 2>&1
        python {workflow.basedir}/../functions/linear_coreg.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            -pet {input.pet} \
            -mri {input.t1} \
            >> {log} 2>&1
        """

rule pvc:
    input:
        pet_fs = rules.linear_coreg.output.pet_fs,
        pet_raw = inputs['pet'].path,
        lta = rules.linear_coreg.output.reg_lta_fs,
        gtmseg = rules.gtm_seg.output.gtmseg,
    output:
        pvc_pet_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-rbv_ref-none_trc-FDG_pet.nii.gz"),
        pvc_pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNative_pvc-rbv_ref-none_trc-FDG_pet.nii.gz"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        psf = config.get("psf", 4.5),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "pvc"),
        fs_license = config.get("fs_license"),
    log:
        os.path.join(root, "logs", "pvc", "sub-{subject}_ses-{session}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/opt/freesurfer-7.4.1
        export FS_LICENSE={params.fs_license}
        source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
        mkdir -p {params.log_dir}
        echo "=== Starting pvc.py at $(date) ===" > {log} 2>&1
        python {workflow.basedir}/../functions/pvc.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            -psf {params.psf} \
            -force \
            >> {log} 2>&1
        """

rule suvr:
    input:
        pvc_pet_fs = rules.pvc.output.pvc_pet_fs,
        pvc_pet_native = rules.pvc.output.pvc_pet_native,
        gtmseg_fs_suvr = rules.gtm_seg.output.gtmseg_fs,
        gtmseg_native_suvr = rules.gtm_seg.output.gtmseg_native,
    output:
        suvr_pet_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-rbv_ref-" + get_ref_region() + "_trc-FDG_pet.nii.gz"),
        suvr_pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNative_pvc-rbv_ref-" + get_ref_region() + "_trc-FDG_pet.nii.gz"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        ref_region = get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "suvr"),
        fs_license = config.get("fs_license"),
    log:
        os.path.join(root, "logs", "suvr", "sub-{subject}_ses-{session}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/opt/freesurfer-7.4.1
        export FS_LICENSE={params.fs_license}
        source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
        mkdir -p {params.log_dir}
        mkdir -p {params.output_dir}/sub-{wildcards.subject}/ses-{wildcards.session}/anat
        echo "=== Starting suvr.py at $(date) ===" > {log} 2>&1
        python {workflow.basedir}/../functions/suvr.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            -ref_region {params.ref_region} \
            >> {log} 2>&1
        """

rule project_pet_data:
    input:
        suvr_pet_fs = rules.suvr.output.suvr_pet_fs,
        surf_L = rules.cortical_surface.output.fsnative_L,
        surf_R = rules.cortical_surface.output.fsnative_R,
        hipp_L = rules.hippunfold.output.hipp_lh,
        hipp_R = rules.hippunfold.output.hipp_rh,
    output:
        # Cortical projection
        func_L = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-rbv_ref-" + get_ref_region() + "_smooth-10mm_trc-FDG_pet.func.gii"),
        func_R = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-rbv_ref-" + get_ref_region() + "_smooth-10mm_trc-FDG_pet.func.gii"),
        # Hippocampal projection
        hipp_func_L = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-rbv_ref-" + get_ref_region() + "_trc-FDG_pet.func.gii"),
        hipp_func_R = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-rbv_ref-" + get_ref_region() + "_trc-FDG_pet.func.gii"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        hippunfold_dir = os.path.join(root, HIPPUNFOLD_DIR_NAME),
        ref_region = get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "project_pet_data"),
        fs_license = config.get("fs_license"),
    log:
        os.path.join(root, "logs", "project_pet_data", "sub-{subject}_ses-{session}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/opt/freesurfer-7.4.1
        export FS_LICENSE={params.fs_license}
        source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
        mkdir -p {params.log_dir}
        echo "=== Starting project_pet_data.py at $(date) ===" > {log} 2>&1
        python {workflow.basedir}/../functions/project_pet_data.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -hippunfold_dir {params.hippunfold_dir} \
            -output_dir {params.output_dir} \
            -ref_region {params.ref_region} \
            -pvc \
            -cortical \
            -hippocampal \
            >> {log} 2>&1
        """

rule subcortical_map:
    input:
        suvr_pet_fs = rules.suvr.output.suvr_pet_fs,
        aparc_aseg = rules.fastsurfer.output.aparc_aseg,
    output:
        csv = os.path.join(root, "qc", "sub-{subject}", "ses-{session}", "sub-{subject}_ses-{session}_subcortical_means_pvc-rbv_ref-" + get_ref_region() + "_trc-FDG_pet.csv"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        ref_region = get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "subcortical_map"),
    log:
        os.path.join(root, "logs", "subcortical_map", "sub-{subject}_ses-{session}.log")
    shell:
        """
        mkdir -p {params.log_dir}
        python {workflow.basedir}/../functions/subcortical_map.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            -ref_region {params.ref_region} \
            > {log} 2>&1
        """

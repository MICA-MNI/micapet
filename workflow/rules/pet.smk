# PET processing rules: Linear Coreg, PVC, SUVR, Project PET, Subcortical Map

# Helper to get reference region from config
def get_ref_region():
    return config.get("ref_region", "pons")

def get_pvc_method():
    return config.get("pvc_method","rbv")

def get_linear_coreg_fs_check(wildcards):
    """Get fs_check input - mark as ancient if using existing outputs."""
    fs_check = os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "norm.mgz")
    if config.get("existing_freesurfer_dir", ""):
        return ancient(fs_check)
    return fs_check

rule linear_coreg:
    input:
        pet = inputs['pet'].path,
        t1 = inputs['T1w'].path,
        # Ensure fastsurfer completed
        fs_check = get_linear_coreg_fs_check,
    output:
        # Reg lta files - Note: Python outputs to /xfm/ subdirectory with _from-pet_to-{space}_xfm.reg.lta naming
        reg_lta_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", "sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-T1wFS_xfm.reg.lta"),
        reg_lta_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", "sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-T1wNativepro_xfm.reg.lta"),
        # Coregistered PET
        pet_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-none_ref-none_trc-{trc}_pet.nii.gz"),
        pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-none_ref-none_trc-{trc}_pet.nii.gz"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "linear_coreg"),
        fs_license = config.get("fs_license"),
        pvc_method = get_pvc_method(),
    log:
        os.path.join(root, "logs", "linear_coreg", "sub-{subject}_ses-{session}_trc-{trc}.log")
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
            -trc {wildcards.trc} \
            -pvc_method {params.pvc_method}
            >> {log} 2>&1
        """

rule pvc:
    input:
        pet_fs = rules.linear_coreg.output.pet_fs,
        pet_raw = inputs['pet'].path,
        lta = rules.linear_coreg.output.reg_lta_fs,
        gtmseg = rules.gtm_seg.output.gtmseg,
    output:
        pvc_pet_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-"+get_pvc_method()+"_ref-none_trc-{trc}_pet.nii.gz"),
        pvc_pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-"+get_pvc_method()+"_ref-none_trc-{trc}_pet.nii.gz"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        psf = config.get("psf", 4.5),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "pvc"),
        fs_license = config.get("fs_license"),
        pvc_method = get_pvc_method(),
    log:
        os.path.join(root, "logs", "pvc", "sub-{subject}_ses-{session}_trc-{trc}.log")
    run:
        if params.pvc_method == "rbv":
            shell("""
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
                    -trc {wildcards.trc} \
                    -force \
                    >> {log} 2>&1
                """)
            
        else: 
            shell("""
                set +eu  # Disable strict mode completely
                export FREESURFER_HOME=/opt/freesurfer-7.4.1
                export FS_LICENSE={params.fs_license}
                source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
                mkdir -p {params.log_dir}
                echo "=== Starting petpvc.py at $(date) ===" > {log} 2>&1
                python {workflow.basedir}/../functions/petpvc.py \
                    -sub {wildcards.subject} \
                    -ses {wildcards.session} \
                    -bids {params.bids_dir} \
                    -subj_dir {params.subj_dir} \
                    -output_dir {params.output_dir} \
                    -psf {params.psf} \
                    -trc {wildcards.trc} \
                    -pvc_method {params.pvc_method} \
                    -force \
                    >> {log} 2>&1
                """)
        

rule suvr:
    input:
        pvc_pet_fs = rules.pvc.output.pvc_pet_fs,
        pvc_pet_native = rules.pvc.output.pvc_pet_native,
    output:
        suvr_pet_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
        suvr_pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        ref_region = get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "suvr"),
        fs_license = config.get("fs_license"),
        pvc_method = get_pvc_method(),
    log:
        os.path.join(root, "logs", "suvr", "sub-{subject}_ses-{session}_trc-{trc}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/opt/freesurfer-7.4.1
        export FS_LICENSE={params.fs_license}
        source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
        mkdir -p {params.log_dir}
        echo "=== Starting suvr.py at $(date) ===" > {log} 2>&1
        python {workflow.basedir}/../functions/suvr.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            -ref_region {params.ref_region} \
            -trc {wildcards.trc} \
            -pvc_method {params.pvc_method} \
            >> {log} 2>&1
        """

def get_project_pet_data_inputs(wildcards):
    """Get project_pet_data inputs - mark surfaces as ancient if using existing outputs."""
    inputs_dict = {"suvr_pet_fs": rules.suvr.output.suvr_pet_fs}
    
    # Cortical surfaces - mark as ancient if using existing outputs (will be generated by cortical_surface rule)
    surf_L = os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "surf", f"sub-{wildcards.subject}_ses-{wildcards.session}_hemi-L_surf-fsnative_label-midthickness.surf.gii")
    surf_R = os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "surf", f"sub-{wildcards.subject}_ses-{wildcards.session}_hemi-R_surf-fsnative_label-midthickness.surf.gii")
    inputs_dict["surf_L"] = surf_L
    inputs_dict["surf_R"] = surf_R
    
    # Hippocampal surfaces - mark as ancient if using existing outputs
    hipp_L = os.path.join(root, HIPPUNFOLD_DIR_NAME, "hippunfold", f"sub-{wildcards.subject}", f"ses-{wildcards.session}", "surf", f"sub-{wildcards.subject}_ses-{wildcards.session}_hemi-L_space-T1w_den-2mm_label-hipp_midthickness.surf.gii")
    hipp_R = os.path.join(root, HIPPUNFOLD_DIR_NAME, "hippunfold", f"sub-{wildcards.subject}", f"ses-{wildcards.session}", "surf", f"sub-{wildcards.subject}_ses-{wildcards.session}_hemi-R_space-T1w_den-2mm_label-hipp_midthickness.surf.gii")
    
    if config.get("existing_hippunfold_dir", ""):
        inputs_dict["hipp_L"] = ancient(hipp_L)
        inputs_dict["hipp_R"] = ancient(hipp_R)
    else:
        inputs_dict["hipp_L"] = hipp_L
        inputs_dict["hipp_R"] = hipp_R
    
    return inputs_dict

rule project_pet_data:
    input:
        unpack(get_project_pet_data_inputs)
    output:
        # Cortical projection
        func_L = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_smooth-10mm_trc-{trc}_pet.func.gii"),
        func_R = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_smooth-10mm_trc-{trc}_pet.func.gii"),
        # Hippocampal projection
        hipp_func_L = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.func.gii"),
        hipp_func_R = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.func.gii"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        hippunfold_dir = os.path.join(root, HIPPUNFOLD_DIR_NAME),
        ref_region = get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "project_pet_data"),
        fs_license = config.get("fs_license"),
        pvc_method = get_pvc_method(),
    log:
        os.path.join(root, "logs", "project_pet_data", "sub-{subject}_ses-{session}_trc-{trc}.log")
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
            -trc {wildcards.trc} \
            -pvc_method {params.pvc_method} \
            -pvc \
            -cortical \
            -hippocampal \
            >> {log} 2>&1
        """

def get_subcortical_map_inputs(wildcards):
    """Get subcortical_map inputs - mark aparc_aseg as ancient if using existing outputs."""
    aparc_aseg = os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "aparc+aseg.mgz")
    inputs_dict = {"suvr_pet_fs": rules.suvr.output.suvr_pet_fs}
    
    if config.get("existing_freesurfer_dir", ""):
        inputs_dict["aparc_aseg"] = ancient(aparc_aseg)
    else:
        inputs_dict["aparc_aseg"] = aparc_aseg
    
    return inputs_dict

rule subcortical_map:
    input:
        unpack(get_subcortical_map_inputs)
    output:
        csv = os.path.join(root, "qc", "sub-{subject}", "ses-{session}", "sub-{subject}_ses-{session}_subcortical_means_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.csv"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        ref_region = get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "subcortical_map"),
        pvc_method = get_pvc_method(),
    log:
        os.path.join(root, "logs", "subcortical_map", "sub-{subject}_ses-{session}_trc-{trc}.log")
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
            -trc {wildcards.trc} \
            -pvc_method {params.pvc_method} \
            > {log} 2>&1
        """

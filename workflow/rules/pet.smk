# PET processing rules: Linear Coreg, PVC, SUVR, Project PET, Subcortical Map

# Helper to get reference region from config
def get_ref_region():
    return config.get("ref_region", "pons")

def get_pvc_method():
    return config.get("pvc_method","RBV-FS")

def get_pvc_mask():
    return config.get("pvc_mask", None)

def get_pvc_n_iter():
    return config.get("pvc_n_iter", 10)

def get_pvc_n_deconv():
    return config.get("pvc_n_deconv", 10)

def get_smoothing():
    if config.get("smoothing", 0) != 0:
        return " ".join(str(s) for s in config.get("smoothing"))
    else:
        return 0

def get_skip_hippunfold_arg():
    if config.get("skip_hippunfold", False):
        return ""
    else:
        return "-hippocampal"
    
def get_edge_reg_arg():
    if config.get("edge_reg", False):
        return "-edge_reg"
    else:
        return ""

def get_linear_coreg_fs_check(wildcards):
    """Get fs_check input - mark as ancient if using existing outputs."""
    fs_check = os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "norm.mgz")
    if config.get("existing_freesurfer_dir", ""):
        return ancient(fs_check)
    return fs_check

LINEAR_COREG_REG_LTA_FS = (
    "sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-T1wFS_0GenericAffine.mat" 
    if config.get("edge_reg", False) else 
    "sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-T1wFS_xfm.reg.lta"
)

LINEAR_COREG_REG_LTA_NATIVEPRO = (
    "sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-T1wNativepro_0GenericAffine.mat" 
    if config.get("edge_reg", False) else 
    "sub-{subject}_ses-{session}_trc-{trc}_from-pet_to-T1wNativepro_xfm.reg.lta"
)
    
rule linear_coreg:
    input:
        pet = inputs['pet'].path,
        t1 = inputs['T1w'].path,
        # Ensure fastsurfer completed
        fs_check = get_linear_coreg_fs_check,
    output:
        # Reg lta files - Note: Python outputs to /xfm/ subdirectory with _from-pet_to-{space}_xfm.reg.lta naming
        reg_lta_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", LINEAR_COREG_REG_LTA_FS),
        reg_lta_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", LINEAR_COREG_REG_LTA_NATIVEPRO),
        # reg_lta_fs_nativepro = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", "sub-{subject}_ses-{session}_from-T1wFS_to-T1wNativepro_xfm.reg.lta"),
        # Coregistered PET
        pet_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-none_ref-none_trc-{trc}_pet.nii.gz"),
        pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-none_ref-none_trc-{trc}_pet.nii.gz"),
        # nativepro_mri = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "anat", "sub-{subject}_ses-{session}_space-nativepro_T1w.nii.gz"), -> throws error - not same wildcards as other outputs
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "linear_coreg"),
        fs_license = config.get("fs_license"),
        pvc_method = lambda wildcards: get_pvc_method(),
        edge_reg_arg = lambda wildcards: get_edge_reg_arg() if config.get("edge_reg", False) else "",
    log:
        os.path.join(root, "logs", "linear_coreg", "sub-{subject}_ses-{session}_trc-{trc}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/micapet/freesurfer
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
            -pvc_method {params.pvc_method} \
            {params.edge_reg_arg} \
            >> {log} 2>&1
        """

def get_gtm_seg_inputs(wildcards):
    """Get GTM seg inputs - mark as ancient if using existing outputs."""
    base_paths = {
        "norm": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "norm.mgz"),
        "talairach": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "transforms", "talairach.lta"),
        "brainmask": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "brainmask.mgz"),
    }
    if config.get("existing_freesurfer_dir", ""):
        return {k: ancient(v) for k, v in base_paths.items()}
    return base_paths

rule gtm_seg:
    input:
        unpack(get_gtm_seg_inputs),
        # rules.linear_coreg.output.reg_lta_fs_nativepro,
        # reg_lta_fs_nativepro = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", "sub-{subject}_ses-{session}_from-T1wFS_to-T1wNativepro_xfm.reg.lta"),
    output:
        gtmseg_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "anat", "sub-{subject}_ses-{session}_space-T1wFS_desc-gtmseg.nii.gz"),
        gtmseg_nativepro = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "anat", "sub-{subject}_ses-{session}_space-T1wNativepro_desc-gtmseg.nii.gz"),
    params:
        bids_dir = config["bids_dir"],
        # gtm_seg.py uses -subj_dir
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "gtm_seg"),
        fs_license = config.get("fs_license"),
        trc = config.get("trc", "FDG"),
    log:
        os.path.join(root, "logs", "gtm_seg", "sub-{subject}_ses-{session}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/micapet/freesurfer
        export FS_LICENSE={params.fs_license}
        source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
        mkdir -p {params.log_dir}
        echo "=== Starting gtm_seg.py at $(date) ===" > {log} 2>&1
        python -u {workflow.basedir}/../functions/gtm_seg.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -trc {params.trc} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            >> {log} 2>&1
        """

rule pvc:
    input:
        pet_fs = rules.linear_coreg.output.pet_fs,
        pet_raw = inputs['pet'].path,
        lta = rules.linear_coreg.output.reg_lta_fs,
        gtmseg_fs = rules.gtm_seg.output.gtmseg_fs, # gtmseg in T1wFS space
        gtmseg_nativepro = rules.gtm_seg.output.gtmseg_nativepro, # gtmseg in T1wNativepro space
        # gtmseg = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "gtmseg.mgz"),
        # gtmseg_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "anat", "sub-{subject}_ses-{session}_space-T1wFS_desc-gtmseg.nii.gz"),
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
        pvc_method = lambda wildcards: get_pvc_method(),
        pvc_mask_arg = lambda wildcards: f"-pvc_mask {config['pvc_mask']}" if config.get("pvc_mask") else "",
        pvc_n_iter_arg = lambda wildcards: f"-pvc_n_iter {config['pvc_n_iter']}" if config.get("pvc_n_iter") else "",
        pvc_n_deconv_arg = lambda wildcards: f"-pvc_n_deconv {config['pvc_n_deconv']}" if config.get("pvc_n_deconv") else "",
    log:
        os.path.join(root, "logs", "pvc", "sub-{subject}_ses-{session}_trc-{trc}.log")
    run:
        if params.pvc_method == "RBV-FS":
            shell("""
                set +eu  # Disable strict mode completely
                export FREESURFER_HOME=/micapet/freesurfer
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
                export FREESURFER_HOME=/micapet/freesurfer
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
                    {params.pvc_mask_arg} \
                    {params.pvc_n_iter_arg} \
                    {params.pvc_n_deconv_arg} \
                    >> {log} 2>&1
                """)

rule suvr:
    input:
        pvc_pet_fs = rules.pvc.output.pvc_pet_fs,
        pvc_pet_native = rules.pvc.output.pvc_pet_native,
    output:
        suvr_pet_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-none_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
        suvr_pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-none_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
        suvr_pet_fs_pvc = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
        suvr_pet_native_pvc = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        ref_region = lambda wildcards: get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "suvr"),
        fs_license = config.get("fs_license"),
        pvc_method = lambda wildcards: get_pvc_method(),
    log:
        os.path.join(root, "logs", "suvr", "sub-{subject}_ses-{session}_trc-{trc}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/micapet/freesurfer
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

if config.get("nonlinear_coreg", True):
    rule nonlinear_coreg:
        input:
            suvr_pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-none_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
            suvr_pet_native_pvc = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
            nonsuvr_pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-none_ref-none_trc-{trc}_pet.nii.gz"),
            nonsuvr_pet_native_pvc = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-"+get_pvc_method()+"_ref-none_trc-{trc}_pet.nii.gz"),
        output:
            affine = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", "sub-{subject}_ses-{session}_trc-{trc}_from-T1wNativepro_to-MNI_lamaregAffine.mat"),
            warp1 = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", "sub-{subject}_ses-{session}_trc-{trc}_from-T1wNativepro_to-MNI_lamaregWarp1.nii.gz"),
            warp2 = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "xfm", "sub-{subject}_ses-{session}_trc-{trc}_from-T1wNativepro_to-MNI_lamaregWarp2.nii.gz"),
            suvr_pet_native_mni = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-MNI_pvc-none_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
            suvr_pet_native_pvc_mni = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-MNI_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.nii.gz"),
            nonsuvr_pet_native_mni = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-MNI_pvc-none_ref-none_trc-{trc}_pet.nii.gz"),
            nonsuvr_pet_native_pvc_mni = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-MNI_pvc-"+get_pvc_method()+"_ref-none_trc-{trc}_pet.nii.gz"),
        params:
            bids_dir = config["bids_dir"],
            subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
            ref_region = lambda wildcards: get_ref_region(),
            output_dir = root,
            log_dir = os.path.join(root, "logs", "nonlinear_coreg"),
            fs_license = config.get("fs_license"),
            pvc_method = lambda wildcards: get_pvc_method(),
        log:
            os.path.join(root, "logs", "nonlinear_coreg", "sub-{subject}_ses-{session}_trc-{trc}.log")
        shell:
            """
            set +eu  # Disable strict mode completely
            export FREESURFER_HOME=/micapet/freesurfer
            export FS_LICENSE={params.fs_license}
            source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
            mkdir -p {params.log_dir}
            echo "=== Starting nonlinear_coreg.py at $(date) ===" > {log} 2>&1
            python {workflow.basedir}/../functions/nonlinear_coreg.py \
                -trc {wildcards.trc} \
                -sub {wildcards.subject} \
                -ses {wildcards.session} \
                -bids {params.bids_dir} \
                -subj_dir {params.subj_dir} \
                -pvc_method {params.pvc_method} \
                -ref_region {params.ref_region} \
                -output_dir {params.output_dir} \
                >> {log} 2>&1
            """
            

def get_project_pet_data_inputs(wildcards):
    """Get project_pet_data inputs - mark surfaces as ancient if using existing outputs."""
    inputs_dict = {"fsLR_32k_L": rules.cortical_surface.output.fsLR_32k_L,
        "fsLR_32k_R": rules.cortical_surface.output.fsLR_32k_R,
        "fsnative_L": rules.cortical_surface.output.fsnative_L,
        "fsnative_R": rules.cortical_surface.output.fsnative_R,
        "suvr_pet_fs": rules.suvr.output.suvr_pet_fs,
        "suvr_pet_native": rules.suvr.output.suvr_pet_native,
        "suvr_pet_fs_pvc": rules.suvr.output.suvr_pet_fs_pvc,
        "suvr_pet_native_pvc": rules.suvr.output.suvr_pet_native_pvc}
    
    if not config.get("skip_hippunfold", False): # If not skipping HippUnfold, add HippUnfold outputs to inputs_dict
        inputs_dict["hipp_lh"] = os.path.join(root, HIPPUNFOLD_DIR_NAME, "hippunfold", f"sub-{wildcards.subject}", f"ses-{wildcards.session}", "surf", f"sub-{wildcards.subject}_ses-{wildcards.session}_hemi-L_space-T1w_den-2mm_label-hipp_midthickness.surf.gii")
        
        inputs_dict["hipp_rh"] = os.path.join(root, HIPPUNFOLD_DIR_NAME, "hippunfold", f"sub-{wildcards.subject}", f"ses-{wildcards.session}", "surf", f"sub-{wildcards.subject}_ses-{wildcards.session}_hemi-R_space-T1w_den-2mm_label-hipp_midthickness.surf.gii")
        
        if config.get("existing_hippunfold_dir", ""): # If using existing HippUnfold outputs, mark as ancient
            inputs_dict["hipp_lh"] = ancient(inputs_dict["hipp_lh"])
            inputs_dict["hipp_rh"] = ancient(inputs_dict["hipp_rh"])
    
    return inputs_dict

PROJECT_PET_DATA_OUTPUTS = {
    "func_L": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-" + get_pvc_method() + "_ref-" + get_ref_region() + "_smooth-none_trc-{trc}_pet.func.gii"),
    "func_R": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-" + get_pvc_method() + "_ref-" + get_ref_region() + "_smooth-none_trc-{trc}_pet.func.gii"),
}

if not config.get("skip_hippunfold", False):
    PROJECT_PET_DATA_OUTPUTS["hipp_func_L"] = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-" + get_pvc_method() + "_ref-" + get_ref_region() + "_trc-{trc}_pet.func.gii")
    PROJECT_PET_DATA_OUTPUTS["hipp_func_R"] = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-" + get_pvc_method() + "_ref-" + get_ref_region() + "_trc-{trc}_pet.func.gii")

rule project_pet_data:
    input:
        unpack(get_project_pet_data_inputs),
        
        # fsLR_32k_L = rules.cortical_surface.output.fsLR_32k_L,
        # fsLR_32k_R = rules.cortical_surface.output.fsLR_32k_R,
        # fsnative_L = rules.cortical_surface.output.fsnative_L,
        # fsnative_R = rules.cortical_surface.output.fsnative_R,
        # suvr_pet_fs = rules.suvr.output.suvr_pet_fs,
        # suvr_pet_native = rules.suvr.output.suvr_pet_native,
        # suvr_pet_fs_pvc = rules.suvr.output.suvr_pet_fs_pvc,
        # suvr_pet_native_pvc = rules.suvr.output.suvr_pet_native_pvc,
        # # Hippocampal surfaces
        # hipp_lh = os.path.join(root, HIPPUNFOLD_DIR_NAME, "hippunfold", "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_space-T1w_den-2mm_label-hipp_midthickness.surf.gii"),
        # hipp_rh = os.path.join(root, HIPPUNFOLD_DIR_NAME, "hippunfold", "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_space-T1w_den-2mm_label-hipp_midthickness.surf.gii"),
    output:
        func_L = PROJECT_PET_DATA_OUTPUTS["func_L"],
        func_R = PROJECT_PET_DATA_OUTPUTS["func_R"],
        
        # # Cortical projection
        # func_L = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_smooth-none_trc-{trc}_pet.func.gii"),
        # func_R = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_smooth-none_trc-{trc}_pet.func.gii"),
        # # Hippocampal projection
        # hipp_func_L = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.func.gii"),
        # hipp_func_R = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "surf", "sub-{subject}_ses-{session}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_pet.func.gii"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        hippunfold_dir = os.path.join(root, HIPPUNFOLD_DIR_NAME),
        ref_region = lambda wildcards: get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "project_pet_data"),
        fs_license = config.get("fs_license"),
        pvc_method = lambda wildcards: get_pvc_method(),
        smoothing = lambda wildcards: get_smoothing(),
        skip_hippunfold_arg = lambda wildcards: f"-hippocampal" if not config.get("skip_hippunfold", False) else "",
    log:
        os.path.join(root, "logs", "project_pet_data", "sub-{subject}_ses-{session}_trc-{trc}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/micapet/freesurfer
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
            -cortical \
            {params.skip_hippunfold_arg} \
            -smoothing {params.smoothing} \
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
        # unpack(get_subcortical_map_inputs)
        suvr_pet_fs = rules.suvr.output.suvr_pet_fs,
        aparc_aseg = os.path.join(root, FASTSURFER_DIR_NAME, "sub-{subject}_ses-{session}", "mri", "aparc+aseg.mgz"),
    output:
        csv = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "qc", "sub-{subject}_ses-{session}_pvc-"+get_pvc_method()+"_ref-" + get_ref_region() + "_trc-{trc}_subcortical_means_pet.csv"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        ref_region = lambda wildcards: get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "subcortical_map"),
        pvc_method = lambda wildcards: get_pvc_method(),
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

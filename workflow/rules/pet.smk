# PET processing rules: Linear Coreg, PVC, SUVR, Project PET, Subcortical Map

rule linear_coreg:
    input:
        pet = inputs.pet.path,
        t1 = inputs.T1w.path,
        # Implicit dependency on fastsurfer dir existence, although script checks it.
        # We can add a file from fastsurfer to ensure it ran.
        fs_check = rules.fastsurfer.output.norm
    output:
        # Reg lta files
        reg_lta_fs = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/pet/sub-{{subject}}_ses-{{session}}_trc-FDG_pet_to_T1wFS_xfm.reg.lta",
        reg_lta_native = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/pet/sub-{{subject}}_ses-{{session}}_trc-FDG_pet_to_T1wNative_xfm.reg.lta",
        # Coregistered PET
        pet_fs = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/pet/sub-{{subject}}_ses-{{session}}_space-T1wFS_pvc-none_ref-none_trc-FDG_pet.nii.gz",
        pet_native = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/pet/sub-{{subject}}_ses-{{session}}_space-T1wNative_pvc-none_ref-none_trc-FDG_pet.nii.gz"
    params:
        bids_dir = config["bids_dir"],
        subj_dir = f"derivatives/{FASTSURFER_DIR_NAME}"
    log:
        "logs/linear_coreg/sub-{subject}_ses-{session}.log"
    shell:
        """
        python functions/linear_coreg.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -pet {input.pet} \
            -mri {input.t1} \
            > {log} 2>&1
        """

rule pvc:
    input:
        pet_fs = rules.linear_coreg.output.pet_fs,  # Actually script uses original pet + lta
        pet_raw = inputs.pet.path,
        lta = rules.linear_coreg.output.reg_lta_fs,
        gtmseg = rules.gtm_seg.output.gtmseg
    output:
        pvc_pet_fs = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/pet/sub-{{subject}}_ses-{{session}}_space-T1wFS_pvc-rbv_ref-none_trc-FDG_pet.nii.gz",
        # pcv.py output list also includes native space? Checking list_of_tests.txt... yes.
        pvc_pet_native = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/pet/sub-{{subject}}_ses-{{session}}_space-T1wNative_pvc-rbv_ref-none_trc-FDG_pet.nii.gz"
    params:
        bids_dir = config["bids_dir"],
        subj_dir = f"derivatives/{FASTSURFER_DIR_NAME}",
        psf = config.get("psf", 4.5)
    log:
        "logs/pvc/sub-{subject}_ses-{session}.log"
    shell:
        """
        python functions/pvc.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -psf {params.psf} \
            > {log} 2>&1
        """

rule suvr:
    input:
        pvc_pet_fs = rules.pvc.output.pvc_pet_fs,
        pvc_pet_native = rules.pvc.output.pvc_pet_native
    output:
        # The outputs depend on the ref_region parameter. Default is 'pons'.
        # We'll assume 'pons' for the rule, but user config might change it.
        # Ideally, we should use dynamic output or just list the one defined in config.
        suvr_pet_fs = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/pet/sub-{{subject}}_ses-{{session}}_space-T1wFS_pvc-rbv_ref-{config.get('ref_region', 'pons')}_trc-FDG_pet.nii.gz",
        suvr_pet_native = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/pet/sub-{{subject}}_ses-{{session}}_space-T1wNative_pvc-rbv_ref-{config.get('ref_region', 'pons')}_trc-FDG_pet.nii.gz"
    params:
        bids_dir = config["bids_dir"],
        subj_dir = f"derivatives/{FASTSURFER_DIR_NAME}",
        ref_region = config.get("ref_region", "pons")
    log:
        "logs/suvr/sub-{subject}_ses-{session}.log"
    shell:
        """
        python functions/suvr.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -ref_region {params.ref_region} \
            > {log} 2>&1
        """

rule project_pet_data:
    input:
        suvr_pet_fs = rules.suvr.output.suvr_pet_fs,
        surf_L = rules.cortical_surface.output.fsnative_L,
        surf_R = rules.cortical_surface.output.fsnative_R,
        hipp_L = rules.hippunfold.output.hipp_lh,
        hipp_R = rules.hippunfold.output.hipp_rh
    output:
        # Cortical projection
        func_L = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-L_surf-fsLR-32k_label-midthickness_pvc-rbv_ref-{config.get('ref_region', 'pons')}_smooth-10mm_trc-FDG_pet.func.gii",
        func_R = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-R_surf-fsLR-32k_label-midthickness_pvc-rbv_ref-{config.get('ref_region', 'pons')}_smooth-10mm_trc-FDG_pet.func.gii",
        # Hippocampal projection
        hipp_func_L = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-L_surf-hipp_den-2mm_label-midthickness_pvc-rbv_ref-{config.get('ref_region', 'pons')}_trc-FDG_pet.func.gii",
        hipp_func_R = f"derivatives/{MICAPET_DIR_NAME}/sub-{{subject}}/ses-{{session}}/surf/sub-{{subject}}_ses-{{session}}_hemi-R_surf-hipp_den-2mm_label-midthickness_pvc-rbv_ref-{config.get('ref_region', 'pons')}_trc-FDG_pet.func.gii"
    params:
        bids_dir = config["bids_dir"],
        subj_dir = f"derivatives/{FASTSURFER_DIR_NAME}",
        hippunfold_dir = f"derivatives/{HIPPUNFOLD_DIR_NAME}",
        ref_region = config.get("ref_region", "pons")
    log:
        "logs/project_pet_data/sub-{subject}_ses-{session}.log"
    shell:
        """
        python functions/project_pet_data.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -hippunfold_dir {params.hippunfold_dir} \
            -ref_region {params.ref_region} \
            -pvc \
            -cortical \
            -hippocampal \
            > {log} 2>&1
        """

rule subcortical_map:
    input:
        suvr_pet_fs = rules.suvr.output.suvr_pet_fs,
        aparc_aseg = rules.fastsurfer.output.aparc_aseg
    output:
        csv = f"qc/sub-{{subject}}/ses-{{session}}/sub-{{subject}}_ses-{{session}}_subcortical_means_pvc-rbv_ref-{config.get('ref_region', 'pons')}_trc-FDG_pet.csv"
    params:
        bids_dir = config["bids_dir"],
        subj_dir = f"derivatives/{FASTSURFER_DIR_NAME}",
        ref_region = config.get("ref_region", "pons")
    log:
        "logs/subcortical_map/sub-{subject}_ses-{session}.log"
    shell:
        """
        python functions/subcortical_map.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -ref_region {params.ref_region} \
            > {log} 2>&1
        """

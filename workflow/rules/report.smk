# Report generation

rule clinical_report:
    input:
        suvr_pet_fs = rules.suvr.output.suvr_pet_fs,
        func_L = rules.project_pet_data.output.func_L,
        func_R = rules.project_pet_data.output.func_R,
        hipp_func_L = rules.project_pet_data.output.hipp_func_L,
        hipp_func_R = rules.project_pet_data.output.hipp_func_R,
        csv = rules.subcortical_map.output.csv,
    output:
        report = os.path.join(root, "qc", "sub-{subject}_ses-{session}_report.html"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        ref_region = config.get("ref_region", "pons"),
        output_dir = root,
    log:
        os.path.join(root, "logs", "clinical_report", "sub-{subject}_ses-{session}.log")
    shell:
        """
        python {workflow.basedir}/../functions/clinical_reports.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            -ref_region {params.ref_region} \
            > {log} 2>&1
        """

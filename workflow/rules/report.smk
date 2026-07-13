# Report generation
def get_pvc_method():
    return config.get("pvc_method","RBV-FS")

def get_ref_region():
    return config.get("ref_region","pons")

rule report:
    input:
        suvr_pet_fs = rules.suvr.output.suvr_pet_fs,
        func_L = rules.project_pet_data.output.func_L,
        func_R = rules.project_pet_data.output.func_R,
        csv = rules.subcortical_map.output.csv,
    output:
        report = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "qc", "sub-{subject}_ses-{session}_pvc-"+get_pvc_method()+"_ref-"+get_ref_region()+"_trc-{trc}_report.html"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        ref_region = lambda wildcards: get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "report"),
        fs_license = config.get("fs_license"),
        pvc_method = lambda wildcards: get_pvc_method(),
        skip_hippunfold_arg = lambda wildcards: f"-hippocampal" if not config.get("skip_hippunfold", False) else "",
    log:
        os.path.join(root, "logs", "report", "sub-{subject}_ses-{session}_ref-"+get_ref_region()+"_trc-{trc}.log")
    shell:
        """
        set +eu  # Disable strict mode completely
        export FREESURFER_HOME=/micapet/freesurfer
        export FS_LICENSE={params.fs_license}
        source $FREESURFER_HOME/SetUpFreeSurfer.sh || true
        mkdir -p {params.log_dir}
        python {workflow.basedir}/../functions/report.py \
            -sub {wildcards.subject} \
            -ses {wildcards.session} \
            -bids {params.bids_dir} \
            -subj_dir {params.subj_dir} \
            -output_dir {params.output_dir} \
            -ref_region {params.ref_region} \
            -pvc_method {params.pvc_method} \
            -trc {wildcards.trc} \
            {params.skip_hippunfold_arg} \
            > {log} 2>&1
        """

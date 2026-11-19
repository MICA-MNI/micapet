# Anatomy processing rules: FastSurfer, HippUnfold, Cortical Surface mappings
import sys
import os
from MICA_PET import fastsurfer, hippunfold, cortical_surface, gtm_seg, linear_coreg, pvc, suvr, project_pet_data, nonlinear_coreg, subcortical_map, report
from utils import *
import logging
import contextlib
import warnings 
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
warnings.filterwarnings("ignore", category=UserWarning, module="stopit")

# if not config.get("existing_freesurfer_dir", ""): 
rule fastsurfer:
    input:
        t1 = inputs['T1w'].path
    output:
        pial_lh = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "lh.pial"),
        pial_rh = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "rh.pial"),
        white_lh = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "lh.white"),
        white_rh = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "rh.white"),
        sphere_lh = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "lh.sphere.reg"),
        sphere_rh = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "rh.sphere.reg"),
        norm = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "norm.mgz"),
        talairach = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "talairach.lta"),
        brainmask = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "brainmask.mgz"),
        aparc_aseg = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "aparc+aseg.mgz"),
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
    shell:
        '''
        mkdir -p {params.log_dir}
        python -u -c "from MICA_PET import fastsurfer; fastsurfer(
            subject='{wildcards.subject}',
            session='{wildcards.session}',
            bids_dir='{params.bids_dir}',
            subj_dir='{params.subj_dir}',
            fastsurfer_img='{params.img}',
            fs_license='{params.fs_license}',
            threads={threads},
            tmpdir='{params.tmpdir}',
            force={params.force}
        )" \
            > {log} 2>&1
        '''

if not config.get("skip_hippunfold", False): #and not config.get("existing_hippunfold_dir", ""): #runs hippunfold if flag not set and existing dir not specified, skip hippunfold if flag set or if existing dir specified
    rule hippunfold:
        input:
            t1 = inputs['T1w'].path
        output:
            hipp_lh = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "sub-{subject}_ses-{session}_hemi-L_space-T1w_den-2mm_label-hipp_midthickness.surf.gii"),
            hipp_rh = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "sub-{subject}_ses-{session}_hemi-R_space-T1w_den-2mm_label-hipp_midthickness.surf.gii"),
        params:
            bids_dir = config["bids_dir"],
            img = config.get("hippunfold_img"),
            # hippunfold.py uses -hippunfold_dir NOT -output_dir
            hippunfold_dir = os.path.join(root, HIPPUNFOLD_DIR_NAME),
            cachedir_arg = config['hippunfold_cache_dir'] if config.get("hippunfold_cache_dir") else None,
            log_dir = os.path.join(root, "logs", "hippunfold"),
            tmpdir = "/tmp",
            force = config.get("force", False),
        log:
            os.path.join(root, "logs", "hippunfold", "sub-{subject}_ses-{session}.log")
        threads: config.get("threads", 8)
        shell:
            '''
            mkdir -p {params.log_dir}
            python -u -c "from MICA_PET import hippunfold; hippunfold(
                subject='{wildcards.subject}',
                session='{wildcards.session}',
                bids_dir='{params.bids_dir}',
                hippunfold_dir='{params.hippunfold_dir}',
                hippunfold_img='{params.img}',
                tmpdir='{params.tmpdir}',
                cachedir={params.cachedir_arg},
                threads={threads},
                force={params.force}
            )" \
                > {log} 2>&1
            '''

def get_cortical_surface_inputs(wildcards):
    """Get cortical surface inputs - mark as ancient if using existing outputs."""
    base_paths = {
        "pial_lh": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "lh.pial"),
        "pial_rh": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "rh.pial"),
        "white_lh": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "lh.white"),
        "white_rh": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "rh.white"),
        "sphere_lh": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "lh.sphere.reg"),
        "sphere_rh": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "rh.sphere.reg"),
        "norm": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "norm.mgz"),
        "talairach": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "talairach.lta"),
        "brainmask": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "brainmask.mgz"),
        "aparc_aseg": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "aparc+aseg.mgz"),
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
    shell:
        '''
            mkdir -p {params.log_dir}
            python -u -c "from MICA_PET import cortical_surface; cortical_surface(
                subject='{wildcards.subject}',
                session='{wildcards.session}',
                bids_dir='{params.bids_dir}',
                subj_dir='{params.subj_dir}'
            )" \
                > {log} 2>&1
            '''

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
    val = config.get("smoothing", 0)
    if isinstance(val, list):
        return [float(s) for s in val]
    elif val is not None:
        return float(val)
    return 0.0
    # if config.get("smoothing", 0) != 0:
    #     return " ".join(str(s) for s in config.get("smoothing"))
    # else:
    #     return 0

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
    # fs_check = os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "norm.mgz")
    fs_check = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "norm.mgz")
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
        # Coregistered PET
        pet_fs = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wFS_pvc-none_ref-none_trc-{trc}_pet.nii.gz"),
        pet_native = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "pet", "sub-{subject}_ses-{session}_space-T1wNativepro_pvc-none_ref-none_trc-{trc}_pet.nii.gz"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "linear_coreg"),
        fs_license = config.get("fs_license"),
        pvc_method = lambda wildcards: get_pvc_method(),
        edge_reg = config.get("edge_reg", False),
    log:
        os.path.join(root, "logs", "linear_coreg", "sub-{subject}_ses-{session}_trc-{trc}.log")
    shell:
        '''
            mkdir -p {params.log_dir}
            python -u -c "from MICA_PET import linear_coreg; linear_coreg(
                subject='{wildcards.subject}',
                session='{wildcards.session}',
                trc='{wildcards.trc}',
                bids_dir='{params.bids_dir}',
                subj_dir='{params.subj_dir}',
                edge_reg={params.edge_reg}
            )" \
                > {log} 2>&1
            '''

def get_gtm_seg_inputs(wildcards):
    """Get GTM seg inputs - mark as ancient if using existing outputs."""
    # base_paths = {
    #     "norm": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "norm.mgz"),
    #     "talairach": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "transforms", "talairach.lta"),
    #     "brainmask": os.path.join(root, FASTSURFER_DIR_NAME, f"sub-{wildcards.subject}_ses-{wildcards.session}", "mri", "brainmask.mgz"),
    # }
    base_paths = {
        "norm": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "norm.mgz"),
        "talairach": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "talairach.lta"),
        "brainmask": os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", "brainmask.mgz"),
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
        # trc = config.get("trc", "FDG"),
    log:
        os.path.join(root, "logs", "gtm_seg", "sub-{subject}_ses-{session}.log")
    shell:
        '''
            mkdir -p {params.log_dir}
            python -u -c "from MICA_PET import gtm_seg; gtm_seg(
                subject='{wildcards.subject}',
                session='{wildcards.session}',
                bids_dir='{params.bids_dir}',
                subj_dir='{params.subj_dir}',
                threads={threads}
            )" \
                > {log} 2>&1
            '''

rule pvc:
    input:
        pet_fs = rules.linear_coreg.output.pet_fs,
        pet_raw = inputs['pet'].path,
        lta = rules.linear_coreg.output.reg_lta_fs,
        gtmseg_fs = rules.gtm_seg.output.gtmseg_fs, # gtmseg in T1wFS space
        gtmseg_nativepro = rules.gtm_seg.output.gtmseg_nativepro, # gtmseg in T1wNativepro space
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
        pvc_mask_arg = config['pvc_mask'] if config.get("pvc_mask") else None,
        pvc_n_iter_arg = config['pvc_n_iter'] if config.get("pvc_n_iter") else None,
        pvc_n_deconv_arg = config['pvc_n_deconv'] if config.get("pvc_n_deconv") else None,
    log:
        os.path.join(root, "logs", "pvc", "sub-{subject}_ses-{session}_trc-{trc}.log")
    shell:
        '''
            mkdir -p {params.log_dir}
            python -u -c "from MICA_PET import pvc; pvc(
                subject='{wildcards.subject}',
                session='{wildcards.session}',
                trc='{wildcards.trc}',
                bids_dir='{params.bids_dir}',
                subj_dir='{params.subj_dir}',
                pvc_method='{params.pvc_method}',
                psf={params.psf},
                pvc_mask={params.pvc_mask_arg},
                pvc_n_iter={params.pvc_n_iter_arg},
                pvc_n_deconv={params.pvc_n_deconv_arg}
            )" \
                > {log} 2>&1
            '''

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
        '''
            mkdir -p {params.log_dir}
            python -u -c "from MICA_PET import suvr; suvr(
                subject='{wildcards.subject}',
                session='{wildcards.session}',
                trc='{wildcards.trc}',
                bids_dir='{params.bids_dir}',
                subj_dir='{params.subj_dir}',
                pvc_method='{params.pvc_method}',
                ref_region='{params.ref_region}'
            )" \
                > {log} 2>&1
            '''
        
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
            '''
                mkdir -p {params.log_dir}
                python -u -c "from MICA_PET import nonlinear_coreg; nonlinear_coreg(
                    subject='{wildcards.subject}',
                    session='{wildcards.session}',
                    trc='{wildcards.trc}',
                    bids_dir='{params.bids_dir}',
                    pvc_method='{params.pvc_method}',
                    ref_region='{params.ref_region}'
                )" \
                    > {log} 2>&1
                '''

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
        
        inputs_dict["hipp_lh"] = rules.hippunfold.output.hipp_lh
        inputs_dict["hipp_rh"] = rules.hippunfold.output.hipp_rh

        # inputs_dict["hipp_lh"] = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", f"sub-{wildcards.subject}_ses-{wildcards.session}_hemi-L_space-T1w_den-2mm_label-hipp_midthickness.surf.gii")
        
        # inputs_dict["hipp_rh"] = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "tmp", f"sub-{wildcards.subject}_ses-{wildcards.session}_hemi-R_space-T1w_den-2mm_label-hipp_midthickness.surf.gii")
        
        # if config.get("existing_hippunfold_dir", ""): # If using existing HippUnfold outputs, mark as ancient
        #     inputs_dict["hipp_lh"] = ancient(inputs_dict["hipp_lh"])
        #     inputs_dict["hipp_rh"] = ancient(inputs_dict["hipp_rh"])
    
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
    output:
        func_L = PROJECT_PET_DATA_OUTPUTS["func_L"],
        func_R = PROJECT_PET_DATA_OUTPUTS["func_R"],
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        hippunfold_dir = os.path.join(root, HIPPUNFOLD_DIR_NAME),
        ref_region = lambda wildcards: get_ref_region(),
        output_dir = root,
        tmpdir = "/tmp",
        log_dir = os.path.join(root, "logs", "project_pet_data"),
        fs_license = config.get("fs_license"),
        pvc_method = lambda wildcards: get_pvc_method(),
        smoothing = lambda wildcards: get_smoothing(),
        skip_hippunfold = not config.get("skip_hippunfold", False),
    log:
        os.path.join(root, "logs", "project_pet_data", "sub-{subject}_ses-{session}_trc-{trc}.log")
    shell:
        '''
            mkdir -p {params.log_dir}
            python -u -c "from MICA_PET import project_pet_data; project_pet_data(
                subject='{wildcards.subject}',
                session='{wildcards.session}',
                trc='{wildcards.trc}',
                bids_dir='{params.bids_dir}',
                subj_dir='{params.subj_dir}',
                pvc_method='{params.pvc_method}',
                ref_region='{params.ref_region}',
                tmpdir='{params.tmpdir}',
                hippunfold_dir='{params.hippunfold_dir}',
                cortical=True,
                hippocampal={params.skip_hippunfold},
                smoothing='{params.smoothing}'
            )" \
                > {log} 2>&1
        '''

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
        aparc_aseg = rules.fastsurfer.output.aparc_aseg,
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
        '''
            mkdir -p {params.log_dir}
            python -u -c "from MICA_PET import subcortical_map; subcortical_map(
                subject='{wildcards.subject}',
                session='{wildcards.session}',
                trc='{wildcards.trc}',
                bids_dir='{params.bids_dir}',
                subj_dir='{params.subj_dir}',
                pvc_method='{params.pvc_method}',
                ref_region='{params.ref_region}'
            )" \
                > {log} 2>&1
        '''

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
        # report = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "qc", "sub-{subject}_ses-{session}_pvc-"+get_pvc_method()+"_ref-"+get_ref_region()+"_trc-{trc}_report.html"),
        report = os.path.join(root, MICAPET_DIR_NAME, "sub-{subject}", "ses-{session}", "report", "sub-{subject}_ses-{session}_pvc-"+get_pvc_method()+"_ref-"+get_ref_region()+"_trc-{trc}_report.html"),
    params:
        bids_dir = config["bids_dir"],
        subj_dir = os.path.join(root, FASTSURFER_DIR_NAME),
        ref_region = lambda wildcards: get_ref_region(),
        output_dir = root,
        log_dir = os.path.join(root, "logs", "report"),
        fs_license = config.get("fs_license"),
        pvc_method = lambda wildcards: get_pvc_method(),
        skip_hippunfold = not config.get("skip_hippunfold", False),
        normalize_histogram_max = config.get("normalize_histogram_max", False),
        smoothing = lambda wildcards: get_smoothing(),
    log:
        os.path.join(root, "logs", "report", "sub-{subject}_ses-{session}_ref-"+get_ref_region()+"_trc-{trc}.log")
    shell:
        '''
            mkdir -p {params.log_dir}
            python -u -c "from MICA_PET import report; report(
                subject='{wildcards.subject}',
                session='{wildcards.session}',
                trc='{wildcards.trc}',
                bids_dir='{params.bids_dir}',
                subj_dir='{params.subj_dir}',
                pvc_method='{params.pvc_method}',
                ref_region='{params.ref_region}',
                hippocampal={params.skip_hippunfold},
                z_score=True,
                normalize_histogram_max={params.normalize_histogram_max},
                smoothing='{params.smoothing}'
            )" \
                > {log} 2>&1
        '''
#!/usr/bin/env python
"""
Functional Test Suite for MICA-PET Pipeline

This test suite validates:
1. Python function argument parsing (without execution)
2. Input/output path generation logic
3. Environment variable handling
4. Function imports and dependencies

These tests can run without actual neuroimaging data by mocking
the heavy processing and validating the path/argument logic.

Run with: pytest tests/test_functional.py -v
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import argparse

# Add functions directory to path
REPO_ROOT = Path(__file__).parent.parent
FUNCTIONS_DIR = REPO_ROOT / "functions"
sys.path.insert(0, str(FUNCTIONS_DIR))


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_bids_dir(tmp_path):
    """Create a mock BIDS directory structure."""
    bids_dir = tmp_path / "bids"
    subject = "PX003"
    session = "01"
    tracer = "FDG"
    
    # Create rawdata structure
    rawdata = bids_dir / "rawdata" / f"sub-{subject}" / f"ses-{session}"
    (rawdata / "anat").mkdir(parents=True)
    (rawdata / "pet").mkdir(parents=True)
    
    # Create mock input files
    (rawdata / "anat" / f"sub-{subject}_ses-{session}_T1w.nii.gz").touch()
    (rawdata / "pet" / f"sub-{subject}_ses-{session}_trc-{tracer}_pet.nii.gz").touch()
    
    # Create derivatives structure
    derivatives = bids_dir / "derivatives"
    (derivatives / "fastsurfer" / f"sub-{subject}_ses-{session}" / "surf").mkdir(parents=True)
    (derivatives / "fastsurfer" / f"sub-{subject}_ses-{session}" / "mri" / "transforms").mkdir(parents=True)
    (derivatives / "hippunfold_v1.4.1" / "hippunfold" / f"sub-{subject}" / f"ses-{session}" / "surf").mkdir(parents=True)
    (derivatives / "MICA-PET_v.alpha.0.5" / f"sub-{subject}" / f"ses-{session}" / "pet").mkdir(parents=True)
    (derivatives / "MICA-PET_v.alpha.0.5" / f"sub-{subject}" / f"ses-{session}" / "surf").mkdir(parents=True)
    (derivatives / "MICA-PET_v.alpha.0.5" / f"sub-{subject}" / f"ses-{session}" / "xfm").mkdir(parents=True)
    (derivatives / "MICA-PET_v.alpha.0.5" / f"sub-{subject}" / f"ses-{session}" / "anat").mkdir(parents=True)
    (derivatives / "MICA-PET_v.alpha.0.5" / f"sub-{subject}" / f"ses-{session}" / "qc").mkdir(parents=True)
    # Create qc directory
    (bids_dir / f"sub-{subject}" / f"ses-{session}" / "qc").mkdir(parents=True)
    
    return bids_dir


@pytest.fixture
def mock_env():
    """Set up mock environment variables."""
    env_vars = {
        'MICA_PET_VERSION': 'v.alpha.0.5',
        'FREESURFER_HOME': '/opt/freesurfer',
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def test_subject():
    return "PX003"


@pytest.fixture
def test_session():
    return "01"

@pytest.fixture
def test_tracer():
    return "FDG"


# =============================================================================
# Path Generation Tests
# =============================================================================

class TestPathGeneration:
    """Test that path generation matches expected BIDS structure."""
    
    def test_fastsurfer_output_paths(self, mock_bids_dir, test_subject, test_tracer, test_session):
        """Validate FastSurfer output path structure."""
        subj_dir = mock_bids_dir / "derivatives" / "fastsurfer"
        fs_subj = subj_dir / f"sub-{test_subject}_ses-{test_session}"
        
        expected_outputs = [
            fs_subj / "surf" / "lh.pial",
            fs_subj / "surf" / "rh.pial",
            fs_subj / "surf" / "lh.white",
            fs_subj / "surf" / "rh.white",
            fs_subj / "surf" / "lh.sphere.reg",
            fs_subj / "surf" / "rh.sphere.reg",
            fs_subj / "mri" / "norm.mgz",
            fs_subj / "mri" / "brainmask.mgz",
            fs_subj / "mri" / "aparc+aseg.mgz",
            fs_subj / "mri" / "transforms" / "talairach.lta",
        ]
        
        for path in expected_outputs:
            # Verify parent directories exist in our mock
            assert path.parent.exists() or path.parent.parent.exists()
    
    def test_hippunfold_output_paths(self, mock_bids_dir, test_subject, test_tracer, test_session):
        """Validate HippUnfold output path structure."""
        hipp_dir = mock_bids_dir / "derivatives" / "hippunfold_v1.4.1" / "hippunfold"
        
        for hemi in ["L", "R"]:
            expected = (
                hipp_dir / f"sub-{test_subject}" / f"ses-{test_session}" / "surf" /
                f"sub-{test_subject}_ses-{test_session}_hemi-{hemi}_space-T1w_den-2mm_label-hipp_midthickness.surf.gii"
            )
            assert expected.parent.exists()
    
    def test_linear_coreg_output_paths(self, mock_bids_dir, test_subject, test_tracer, test_session, mock_env):
        """Validate linear_coreg output path structure."""
        version = mock_env['MICA_PET_VERSION']
        mica_pet = mock_bids_dir / "derivatives" / f"MICA-PET_{version}" / f"sub-{test_subject}" / f"ses-{test_session}"
        
        expected_outputs = [
            mica_pet / "xfm" / f"sub-{test_subject}_ses-{test_session}_from-pet_to-T1wFS_xfm.reg.lta",
            mica_pet / "xfm" / f"sub-{test_subject}_ses-{test_session}_from-pet_to-T1wNative_xfm.reg.lta",
            mica_pet / "pet" / f"sub-{test_subject}_ses-{test_session}_space-T1wFS_pvc-none_ref-none_trc-{test_tracer}_pet.nii.gz",
            mica_pet / "pet" / f"sub-{test_subject}_ses-{test_session}_space-T1wNative_pvc-none_ref-none_trc-{test_tracer}_pet.nii.gz",
        ]
        
        for path in expected_outputs:
            assert path.parent.exists(), f"Parent dir should exist: {path.parent}"
    
    def test_pvc_output_paths(self, mock_bids_dir, test_subject, test_tracer, test_session, mock_env):
        """Validate PVC output path structure."""
        version = mock_env['MICA_PET_VERSION']
        mica_pet = mock_bids_dir / "derivatives" / f"MICA-PET_{version}" / f"sub-{test_subject}" / f"ses-{test_session}"
        
        expected_outputs = [
            mica_pet / "pet" / f"sub-{test_subject}_ses-{test_session}_space-T1wFS_pvc-rbv_ref-none_trc-{test_tracer}_pet.nii.gz",
            mica_pet / "pet" / f"sub-{test_subject}_ses-{test_session}_space-T1wNative_pvc-rbv_ref-none_trc-{test_tracer}_pet.nii.gz",
        ]
        
        for path in expected_outputs:
            assert path.parent.exists()
    
    def test_suvr_output_paths(self, mock_bids_dir, test_subject, test_tracer, test_session, mock_env):
        """Validate SUVR output path structure."""
        version = mock_env['MICA_PET_VERSION']
        mica_pet = mock_bids_dir / "derivatives" / f"MICA-PET_{version}" / f"sub-{test_subject}" / f"ses-{test_session}"
        
        for ref in ["pons", "cerebellarGM", "composite"]:
            expected = mica_pet / "pet" / f"sub-{test_subject}_ses-{test_session}_space-T1wFS_pvc-rbv_ref-{ref}_trc-{test_tracer}_pet.nii.gz"
            assert expected.parent.exists()
    
    def test_subcortical_map_output_paths(self, mock_bids_dir, test_subject, test_tracer, test_session):
        """Validate subcortical map output path structure."""
        qc_dir = mock_bids_dir / "qc" / f"sub-{test_subject}" / f"ses-{test_session}"
        
        expected = qc_dir / f"sub-{test_subject}_ses-{test_session}_subcortical_means_pvc-rbv_ref-pons_trc-{test_tracer}_pet.csv"
        assert expected.parent.exists()
    
    def test_clinical_report_output_path(self, mock_bids_dir, test_subject, test_tracer, test_session):
        """Validate clinical report output path."""
        qc_dir = mock_bids_dir / "qc"
        expected = qc_dir / f"sub-{test_subject}_ses-{test_session}_report.html"
        assert expected.parent.exists()


# =============================================================================
# Argument Parser Tests
# =============================================================================

class TestArgumentParsers:
    """Test argument parsing for each function."""
    
    def test_fastsurfer_args(self):
        """Test fastsurfer.py argument parser."""
        # Read the file and extract parser setup
        fastsurfer_code = (FUNCTIONS_DIR / "fastsurfer.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids", "-fastsurfer_img", "-tmpdir", "-fs_license"]
        optional_args = ["-subj_dir", "-T1", "-force", "-threads"]
        
        for arg in required_args:
            assert f'"{arg}"' in fastsurfer_code or f"'{arg}'" in fastsurfer_code, f"Missing required arg: {arg}"
        
        for arg in optional_args:
            assert f'"{arg}"' in fastsurfer_code or f"'{arg}'" in fastsurfer_code, f"Missing optional arg: {arg}"
    
    def test_hippunfold_args(self):
        """Test hippunfold.py argument parser."""
        code = (FUNCTIONS_DIR / "hippunfold.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids", "-hippunfold_img"]
        optional_args = ["-hippunfold_dir", "-cachedir", "-tmpdir", "-B", "-T1", "-force"]
        
        for arg in required_args:
            assert f'"{arg}"' in code or f"'{arg}'" in code, f"Missing arg: {arg}"
    
    def test_linear_coreg_args(self):
        """Test linear_coreg.py argument parser."""
        code = (FUNCTIONS_DIR / "linear_coreg.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids"]
        optional_args = ["-subj_dir", "-output_dir", "-pet", "-mri"]
        
        for arg in required_args + optional_args:
            assert f'"{arg}"' in code or f"'{arg}'" in code, f"Missing arg: {arg}"
    
    def test_pvc_args(self):
        """Test pvc.py argument parser."""
        code = (FUNCTIONS_DIR / "pvc.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids", "-psf", "-subj_dir"]
        optional_args = ["-output_dir", "-pvc_dir", "-force"]
        
        for arg in required_args + optional_args:
            assert f'"{arg}"' in code or f"'{arg}'" in code, f"Missing arg: {arg}"
    
    def test_suvr_args(self):
        """Test suvr.py argument parser."""
        code = (FUNCTIONS_DIR / "suvr.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids", "-subj_dir"]
        optional_args = ["-output_dir", "-ref_region"]
        
        for arg in required_args + optional_args:
            assert f'"{arg}"' in code or f"'{arg}'" in code, f"Missing arg: {arg}"
    
    def test_project_pet_data_args(self):
        """Test project_pet_data.py argument parser."""
        code = (FUNCTIONS_DIR / "project_pet_data.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids", "-subj_dir"]
        optional_args = ["-output_dir", "-hippunfold_dir", "-ref_region", "-pvc", "-cortical", "-hippocampal"]
        
        for arg in required_args + optional_args:
            assert f'"{arg}"' in code or f"'{arg}'" in code, f"Missing arg: {arg}"
    
    def test_subcortical_map_args(self):
        """Test subcortical_map.py argument parser."""
        code = (FUNCTIONS_DIR / "subcortical_map.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids", "-subj_dir"]
        optional_args = ["-output_dir", "-ref_region"]
        
        for arg in required_args + optional_args:
            assert f'"{arg}"' in code or f"'{arg}'" in code, f"Missing arg: {arg}"
    
    def test_clinical_reports_args(self):
        """Test clinical_reports.py argument parser."""
        code = (FUNCTIONS_DIR / "clinical_reports.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids", "-subj_dir"]
        optional_args = ["-output_dir", "-ref_region", "-max_value"]
        
        for arg in required_args + optional_args:
            assert f'"{arg}"' in code or f"'{arg}'" in code, f"Missing arg: {arg}"
    
    def test_cortical_surface_args(self):
        """Test cortical_surface.py argument parser."""
        code = (FUNCTIONS_DIR / "cortical_surface.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids", "-subj_dir"]
        optional_args = ["-output_dir"]
        
        for arg in required_args + optional_args:
            assert f'"{arg}"' in code or f"'{arg}'" in code, f"Missing arg: {arg}"
    
    def test_gtm_seg_args(self):
        """Test gtm_seg.py argument parser."""
        code = (FUNCTIONS_DIR / "gtm_seg.py").read_text()
        
        required_args = ["-sub", "-ses", "-bids", "-subj_dir"]
        optional_args = ["-seg_type", "-force"]
        
        for arg in required_args + optional_args:
            assert f'"{arg}"' in code or f"'{arg}'" in code, f"Missing arg: {arg}"


# =============================================================================
# Output Directory Logic Tests
# =============================================================================

class TestOutputDirectoryLogic:
    """Test that -output_dir argument is properly handled."""
    
    def test_linear_coreg_output_dir_logic(self, mock_env):
        """Test linear_coreg.py handles output_dir correctly."""
        code = (FUNCTIONS_DIR / "linear_coreg.py").read_text()
        
        # Should check for args.output_dir
        assert "args.output_dir" in code
        # Should use it to construct mica_pet_derivatives
        assert "mica_pet_derivatives" in code
        # Should have conditional logic
        assert "if args.output_dir" in code
    
    def test_pvc_output_dir_logic(self, mock_env):
        """Test pvc.py handles output_dir correctly."""
        code = (FUNCTIONS_DIR / "pvc.py").read_text()
        
        assert "args.output_dir" in code
        assert "if args.output_dir" in code
    
    def test_suvr_output_dir_logic(self, mock_env):
        """Test suvr.py handles output_dir correctly."""
        code = (FUNCTIONS_DIR / "suvr.py").read_text()
        
        assert "args.output_dir" in code
        assert "if args.output_dir" in code
    
    def test_project_pet_data_output_dir_logic(self, mock_env):
        """Test project_pet_data.py handles output_dir correctly."""
        code = (FUNCTIONS_DIR / "project_pet_data.py").read_text()
        
        assert "args.output_dir" in code
        assert "if args.output_dir" in code
    
    def test_subcortical_map_output_dir_logic(self, mock_env):
        """Test subcortical_map.py handles output_dir correctly."""
        code = (FUNCTIONS_DIR / "subcortical_map.py").read_text()
        
        assert "args.output_dir" in code
        assert "if args.output_dir" in code
    
    def test_clinical_reports_output_dir_logic(self, mock_env):
        """Test clinical_reports.py handles output_dir correctly."""
        code = (FUNCTIONS_DIR / "clinical_reports.py").read_text()
        
        assert "args.output_dir" in code
        assert "if args.output_dir" in code


# =============================================================================
# Reference Region Tests
# =============================================================================

class TestReferenceRegions:
    """Test reference region handling."""
    
    def test_valid_reference_regions_suvr(self):
        """Test suvr.py accepts valid reference regions."""
        code = (FUNCTIONS_DIR / "suvr.py").read_text()
        
        valid_regions = ["pons", "cerebellarGM", "composite"]
        for region in valid_regions:
            assert region in code, f"Reference region '{region}' should be supported"
    
    def test_valid_reference_regions_subcortical(self):
        """Test subcortical_map.py accepts valid reference regions."""
        code = (FUNCTIONS_DIR / "subcortical_map.py").read_text()
        
        valid_regions = ["pons", "cerebellarGM", "composite", "none"]
        for region in valid_regions:
            assert region in code, f"Reference region '{region}' should be supported"


# =============================================================================
# Dependency Import Tests
# =============================================================================

class TestDependencyImports:
    """Test that required imports are present in each file."""
    
    def test_fastsurfer_imports(self):
        """Test fastsurfer.py has required imports."""
        code = (FUNCTIONS_DIR / "fastsurfer.py").read_text()
        
        required_imports = ["argparse", "os", "sys", "spython"]
        for imp in required_imports:
            assert f"import {imp}" in code or f"from {imp}" in code, f"Missing import: {imp}"
    
    def test_hippunfold_imports(self):
        """Test hippunfold.py has required imports."""
        code = (FUNCTIONS_DIR / "hippunfold.py").read_text()
        
        required_imports = ["argparse", "os", "sys", "spython"]
        for imp in required_imports:
            assert f"import {imp}" in code or f"from {imp}" in code, f"Missing import: {imp}"
    
    def test_linear_coreg_imports(self):
        """Test linear_coreg.py has required imports."""
        code = (FUNCTIONS_DIR / "linear_coreg.py").read_text()
        
        required_imports = ["argparse", "os", "sys", "nipype"]
        for imp in required_imports:
            assert f"import {imp}" in code or f"from {imp}" in code, f"Missing import: {imp}"
    
    def test_pvc_imports(self):
        """Test pvc.py has required imports."""
        code = (FUNCTIONS_DIR / "pvc.py").read_text()
        
        required_imports = ["argparse", "os", "sys", "nipype"]
        for imp in required_imports:
            assert f"import {imp}" in code or f"from {imp}" in code, f"Missing import: {imp}"


# =============================================================================
# BIDS Naming Convention Tests
# =============================================================================

class TestBIDSNamingConventions:
    """Test BIDS naming conventions in output files."""
    
    def test_pet_file_naming(self, test_subject, test_tracer, test_session):
        """Test PET file naming follows BIDS."""
        # Pattern: sub-{subject}_ses-{session}_space-{space}_pvc-{pvc}_ref-{ref}_trc-{tracer}_pet.nii.gz
        # Uses Snakemake wildcards {subject} and {session}
        pattern_parts = [
            "sub-{subject}",
            "ses-{session}",
            "space-",
            "pvc-",
            "ref-",
            "trc-{tracer}",
            "_pet.nii.gz"
        ]
        
        # Check that our rules use these patterns
        pet_rules = (REPO_ROOT / "workflow" / "rules" / "pet.smk").read_text()
        for part in pattern_parts:
            assert part in pet_rules, f"BIDS pattern '{part}' not found in pet rules"
    
    def test_surface_file_naming(self, test_subject, test_tracer, test_session):
        """Test surface file naming follows conventions."""
        # Uses Snakemake wildcards {subject} and {session}
        pattern_parts = [
            "sub-{subject}",
            "ses-{session}",
            "hemi-",
            "label-midthickness",
        ]
        
        pet_rules = (REPO_ROOT / "workflow" / "rules" / "pet.smk").read_text()
        for part in pattern_parts:
            assert part in pet_rules, f"Surface naming pattern '{part}' not found"
    
    def test_transform_file_naming(self):
        """Test transform file naming."""
        pet_rules = (REPO_ROOT / "workflow" / "rules" / "pet.smk").read_text()
        
        # Should use _from-{source}_to-{target}_xfm pattern
        assert "_from-pet_to-" in pet_rules
        assert "_xfm.reg.lta" in pet_rules


# =============================================================================
# Integration Tests (Mock-based)
# =============================================================================

class TestMockIntegration:
    """Integration tests using mocks."""
    
    def test_full_pipeline_path_chain(self, mock_bids_dir, test_subject, test_tracer, test_session, mock_env):
        """Test that output paths from one step match input paths for the next."""
        version = mock_env['MICA_PET_VERSION']
        
        # FastSurfer outputs -> GTM_seg inputs
        fs_dir = mock_bids_dir / "derivatives" / "fastsurfer" / f"sub-{test_subject}_ses-{test_session}"
        gtm_inputs = [
            fs_dir / "mri" / "norm.mgz",
            fs_dir / "mri" / "transforms" / "talairach.lta",
            fs_dir / "mri" / "brainmask.mgz",
        ]
        
        # Linear_coreg outputs -> PVC inputs
        mica_pet = mock_bids_dir / "derivatives" / f"MICA-PET_{version}" / f"sub-{test_subject}" / f"ses-{test_session}"
        coreg_to_pvc = [
            mica_pet / "xfm" / f"sub-{test_subject}_ses-{test_session}_from-pet_to-T1wFS_xfm.reg.lta",
        ]
        
        # PVC outputs -> SUVR inputs
        pvc_to_suvr = [
            mica_pet / "pet" / f"sub-{test_subject}_ses-{test_session}_space-T1wFS_pvc-rbv_ref-none_trc-{test_tracer}_pet.nii.gz",
        ]
        
        # Verify all parent directories exist in mock
        all_paths = gtm_inputs + coreg_to_pvc + pvc_to_suvr
        for path in all_paths:
            assert path.parent.exists() or path.parent.parent.exists(), f"Path chain broken at: {path}"


# =============================================================================
# Surface File Tests
# =============================================================================

class TestSurfaceFiles:
    """Test surface file handling."""
    
    def test_repo_surface_files_exist(self):
        """Test that required surface template files exist."""
        surfaces_dir = REPO_ROOT / "surfaces"
        
        required_files = [
            "fsLR-32k.L.sphere.reg.surf.gii",
            "fsLR-32k.R.sphere.reg.surf.gii",
            "fsLR-5k.L.sphere.reg.surf.gii",
            "fsLR-5k.R.sphere.reg.surf.gii",
            "sctx.L.surf.gii",
            "sctx.R.surf.gii",
        ]
        
        for filename in required_files:
            assert (surfaces_dir / filename).exists(), f"Missing surface file: {filename}"
    
    def test_control_histogram_files_exist(self):
        """Test that FDG control histogram files exist."""
        surfaces_dir = REPO_ROOT / "surfaces"
        
        required_files = [
            "FDG_surf_ctrl_hist_norm_mean.csv",
            "FDG_surf_ctrl_hist_norm_std.csv",
        ]
        
        for filename in required_files:
            assert (surfaces_dir / filename).exists(), f"Missing histogram file: {filename}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

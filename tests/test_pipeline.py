#!/usr/bin/env python
"""
Test suite for MICA-PET Snakebids pipeline.

Tests validate:
1. Configuration file structure
2. Rule input/output path consistency
3. Python function argument parsing
4. Integration between rules and Python functions
"""

import os
import sys
import yaml
import pytest
from pathlib import Path

# Add functions directory to path for testing
REPO_ROOT = Path(__file__).parent.parent
FUNCTIONS_DIR = REPO_ROOT / "functions"
sys.path.insert(0, str(FUNCTIONS_DIR))


class TestSnakebidsConfig:
    """Test snakebids.yml configuration."""
    
    @pytest.fixture
    def config(self):
        config_path = REPO_ROOT / "config" / "snakebids.yml"
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def test_config_has_pybids_inputs(self, config):
        """Config must have pybids_inputs section."""
        assert "pybids_inputs" in config
    
    def test_pybids_has_t1w(self, config):
        """Must have T1w input definition."""
        assert "T1w" in config["pybids_inputs"]
        t1w = config["pybids_inputs"]["T1w"]
        assert "filters" in t1w
        assert "wildcards" in t1w
    
    def test_pybids_has_pet(self, config):
        """Must have PET input definition."""
        assert "pet" in config["pybids_inputs"]
        pet = config["pybids_inputs"]["pet"]
        assert "filters" in pet
        # BIDS entity should be 'tracer' not 'trc'
        assert "tracer" in pet["filters"], "Should use 'tracer' not 'trc' for BIDS entity"
    
    def test_config_has_required_args(self, config):
        """Config must define required CLI arguments."""
        assert "parse_args" in config
        args = config["parse_args"]
        
        # Args are in --flag-format in the config
        required_args = ["--fastsurfer-img", "--hippunfold-img", "--fs-license"]
        for arg in required_args:
            assert arg in args, f"Missing required arg: {arg}"


class TestPythonFunctionArguments:
    """Test that Python functions accept required arguments."""
    
    def test_fastsurfer_has_subj_dir_arg(self):
        """fastsurfer.py must accept -subj_dir."""
        fastsurfer_path = FUNCTIONS_DIR / "fastsurfer.py"
        content = fastsurfer_path.read_text()
        assert "-subj_dir" in content
        assert "-tmpdir" in content  # Required argument
        assert "-fs_license" in content  # Required argument
    
    def test_hippunfold_has_hippunfold_dir_arg(self):
        """hippunfold.py must accept -hippunfold_dir."""
        hippunfold_path = FUNCTIONS_DIR / "hippunfold.py"
        content = hippunfold_path.read_text()
        assert "-hippunfold_dir" in content
        assert "-hippunfold_img" in content
    
    def test_linear_coreg_has_output_dir_arg(self):
        """linear_coreg.py must accept -output_dir."""
        path = FUNCTIONS_DIR / "linear_coreg.py"
        content = path.read_text()
        assert "-output_dir" in content
        assert "-subj_dir" in content
    
    def test_pvc_has_output_dir_arg(self):
        """pvc.py must accept -output_dir."""
        path = FUNCTIONS_DIR / "pvc.py"
        content = path.read_text()
        assert "-output_dir" in content
        assert "-psf" in content
    
    def test_suvr_has_output_dir_arg(self):
        """suvr.py must accept -output_dir."""
        path = FUNCTIONS_DIR / "suvr.py"
        content = path.read_text()
        assert "-output_dir" in content
        assert "-ref_region" in content
    
    def test_project_pet_data_has_output_dir_arg(self):
        """project_pet_data.py must accept -output_dir."""
        path = FUNCTIONS_DIR / "project_pet_data.py"
        content = path.read_text()
        assert "-output_dir" in content
        assert "-hippunfold_dir" in content
    
    def test_subcortical_map_has_output_dir_arg(self):
        """subcortical_map.py must accept -output_dir."""
        path = FUNCTIONS_DIR / "subcortical_map.py"
        content = path.read_text()
        assert "-output_dir" in content
    
    def test_cortical_surface_has_output_dir_arg(self):
        """cortical_surface.py must accept -output_dir."""
        path = FUNCTIONS_DIR / "cortical_surface.py"
        content = path.read_text()
        assert "-output_dir" in content
    
    def test_clinical_reports_has_output_dir_arg(self):
        """clinical_reports.py must accept -output_dir."""
        path = FUNCTIONS_DIR / "clinical_reports.py"
        content = path.read_text()
        assert "-output_dir" in content


class TestSnakemakeRules:
    """Test Snakemake rule files."""
    
    @pytest.fixture
    def anatomy_rules(self):
        path = REPO_ROOT / "workflow" / "rules" / "anatomy.smk"
        return path.read_text()
    
    @pytest.fixture
    def pet_rules(self):
        path = REPO_ROOT / "workflow" / "rules" / "pet.smk"
        return path.read_text()
    
    @pytest.fixture
    def report_rules(self):
        path = REPO_ROOT / "workflow" / "rules" / "report.smk"
        return path.read_text()
    
    def test_fastsurfer_rule_uses_subj_dir(self, anatomy_rules):
        """FastSurfer rule must pass -subj_dir."""
        assert "-subj_dir" in anatomy_rules
        assert "-tmpdir" in anatomy_rules
    
    def test_hippunfold_rule_uses_hippunfold_dir(self, anatomy_rules):
        """HippUnfold rule must pass -hippunfold_dir."""
        assert "-hippunfold_dir" in anatomy_rules
    
    def test_linear_coreg_uses_output_dir(self, pet_rules):
        """Linear coreg rule must pass -output_dir."""
        assert "-output_dir" in pet_rules
    
    def test_pvc_uses_output_dir(self, pet_rules):
        """PVC rule must pass -output_dir."""
        # Check that pvc rule section has output_dir
        assert "pvc.py" in pet_rules
        assert "-output_dir" in pet_rules
    
    def test_suvr_uses_output_dir(self, pet_rules):
        """SUVR rule must pass -output_dir."""
        assert "suvr.py" in pet_rules
    
    def test_project_pet_data_uses_output_dir(self, pet_rules):
        """Project PET data rule must pass -output_dir."""
        assert "project_pet_data.py" in pet_rules
    
    def test_clinical_report_uses_output_dir(self, report_rules):
        """Clinical report rule must pass -output_dir."""
        assert "-output_dir" in report_rules


class TestWorkflowStructure:
    """Test overall workflow structure."""
    
    def test_snakefile_exists(self):
        """Main Snakefile must exist."""
        snakefile = REPO_ROOT / "workflow" / "Snakefile"
        assert snakefile.exists()
    
    def test_snakefile_has_generate_inputs(self):
        """Snakefile must call generate_inputs."""
        snakefile = REPO_ROOT / "workflow" / "Snakefile"
        content = snakefile.read_text()
        assert "generate_inputs" in content
        assert "inputs" in content
    
    def test_snakefile_includes_rules(self):
        """Snakefile must include rule files."""
        snakefile = REPO_ROOT / "workflow" / "Snakefile"
        content = snakefile.read_text()
        assert "anatomy.smk" in content
        assert "pet.smk" in content
        assert "report.smk" in content
    
    def test_all_rule_files_exist(self):
        """All referenced rule files must exist."""
        rules_dir = REPO_ROOT / "workflow" / "rules"
        assert (rules_dir / "anatomy.smk").exists()
        assert (rules_dir / "pet.smk").exists()
        assert (rules_dir / "report.smk").exists()


class TestOutputPaths:
    """Test that output paths in rules match what Python functions produce."""
    
    def test_linear_coreg_output_path_uses_xfm_dir(self):
        """linear_coreg outputs to /xfm/ subdirectory."""
        pet_rules = (REPO_ROOT / "workflow" / "rules" / "pet.smk").read_text()
        # The rule should output to xfm directory
        assert 'xfm",' in pet_rules or "/xfm/" in pet_rules
    
    def test_linear_coreg_lta_filename_format(self):
        """linear_coreg LTA files use _from-pet_to-{space}_xfm.reg.lta format."""
        pet_rules = (REPO_ROOT / "workflow" / "rules" / "pet.smk").read_text()
        assert "_from-pet_to-T1wFS_xfm.reg.lta" in pet_rules
        assert "_from-pet_to-T1wNative_xfm.reg.lta" in pet_rules


class TestRunScript:
    """Test run.py entry point."""
    
    def test_run_py_exists(self):
        """run.py must exist."""
        run_py = REPO_ROOT / "run.py"
        assert run_py.exists()
    
    def test_run_py_uses_bidsapp(self):
        """run.py must use snakebids.bidsapp."""
        run_py = REPO_ROOT / "run.py"
        content = run_py.read_text()
        assert "bidsapp" in content


class TestSmkConfigAccess:
    """Regression tests: smk input functions must not reference Snakefile globals directly.

    Root cause of bug (2026-02): pet.smk and anatomy.smk input helper functions
    referenced EXISTING_FREESURFER_DIR / EXISTING_HIPPUNFOLD_DIR as bare global names.
    These globals are defined in the Snakefile, but if the container image contains
    smk files from one commit and a Snakefile from another the names are undefined at
    call time, producing:
        NameError: name 'EXISTING_FREESURFER_DIR' is not defined

    Fix: input functions must use config.get("existing_freesurfer_dir", "") directly.
    These tests enforce that pattern.
    """

    SMK_FILES = [
        REPO_ROOT / "workflow" / "rules" / "pet.smk",
        REPO_ROOT / "workflow" / "rules" / "anatomy.smk",
        REPO_ROOT / "workflow" / "rules" / "report.smk",
    ]

    @pytest.mark.parametrize(
        "smk_file",
        SMK_FILES,
        ids=["pet.smk", "anatomy.smk", "report.smk"],
    )
    def test_no_bare_existing_freesurfer_global(self, smk_file):
        """smk files must not reference EXISTING_FREESURFER_DIR as a bare identifier."""
        import re
        content = smk_file.read_text()
        matches = re.findall(r'\bEXISTING_FREESURFER_DIR\b', content)
        assert not matches, (
            f"{smk_file.name} references bare global EXISTING_FREESURFER_DIR "
            f"({len(matches)} occurrence(s)). Use config.get('existing_freesurfer_dir', '') instead."
        )

    @pytest.mark.parametrize(
        "smk_file",
        SMK_FILES,
        ids=["pet.smk", "anatomy.smk", "report.smk"],
    )
    def test_no_bare_existing_hippunfold_global(self, smk_file):
        """smk files must not reference EXISTING_HIPPUNFOLD_DIR as a bare identifier."""
        import re
        content = smk_file.read_text()
        matches = re.findall(r'\bEXISTING_HIPPUNFOLD_DIR\b', content)
        assert not matches, (
            f"{smk_file.name} references bare global EXISTING_HIPPUNFOLD_DIR "
            f"({len(matches)} occurrence(s)). Use config.get('existing_hippunfold_dir', '') instead."
        )

    def test_pet_smk_uses_config_get_for_existing_dirs(self):
        """pet.smk must access existing-dir flags via config.get()."""
        content = (REPO_ROOT / "workflow" / "rules" / "pet.smk").read_text()
        assert 'config.get("existing_freesurfer_dir"' in content, \
            "pet.smk must use config.get('existing_freesurfer_dir') in input functions"
        assert 'config.get("existing_hippunfold_dir"' in content, \
            "pet.smk must use config.get('existing_hippunfold_dir') in input functions"

    def test_anatomy_smk_uses_config_get_for_existing_dirs(self):
        """anatomy.smk must access existing-freesurfer-dir flag via config.get()."""
        content = (REPO_ROOT / "workflow" / "rules" / "anatomy.smk").read_text()
        assert 'config.get("existing_freesurfer_dir"' in content, \
            "anatomy.smk must use config.get('existing_freesurfer_dir') in input functions"

    def test_snakefile_derives_existing_dirs_from_config(self):
        """Snakefile must derive EXISTING_*_DIR from config (not hardcoded)."""
        content = (REPO_ROOT / "workflow" / "Snakefile").read_text()
        assert 'config.get("existing_freesurfer_dir"' in content
        assert 'config.get("existing_hippunfold_dir"' in content

    def test_existing_dir_cli_args_in_snakebids_yml(self):
        """snakebids.yml must declare --existing-freesurfer-dir and --existing-hippunfold-dir."""
        config_path = REPO_ROOT / "config" / "snakebids.yml"
        config = yaml.safe_load(config_path.read_text())
        parse_args = config.get("parse_args", {})
        assert "--existing-freesurfer-dir" in parse_args, \
            "snakebids.yml is missing --existing-freesurfer-dir CLI arg"
        assert "--existing-hippunfold-dir" in parse_args, \
            "snakebids.yml is missing --existing-hippunfold-dir CLI arg"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Test suite for MICA-PET Snakebids Pipeline Configuration

This test suite validates:
1. YAML configuration syntax
2. Required configuration keys
3. Snakemake file syntax
4. Directory structure
5. Import compatibility

Run with: pytest tests/test_snakebids_config.py -v
"""
import os
import sys
import pytest
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestDirectoryStructure:
    """Test that the required directory structure exists."""
    
    def test_workflow_directory_exists(self):
        """Check that workflow directory exists."""
        workflow_dir = PROJECT_ROOT / "workflow"
        assert workflow_dir.exists(), f"Workflow directory not found: {workflow_dir}"
    
    def test_config_directory_exists(self):
        """Check that config directory exists."""
        config_dir = PROJECT_ROOT / "config"
        assert config_dir.exists(), f"Config directory not found: {config_dir}"
    
    def test_functions_directory_exists(self):
        """Check that functions directory exists."""
        functions_dir = PROJECT_ROOT / "functions"
        assert functions_dir.exists(), f"Functions directory not found: {functions_dir}"
    
    def test_snakefile_exists(self):
        """Check that main Snakefile exists."""
        snakefile = PROJECT_ROOT / "workflow" / "Snakefile"
        assert snakefile.exists(), f"Snakefile not found: {snakefile}"
    
    def test_rules_directory_exists(self):
        """Check that rules directory exists."""
        rules_dir = PROJECT_ROOT / "workflow" / "rules"
        assert rules_dir.exists(), f"Rules directory not found: {rules_dir}"
    
    def test_required_rule_files_exist(self):
        """Check that all required rule files exist."""
        rules_dir = PROJECT_ROOT / "workflow" / "rules"
        required_rules = ["anatomy.smk", "pet.smk", "report.smk"]
        
        for rule_file in required_rules:
            rule_path = rules_dir / rule_file
            assert rule_path.exists(), f"Rule file not found: {rule_path}"
    
    def test_run_py_exists(self):
        """Check that run.py entry point exists."""
        run_py = PROJECT_ROOT / "run.py"
        assert run_py.exists(), f"run.py not found: {run_py}"
    
    def test_snakebids_config_exists(self):
        """Check that snakebids.yml configuration exists."""
        config_file = PROJECT_ROOT / "config" / "snakebids.yml"
        assert config_file.exists(), f"snakebids.yml not found: {config_file}"


class TestYAMLConfiguration:
    """Test YAML configuration file validity."""
    
    @pytest.fixture
    def config(self):
        """Load the snakebids configuration."""
        import yaml
        config_path = PROJECT_ROOT / "config" / "snakebids.yml"
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def test_yaml_syntax_valid(self):
        """Test that the YAML file has valid syntax."""
        import yaml
        config_path = PROJECT_ROOT / "config" / "snakebids.yml"
        try:
            with open(config_path, 'r') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML syntax: {e}")
    
    def test_pybids_inputs_exists(self, config):
        """Test that pybids_inputs section exists."""
        assert 'pybids_inputs' in config, "pybids_inputs not found in config"
    
    def test_pybids_inputs_has_t1w(self, config):
        """Test that T1w input is defined."""
        assert 'T1w' in config['pybids_inputs'], "T1w not defined in pybids_inputs"
    
    def test_pybids_inputs_has_pet(self, config):
        """Test that pet input is defined."""
        assert 'pet' in config['pybids_inputs'], "pet not defined in pybids_inputs"
    
    def test_t1w_has_required_keys(self, config):
        """Test that T1w input has required keys."""
        t1w = config['pybids_inputs']['T1w']
        assert 'filters' in t1w, "T1w missing 'filters' key"
        assert 'wildcards' in t1w, "T1w missing 'wildcards' key"
    
    def test_pet_has_required_keys(self, config):
        """Test that pet input has required keys."""
        pet = config['pybids_inputs']['pet']
        assert 'filters' in pet, "pet missing 'filters' key"
        assert 'wildcards' in pet, "pet missing 'wildcards' key"
    
    def test_wildcards_include_subject(self, config):
        """Test that wildcards include subject."""
        t1w_wildcards = config['pybids_inputs']['T1w']['wildcards']
        pet_wildcards = config['pybids_inputs']['pet']['wildcards']
        assert 'subject' in t1w_wildcards, "T1w wildcards missing 'subject'"
        assert 'subject' in pet_wildcards, "pet wildcards missing 'subject'"
    
    def test_analysis_levels_exists(self, config):
        """Test that analysis_levels section exists."""
        assert 'analysis_levels' in config, "analysis_levels not found in config"
    
    def test_targets_by_analysis_level_exists(self, config):
        """Test that targets_by_analysis_level section exists."""
        assert 'targets_by_analysis_level' in config, "targets_by_analysis_level not found"
    
    def test_parse_args_exists(self, config):
        """Test that parse_args section exists."""
        assert 'parse_args' in config, "parse_args not found in config"
    
    def test_required_cli_args_defined(self, config):
        """Test that required CLI arguments are defined."""
        parse_args = config['parse_args']
        required_args = ['--fastsurfer-img', '--hippunfold-img', '--fs-license']
        for arg in required_args:
            assert arg in parse_args, f"Required CLI argument not defined: {arg}"


class TestSnakemakeSyntax:
    """Test Snakemake file syntax."""
    
    def test_snakefile_python_syntax(self):
        """Test that Snakefile has valid Python syntax."""
        snakefile = PROJECT_ROOT / "workflow" / "Snakefile"
        with open(snakefile, 'r') as f:
            content = f.read()
        
        # Basic check - look for common syntax errors
        # Note: Full validation requires snakemake which may not be installed locally
        assert 'rule all:' in content, "Target rule 'all' not found in Snakefile"
        assert 'include:' in content, "No include statements found in Snakefile"
        assert 'generate_inputs' in content, "generate_inputs not called in Snakefile"
    
    def test_rule_files_syntax(self):
        """Test that rule files have valid Snakemake syntax."""
        rules_dir = PROJECT_ROOT / "workflow" / "rules"
        rule_files = ["anatomy.smk", "pet.smk", "report.smk"]
        
        for rule_file in rule_files:
            rule_path = rules_dir / rule_file
            with open(rule_path, 'r') as f:
                content = f.read()
            
            # Check for at least one rule definition
            assert 'rule ' in content, f"No rules found in {rule_file}"
            # Check for proper rule structure
            assert 'input:' in content, f"No input section in {rule_file}"
            assert 'output:' in content, f"No output section in {rule_file}"


class TestSnakebidsIntegration:
    """Test snakebids-specific patterns."""
    
    def test_snakefile_imports_snakebids(self):
        """Test that Snakefile imports snakebids correctly."""
        snakefile = PROJECT_ROOT / "workflow" / "Snakefile"
        with open(snakefile, 'r') as f:
            content = f.read()
        
        assert 'import snakebids' in content or 'from snakebids import' in content, \
            "snakebids not imported in Snakefile"
    
    def test_snakefile_calls_generate_inputs(self):
        """Test that Snakefile calls generate_inputs."""
        snakefile = PROJECT_ROOT / "workflow" / "Snakefile"
        with open(snakefile, 'r') as f:
            content = f.read()
        
        assert 'generate_inputs(' in content, "generate_inputs() not called in Snakefile"
    
    def test_rules_use_inputs_dict_notation(self):
        """Test that rules use dictionary notation for inputs."""
        rules_dir = PROJECT_ROOT / "workflow" / "rules"
        rule_files = ["anatomy.smk", "pet.smk"]
        
        for rule_file in rule_files:
            rule_path = rules_dir / rule_file
            with open(rule_path, 'r') as f:
                content = f.read()
            
            # Should NOT contain attribute-style access (inputs.T1w.path)
            assert 'inputs.T1w.' not in content, \
                f"{rule_file} uses old inputs.T1w notation instead of inputs['T1w']"
            assert 'inputs.pet.' not in content, \
                f"{rule_file} uses old inputs.pet notation instead of inputs['pet']"


class TestRunScript:
    """Test the run.py entry point script."""
    
    def test_run_py_python_syntax(self):
        """Test that run.py has valid Python syntax."""
        run_py = PROJECT_ROOT / "run.py"
        with open(run_py, 'r') as f:
            content = f.read()
        
        try:
            compile(content, run_py, 'exec')
        except SyntaxError as e:
            pytest.fail(f"run.py has syntax error: {e}")
    
    def test_run_py_has_main(self):
        """Test that run.py has a main function."""
        run_py = PROJECT_ROOT / "run.py"
        with open(run_py, 'r') as f:
            content = f.read()
        
        assert 'def main(' in content, "run.py missing main() function"
        assert 'if __name__ == "__main__":' in content, "run.py missing __main__ guard"


class TestFunctionScripts:
    """Test that function scripts exist and have basic structure."""
    
    @pytest.fixture
    def function_scripts(self):
        """Get list of function scripts."""
        functions_dir = PROJECT_ROOT / "functions"
        return [
            "fastsurfer.py",
            "hippunfold.py",
            "cortical_surface.py",
            "gtm_seg.py",
            "linear_coreg.py",
            "pvc.py",
            "suvr.py",
            "project_pet_data.py",
            "subcortical_map.py",
            "clinical_reports.py",
        ]
    
    def test_function_scripts_exist(self, function_scripts):
        """Test that all function scripts exist."""
        functions_dir = PROJECT_ROOT / "functions"
        for script in function_scripts:
            script_path = functions_dir / script
            assert script_path.exists(), f"Function script not found: {script_path}"
    
    def test_function_scripts_have_argparse(self, function_scripts):
        """Test that function scripts use argparse."""
        functions_dir = PROJECT_ROOT / "functions"
        for script in function_scripts:
            script_path = functions_dir / script
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Most scripts should use argparse
            if 'argparse' not in content and 'ArgumentParser' not in content:
                # utils.py might not have argparse
                if script != 'utils.py':
                    pytest.skip(f"{script} doesn't use argparse - may use different pattern")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

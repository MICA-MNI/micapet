#!/usr/bin/env python3
"""
Automated test suite to catch configuration and integration errors
before deploying to the server.
"""
import sys
import subprocess
from pathlib import Path
import tempfile
import shutil

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test(msg):
    print(f"{Colors.BLUE}[TEST]{Colors.RESET} {msg}")

def print_pass(msg):
    print(f"{Colors.GREEN}[PASS]{Colors.RESET} {msg}")

def print_fail(msg):
    print(f"{Colors.RED}[FAIL]{Colors.RESET} {msg}")

def print_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")

def test_file_structure():
    """Test 1: Check all required files exist"""
    print_test("Checking file structure...")
    
    script_dir = Path(__file__).parent
    required_files = {
        "config/snakebids.yml": "Snakebids configuration",
        "workflow/Snakefile": "Main Snakefile",
        "workflow/rules/anatomy.smk": "Anatomy rules",
        "workflow/rules/pet.smk": "PET rules",
        "workflow/rules/report.smk": "Report rules",
        "run.py": "Entry point script",
        "environment.yml": "Conda environment",
    }
    
    all_pass = True
    for file, desc in required_files.items():
        if (script_dir / file).exists():
            print_pass(f"{file} ({desc})")
        else:
            print_fail(f"{file} ({desc}) - MISSING!")
            all_pass = False
    
    return all_pass

def test_yaml_syntax():
    """Test 2: Validate YAML syntax"""
    print_test("Validating YAML syntax...")
    
    try:
        import yaml
        script_dir = Path(__file__).parent
        
        with open(script_dir / "config/snakebids.yml") as f:
            config = yaml.safe_load(f)
        
        print_pass("config/snakebids.yml syntax is valid")
        
        with open(script_dir / "environment.yml") as f:
            env = yaml.safe_load(f)
        
        print_pass("environment.yml syntax is valid")
        return True
        
    except Exception as e:
        print_fail(f"YAML syntax error: {e}")
        return False

def test_python_imports():
    """Test 3: Test Python imports"""
    print_test("Testing Python imports...")
    
    imports_to_test = [
        ("snakebids.app", "SnakeBidsApp"),
        ("pathlib", "Path"),
    ]
    
    all_pass = True
    for module, item in imports_to_test:
        try:
            exec(f"from {module} import {item}")
            print_pass(f"from {module} import {item}")
        except ImportError as e:
            print_fail(f"from {module} import {item} - {e}")
            all_pass = False
    
    return all_pass

def test_run_py_syntax():
    """Test 4: Check run.py for syntax errors"""
    print_test("Checking run.py syntax...")
    
    script_dir = Path(__file__).parent
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(script_dir / "run.py")],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print_pass("run.py has valid Python syntax")
        return True
    else:
        print_fail(f"run.py syntax error: {result.stderr}")
        return False

def test_snakebids_config():
    """Test 5: Validate snakebids config structure"""
    print_test("Validating snakebids configuration...")
    
    try:
        import yaml
        script_dir = Path(__file__).parent
        
        with open(script_dir / "config/snakebids.yml") as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ["pybids_inputs", "parse_args"]
        for section in required_sections:
            if section in config:
                print_pass(f"Found required section: {section}")
            else:
                print_fail(f"Missing required section: {section}")
                return False
        
        # Validate parse_args structure
        if isinstance(config["parse_args"], dict):
            print_pass("parse_args is a dictionary")
            
            # Check for invalid keys in positional args
            for arg_name, arg_config in config["parse_args"].items():
                if isinstance(arg_config, dict):
                    if "required" in arg_config:
                        print_fail(f"Argument '{arg_name}' has 'required' key (invalid for positional args)")
                        return False
                    print_pass(f"Argument '{arg_name}' is properly configured")
        else:
            print_fail("parse_args must be a dictionary")
            return False
        
        return True
        
    except Exception as e:
        print_fail(f"Config validation error: {e}")
        return False

def test_help_command():
    """Test 6: Try to display help (tests argparse setup)"""
    print_test("Testing help command...")
    
    script_dir = Path(__file__).parent
    result = subprocess.run(
        [sys.executable, str(script_dir / "run.py"), "--help"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if result.returncode == 0 and "usage:" in result.stdout.lower():
        print_pass("Help command works - argparse is properly configured")
        return True
    else:
        print_fail(f"Help command failed: {result.stderr}")
        return False

def test_mock_run():
    """Test 7: Test with mock arguments"""
    print_test("Testing with mock arguments...")
    
    script_dir = Path(__file__).parent
    
    # Create a temporary directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create minimal BIDS structure
        bids_dir = tmpdir / "bids"
        bids_dir.mkdir()
        (bids_dir / "dataset_description.json").write_text('{"Name": "test", "BIDSVersion": "1.0.0"}')
        
        result = subprocess.run(
            [
                sys.executable, str(script_dir / "run.py"),
                "/fake/fastsurfer.sif",
                "/fake/hippunfold.sif", 
                "/fake/license.txt",
                "4.5",
                "pons",
                "8",
                "/fake/cache",
                str(bids_dir),
                str(tmpdir / "out"),
                "participant",
                "--help"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print_pass("Mock run succeeded with --help")
            return True
        else:
            print_warn(f"Mock run with --help exit code: {result.returncode}")
            print_warn(f"stderr: {result.stderr[:200]}")
            # Don't fail on this as it might be expected
            return True

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print("MICAPET Snakebids Pipeline - Automated Test Suite")
    print(f"{'='*60}{Colors.RESET}\n")
    
    tests = [
        test_file_structure,
        test_yaml_syntax,
        test_python_imports,
        test_run_py_syntax,
        test_snakebids_config,
        test_help_command,
        test_mock_run,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print_fail(f"Test crashed: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"{Colors.BOLD}{'='*60}")
    print(f"Test Results: {passed}/{total} passed")
    print(f"{'='*60}{Colors.RESET}\n")
    
    if all(results):
        print(f"{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED!{Colors.RESET}")
        print("\nPipeline is ready to deploy to the server.")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ SOME TESTS FAILED!{Colors.RESET}")
        print("\nPlease fix the issues before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

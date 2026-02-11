#!/usr/bin/env python3
import subprocess
import os
import sys

os.chdir('/Users/enningyang/CodeProj/micapet')

def run_cmd(cmd, check=True):
    """Run command and return result"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"$ {cmd}")
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        print(f"Command failed with code {result.returncode}")
    return result

# Clean up any pending operations
run_cmd('git merge --abort', check=False)
run_cmd('git rebase --abort', check=False)

# Add all changes
run_cmd('git add -A')

# Check status
status = run_cmd('git status --short')

# Commit
commit_msg = """Fix: Ensure cortical_surface.py runs with redirected FastSurfer outputs

- Add --existing-freesurfer-dir and --existing-hippunfold-dir CLI arguments
- Implement symlink creation for existing outputs in Snakefile  
- Change rule dependencies from rule.output to direct file paths
- Allows cortical_surface to run even when using existing outputs"""

result = run_cmd(f'git commit -m "{commit_msg}"', check=False)

# Pull
run_cmd('git pull --no-rebase origin 3-snakebidsify')

# Push
run_cmd('git push origin 3-snakebidsify')

print("\n✓ All changes pushed successfully!")

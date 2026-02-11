#!/bin/bash
cd /Users/enningyang/CodeProj/micapet

# Abort any in-progress operations
git merge --abort 2>/dev/null || true
git rebase --abort 2>/dev/null || true

# Add all changes
git add -A

# Commit
git commit -m "Fix: Ensure cortical_surface.py runs with redirected FastSurfer outputs

- Add --existing-freesurfer-dir and --existing-hippunfold-dir CLI arguments
- Implement symlink creation for existing outputs in Snakefile
- Change rule dependencies from rule.output to direct file paths
- Allows cortical_surface to run even when using existing outputs

Fixes issue where cortical_surface.py doesn't run when using redirected
outputs, causing failure at project_pet_data.py"

# Pull and merge
git pull --no-rebase origin 3-snakebidsify

# Push
git push origin 3-snakebidsify

echo "Done!"

<!-- Replace {issue_number} with the issue that will be closed after merging this PR -->
## Description
Fixes #{issue_number}: A few sentences describing the changes proposed in this pull request.

## Type of change
Please delete options accordingly to the description.

<!-- Write an `x` in all the boxes that apply -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] This change requires a documentation update


### Suggested Checklist
<!-- You do not need to complete all the items by the time you submit the pull request, but most likely the changes will only be merged if all the tasks are done. -->

<!-- Write an `x` in all the boxes that apply -->
- [ ] I have performed a self-review of my own code
- [ ] I have made corresponding changes to the documentation 
- [ ] My changes generate no new warnings 
- [ ] I have commented my code, particularly in hard-to-understand areas 
- [ ] I have read the CONTRIBUTING docs
- [ ] My code passes, following the style guidelines `pre-commit run -a` 
- [ ] My code is properly tested with `pytest -sv tests`
- [ ] This pull request is ready to be reviewed
- [ ] Make sure your branch is up-to-date with main branch. See below a general example if `rebase` is need.
```
git checkout main
git pull origin main
git checkout FEATURE_BRANCH 
git rebase main
#git status
#edit conflicting files with your editor
#git rebase --continue
#git add .
git push --force origin FEATURE_BRANCH
```

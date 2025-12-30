# Design: Remove duplicate docs/examples directory

## Approach
Simple directory removal with verification step.

## Implementation Steps

1. **Verify no external references**
   - Search docs/ for any links to `docs/examples/`
   - Check mkdocs.yml for references
   - Confirm CI/CD scripts don't reference location

2. **Remove directory**
   ```bash
   rm -rf docs/examples/
   ```

3. **Verify cleanup**
   ```bash
   # Confirm directory gone
   ls docs/examples/  # Should fail

   # Confirm root examples still exists
   ls examples/  # Should succeed

   # Test documentation build
   mkdocs build
   ```

## Migration Path
No migration needed - files are identical duplicates.

## Risk Mitigation
- **Pre-removal snapshot**: Commit state before removal
- **Validation**: Run `mkdocs build` to confirm no broken links
- **Revert plan**: If issues found, restore from git: `git checkout -- docs/examples/`

## Validation Checklist
- [ ] No references to `docs/examples/` in docs/
- [ ] No references to `docs/examples/` in mkdocs.yml
- [ ] Root `examples/` directory contains all needed files
- [ ] Documentation builds successfully after removal
- [ ] No broken links in generated documentation

## Expected Result
Single canonical examples location at `examples/` root level, following Python project conventions.

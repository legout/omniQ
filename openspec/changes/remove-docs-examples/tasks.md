## 1. Verification
- [x] Search docs/ for references to `docs/examples/`
- [x] Search mkdocs.yml for references to `docs/examples/`
- [x] Confirm root `examples/` has all needed files
- [x] Compare file contents to verify duplicates

## 2. Removal
- [x] Remove `docs/examples/` directory
- [x] Verify directory is removed (`ls docs/examples/` fails)
- [x] Verify root `examples/` still exists

## 3. Validation
- [x] Run `mkdocs build` to confirm no broken links
- [x] Check generated docs for missing example links
- [x] Verify example code can still be imported/run
- [x] Confirm README.md links to examples still work

## 4. Cleanup
- [x] Remove any residual `.pyc` files from `docs/examples/` (if any)
- [x] Remove from `.gitignore` if specifically listed
- [x] Update any internal documentation that might reference old path

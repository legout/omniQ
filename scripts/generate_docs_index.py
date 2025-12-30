#!/usr/bin/env python3
"""Generate docs/index.md from README.md to ensure README-as-index guarantee."""

import shutil
from pathlib import Path


def generate_docs_index():
    """Copy README.md to docs/index.md."""
    project_root = Path(__file__).parent.parent
    readme_path = project_root / "README.md"
    docs_index_path = project_root / "docs" / "index.md"

    shutil.copy(readme_path, docs_index_path)
    print(f"Generated {docs_index_path} from {readme_path}")


if __name__ == "__main__":
    generate_docs_index()

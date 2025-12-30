#!/usr/bin/env python3
"""Build script for MkDocs with README-as-index guarantee."""

import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
    """Run a shell command."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check)
    return result.returncode


def build_docs(strict=True):
    """Build the MkDocs site."""
    project_root = Path(__file__).parent.parent
    generate_script = project_root / "scripts" / "generate_docs_index.py"

    # Step 1: Generate docs/index.md from README.md
    print("\n=== Generating docs/index.md from README.md ===")
    run_command([sys.executable, str(generate_script)])

    # Step 2: Copy examples to docs directory for mkdocs to find
    print("\n=== Copying examples to docs directory ===")
    examples_src = project_root / "examples"
    examples_dst = project_root / "docs" / "examples"
    if examples_src.exists():
        if examples_dst.exists():
            shutil.rmtree(examples_dst)
        shutil.copytree(examples_src, examples_dst)
        print(f"Copied {examples_src} to {examples_dst}")

    # Step 3: Build MkDocs site
    print("\n=== Building MkDocs site ===")
    cmd = ["mkdocs", "build"]
    if strict:
        cmd.append("--strict")
    run_command(cmd)

    # Step 4: Clean up examples from docs directory
    print("\n=== Cleaning up examples from docs directory ===")
    if examples_dst.exists():
        shutil.rmtree(examples_dst)
        print(f"Removed {examples_dst}")

    print("\n=== Build complete ===")


def serve_docs():
    """Serve the MkDocs site for development."""
    project_root = Path(__file__).parent.parent
    generate_script = project_root / "scripts" / "generate_docs_index.py"

    # Generate docs/index.md before serving
    run_command([sys.executable, str(generate_script)])

    # Serve the site with examples directory
    print("\n=== Starting MkDocs dev server ===")
    run_command(["mkdocs", "serve", "--watch", "examples"])


def check_readme_index_consistency():
    """Check that docs/index.md matches README.md."""
    project_root = Path(__file__).parent.parent
    readme_path = project_root / "README.md"
    docs_index_path = project_root / "docs" / "index.md"

    readme_content = readme_path.read_text()
    docs_index_content = docs_index_path.read_text()

    if readme_content != docs_index_content:
        print("ERROR: docs/index.md does not match README.md!")
        print("Run: python scripts/generate_docs_index.py")
        return 1

    print("✓ docs/index.md matches README.md")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "build":
            build_docs(strict="--no-strict" not in sys.argv)
        elif command == "serve":
            serve_docs()
        elif command == "check":
            sys.exit(check_readme_index_consistency())
        else:
            print(f"Unknown command: {command}")
            print("Usage: python scripts/build_docs.py [build|serve|check]")
            sys.exit(1)
    else:
        build_docs()

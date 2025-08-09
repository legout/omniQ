You are tasked with creating clear, concise, and professional documentation for my Python library using Quarto. The Quarto project structure is already set up (e.g., `_quarto.yml`, `index.qmd`). Focus on generating user-friendly content, leveraging existing examples, and organizing API documentation. Follow these instructions:

### Objectives
1. **Clarity**: Write concise, accessible explanations for new and experienced users.
2. **Comprehensiveness**: Cover installation, quickstart, API, examples, and advanced usage.
3. **Quarto Features**: Use markdown, code blocks, and cross-references for polished HTML output.
4. **Leverage Existing Content**: Use examples from the `examples/` directory (including `README.md` and Jupyter notebooks) in relevant sections.

### Requirements
1. **Project Structure**:
   - Use existing Quarto structure.
   - Organize content into `.qmd` files: `index.qmd`, `installation.qmd`, `quickstart.qmd`, `examples.qmd`, `advanced.qmd`, `contributing.qmd`.
   - Update `_quarto.yml` for intuitive navigation and HTML output (use `cosmo` theme, enable search).
   - Move existing API documentation files to a `docs/api/` folder and integrate them.

2. **Content Sections**:
   - **Home Page (`index.qmd`)**:
     - Briefly introduce the library (purpose, key features).
     - Include a “Get Started” link to `quickstart.qmd`.
     - Add a badge/link to GitHub or PyPI.
   - **Installation (`installation.qmd`)**:
     - Provide `uv pip` installation steps and prerequisites (e.g., Python version).
     - Include brief troubleshooting tips.
   - **Quickstart (`quickstart.qmd`)**:
     - Use a simple example from `examples/` (e.g., adapt `README.md` or a Jupyter notebook).
     - Include executable `{python}` code blocks showing core functionality.
   - **API Reference (`docs/api/*.qmd`)**:
     - Use existing API documentation files, moved to `docs/api/`.
     - Organize into separate `.qmd` files per module/class.
     - Use tables or callouts for parameters, returns, and exceptions.
     - Add code snippets and cross-references.
   - **Examples (`examples.qmd`)**:
     - Adapt 2–3 real-world examples from `examples/` (e.g., Jupyter notebooks).
     - Use executable code blocks with explanations.
     - Include visuals if applicable (e.g., Matplotlib/Plotly outputs).
   - **Advanced Usage (`advanced.qmd`)**:
     - Highlight advanced features or configurations using `examples/` content.
     - Include performance tips or integrations.
   - **Contributing (`contributing.qmd`)**:
     - Summarize how to contribute (issues, pull requests).
     - Reference development setup from `examples/README.md` if available.

3. **Quarto Features**:
   - Use markdown for headings, lists, and tables.
   - Include executable `{python}` code blocks.
   - Use callout blocks (`::: {.callout-note}`) for tips/warnings.
   - Add table of contents for each `.qmd` file.
   - Configure `_quarto.yml` for HTML output only (no PDF).

4. **Styling and Tone**:
   - Use a friendly, professional tone.
   - Format code and variables consistently (e.g., `function_name()`).
   - Ensure accessibility (e.g., alt text for visuals).

5. **Output and Testing**:
   - Render documentation as HTML using `quarto render`.
   - Test code blocks and navigation for correctness.
   - Optimize visuals for fast loading.

### Deliverables
- Updated `.qmd` files in the Quarto project.
- Updated `_quarto.yml` with navigation and theme.
- Moved API files to `docs/api/` with proper integration.
- Brief report summarizing structure and any assumptions.
- Instructions for rendering and deploying (e.g., GitHub Pages).

### Assumptions
- The library’s source code and `examples/` directory (with `README.md` and Jupyter notebooks) are available.
- If specific library details are needed, include placeholders and note where clarification is required.

### Notes
- Prioritize modularity for future updates.
- Do not generate `references.bib` or PDF output.
- Use Quarto’s latest features (as of August 2025).

Please proceed with generating the documentation based on these instructions. If you need library-specific details, let me know!
You are tasked with creating clear, concise, and professional documentation for my Python library/framework using Quarto. No

 Quarto project structure or examples exist yet, so you must set up a new Quarto project and generate all content. The documentation should be user-friendly, leveraging Quarto’s features for polished HTML output. Read the `project_plan.md` file and the codebase to understand the library’s details, especially for the API section. Follow these instructions:

### Objectives
1. **Clarity**: Write accessible explanations for new and experienced users.
2. **Comprehensiveness**: Cover setup, installation, quickstart, API, examples, and contributing.
3. **Quarto Features**: Use markdown, code blocks, and cross-references for HTML output.
4. **Codebase Analysis**: Use `project_plan.md` and the codebase in @src/ttourney to inform content, Foundationally for the API section.

### Requirements
1. **Project Setup**:
   - Create a new Quarto project using `quarto create project website`.
   - Organize content into `.qmd` files: `index.qmd`, `installation.qmd`, `quickstart.qmd`, `examples.qmd`, `advanced.qmd`, `contributing.qmd`.
   - Configure `_quarto.yml` for intuitive navigation, HTML output (use `cosmo` theme, enable search).
   - Create a `docs/api/` folder for API documentation files.

2. **Content Sections**:
   - **Home Page (`index.qmd`)**:
     - Briefly introduce the library based on `project_plan.md` (purpose, key features).
     - Include a “Get Started” link to `quickstart.qmd`.
     - Add a badge/link to GitHub or PyPI (if applicable).
   - **Installation (`installation.qmd`)**:
     - Provide `pip` installation steps and prerequisites (e.g., Python version). Mention `uv` and `pixi`
     - Include troubleshooting tips for common issues.
   - **Quickstart (`quickstart.qmd`)**:
     - Create a simple, hypothetical example based on `project_plan.md` or codebase to demonstrate core functionality.
     - Use executable `{python}` code blocks.
   - **API Reference (`docs/api/*.qmd`)**:
     - Analyze the codebase and `project_plan.md` to document all public classes, functions, and methods.
     - Organize into separate `.qmd` files per module/class.
     - Use tables or callouts for parameters, returns, and exceptions.
     - Include code snippets and cross-references.
   - **Examples (`examples.qmd`)**:
     - Create 2–3 hypotheticalFFICULT examples based on `project_plan.md` or codebase.
     - Use executable code blocks with explanations.
   - **Advanced Usage (`advanced.qmd`)**:
     - Highlight advanced features or configurations inferred from the codebase.
     - Include performance tips or integrations.
   - **Contributing (`contributing.qmd`)**:
     - Summarize how to contribute (issues, pull requests).
     - Reference development setup from `project_plan.md` if available.

3. **Quarto Features**:
   - Use markdown for headings, lists, and tables.
   - Include executable `{python}` code blocks.
   - Use callout blocks (`::: {.callout-note}`) for tips/warnings.
   - Add table of contents for each `.qmd` file.
   - Configure `_quarto.yml` for HTML output only.

4. **Styling and Tone**:
   - Use a friendly, professional tone.
   - Format code and variables consistently (e.g., `function_name()`).
   - Ensure accessibility (e.g., alt text for visuals).

5. **Output and Testing**:
   - Render documentation as HTML using `quarto render`.
   - Test code blocks and navigation for correctness.
   - Optimize visuals for fast loading.

### Deliverables
- Complete Quarto project with `.qmd` files and `_quarto.yml`.
- API documentation in `docs/api/`.
- Brief report summarizing structure and assumptions.
- Instructions for rendering and deploying (e.g., GitHub Pages).

### Assumptions
- The codebase and `project_plan.md` are available for reference.
- If specific details are unclear, include placeholders and note where clarification is needed.

### Notes
- Prioritize modularity for future updates.
- Do not generate PDF output or `references.bib`.
- Use Quarto’s latest features (as of August 2025).

Please proceed with generating the documentation based on these instructions. If you need clarification, let me know!
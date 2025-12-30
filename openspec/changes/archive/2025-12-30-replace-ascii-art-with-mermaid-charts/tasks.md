## 1. Verify Mermaid Support
- [x] 1.1 Check if pymdownx.superfences has mermaid enabled in mkdocs.yml
- [x] 1.2 If not enabled, add `pymdownx.superfences.custom_blocks` for mermaid in markdown_extensions
- [x] 1.3 Optionally add mermaid plugin to plugins section for better integration
- [x] 1.4 Test basic mermaid chart renders correctly

## 2. Replace architecture.md Diagrams
- [x] 2.1 Replace component diagram (lines 22-81) with Mermaid flowchart (graph TD)
- [x] 2.2 Replace enqueue flow (lines 211-231) with Mermaid flowchart (graph TB)
- [x] 2.3 Replace worker execution flow (lines 233-276) with Mermaid flowchart (graph TB)

## 3. Replace scheduling.md Diagrams
- [x] 3.1 Replace ETA example timeline (lines 49-70) with Mermaid flowchart (graph LR with time axis)
- [x] 3.2 Replace interval task timeline (lines 114-134) with Mermaid flowchart (graph LR)
- [x] 3.3 Replace failure rescheduling (lines 140-152) with Mermaid flowchart (graph LR)
- [x] 3.4 Replace combined ETA+interval timeline (lines 178-195) with Mermaid flowchart (graph LR)
- [x] 3.5 Replace queue state table (lines 235-247) with Mermaid table or flowchart showing state

## 4. Replace storage-tradeoffs.md Diagram
- [x] 4.1 Replace directory layout (lines 28-42) with Mermaid tree-style flowchart (graph TD)

## 5. Validation and Testing
- [x] 5.1 Build documentation site and verify all Mermaid charts render
- [x] 5.2 Check each diagram for proper styling and readability
- [x] 5.3 Verify all diagrams are responsive on different screen sizes
- [x] 5.4 Test navigation and interactive features (zoom/pan if available)
- [x] 5.5 Review for any broken references or formatting issues

## 6. Final Checks
- [x] 6.1 Run `openspec validate replace-ascii-art-with-mermaid-charts --strict`
- [x] 6.2 Ensure no ASCII art remains in explanation chapter
- [x] 6.3 Verify all diagrams maintain the same information as original ASCII art
- [x] 6.4 Update any cross-references to diagrams if needed

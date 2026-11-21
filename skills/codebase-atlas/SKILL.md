---
name: codebase-atlas
description: Build, update, or review an interactive, source-linked atlas for any codebase. Use for architecture maps, onboarding, deployment and dependency diagrams, and end-to-end walkthroughs of applications, CLIs, libraries, data pipelines, and monorepos.
---

# Codebase Atlas

## Understand the project

1. Identify the project root and any available revision information. Decide which packages, entry points, and environments the atlas covers. In a monorepo, identify the relevant packages and shared boundaries first.
2. Read project instructions and entry points. Search source, manifests, build and startup commands, infrastructure definitions, and tests. Trace real calls, registrations, and asynchronous handoffs. Distinguish a configured dependency from an observed running component.
3. Find a representative journey with a trigger and an observable result. Verify what crosses each boundary, who owns each write or side effect, and what happens when a significant step fails. Use imports as leads when tracing execution.

## Author and review

- Lead with an architecture overview. Map services and external dependencies when the project deploys them. For a library, map its public API, packages and callers. For a CLI or pipeline, show its invocation, processing stages, inputs, and outputs.
- Add a short end-to-end journey and link its stages to detailed views with source anchors. Include alternate and failure paths where they affect behavior. Label connections with the actual action, data, or protocol. Explain what each step does and why it exists.
- Catalog the main source files, configuration, and definitions in scope. Use Python symbols or exact line anchors for any UTF-8 source. Record cross-language file dependencies only when a source line supports them.
- Add searchable documentation pages for concepts, commands, tables, and recovery procedures. Connect each section to the implementation or guide it explains, and link the relevant flow steps back to the sections.
- Save the editable JSON alongside the published atlas, normally under `docs/codebase-atlas/`. Use the [input format](references/spec.md) for layers and catalogs. Keep credentials and local environment files out of embedded source.
- Review the result against implementation and tests using the [independent reviewer](references/reviewer.md). Exercise the overview, main journey, drill-down, and source reader. Record what was checked, including any distinction between reading tests and running them.

## Build

Use Python 3.11+ with its standard library. Run the bundled tools from any directory by passing the source project and spec paths explicitly.

```sh
atlas_skill="/absolute/path/to/codebase-atlas"
project_root="/absolute/path/to/project"
atlas_dir="$project_root/docs/codebase-atlas"

python3 "$atlas_skill/scripts/review_atlas.py" --root "$project_root" \
  "$atlas_dir/flows.json" "$atlas_dir/files.json"
python3 "$atlas_skill/scripts/render_atlas.py" --root "$project_root" --web \
  --out "$atlas_dir" "$atlas_dir/flows.json" "$atlas_dir/files.json"
```

Pass one or more JSON files. The renderer writes SVG diagrams and, with `--web`, an HTML explorer with the referenced source embedded. Use `--project` to override the display name. For reviews, pass repeatable `--include` globs for catalog coverage and `--components` followed by the expected architecture IDs from the relevant configuration. Use the independent review to verify behavior and deployment claims.

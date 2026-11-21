# Atlas input format

Each spec file contains an array of views. Give each view a unique ID using lowercase letters, digits, and hyphens. The viewer uses `files` and `imports` for its built-in routes. Source paths are project-relative, using forward slashes. Pass file paths for file-level references, `path#PythonSymbol.method` for Python definitions, or `path#L42` for an exact line in any UTF-8 source file.

## Flow views

Use `id`, `title`, `subtitle`, `columns`, `lanes`, and `edges`. Set `columns` to a positive integer. A lane has a `label` and `nodes`. Each card has an `id`, `title`, and `detail`. Set `ref` to its source, `why` to its rationale, and `tone` to `entry`, `data`, `success`, or `failure` where useful. Put `null` in empty positions. Keep card text short enough to fit the SVG.

- `label` gives the view a short navigation title. `layer` groups nearby views in the sidebar, and `parent` adds a breadcrumb.
- `topology: true` draws curved connections and puts component roles on cards. Set `component` on a card to an expected architecture ID for the reviewer. That card must have a source reference.
- `startJourney` links to the main flow. Set `startLabel` to customize the link text. Put the overview first.
- `drill` on a card lists view IDs or `view/node` destinations.
- Edges use `["source", "target"]` or `["source", "target", "async", "Payload or action"]`. Use `"flow"` as the third value for a labeled synchronous edge.
- For a linear conversation, set `transcript` to a list of `{node, speaker, text}` objects. A message can set `"align": "end"`. Add `transcriptContext` to describe the example inputs or fixture.

## Reference views

Use `id`, `title`, `subtitle`, and `files`. A row has four values.

```json
[
  "src/report.ts",
  "Reads input and generates the report.",
  [["runReport", "L8"]],
  [["ReportOptions", "Controls filtering and output.", "#L3"]]
]
```

The third value lists entry points. Each can be a Python symbol, a line anchor such as `"L8"`, an empty string for the file itself, or a pair `[label, anchor]`. The fourth value lists definitions. A row is `[name, purpose]` for a Python definition, `[name, purpose, method]` for a Python class method, or `[name, purpose, "#L8"]` for an explicit anchor. Use empty arrays where appropriate.

Add `dependencies` to any reference view to describe verified static dependencies between cataloged files. For example, `["src/cli.ts", "src/report.ts", [4]]` points to the reference on line 4 of `src/cli.ts`. The HTML combines declared dependencies with direct Python imports it can resolve from project-relative module paths. The dependency graph is optional.

## Documentation pages

Add pages alongside flows and references when prose, commands, or tables help explain the project. Give each page an `id`, `title`, `subtitle`, and `sections`. Each section has an `id`, a `title`, and `blocks`.

```json
{
  "id": "runbook",
  "title": "Run the report tool",
  "subtitle": "Inputs and common checks",
  "sections": [{
    "id": "run-report",
    "title": "Generate a report",
    "blocks": [
      "Pass the input file as the first argument.",
      {"code": "node src/cli.mjs inputs.json"},
      {"headers": ["Result", "Meaning"], "rows": [["0", "The report was written."]]}
    ],
    "links": [
      {"label": "Trace report generation", "target": "report/parse-input"},
      {"label": "Open the CLI", "ref": "src/cli.mjs#L8"}
    ]
  }]
}
```

Use a string for a paragraph, `{"items": ["…"]}` for a list, `{"code": "…"}` for a code block, or an object with `headers` and `rows` for a table. Backticks mark inline code in text. A link takes one `ref` or one `target`. The latter can point to a view, `view/node`, or `page/section`. Flow `drill` entries can also point to documentation. Search indexes page and section text. Build with `--web` to include the documentation in the HTML.

## Publish and maintain

Use `--guide-url` for a guide linked from the viewer. Use `--source-base` for a hosted source tree at the same revision. For GitHub-compatible permalinks alongside the embedded source, supply `--revision-url` with an HTTPS URL ending in a full commit SHA. The renderer only adds those links for files whose local bytes match the supplied commit. Recheck explicit line anchors after source edits and regenerate the site.

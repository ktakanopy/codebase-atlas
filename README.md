# Codebase Atlas

Codebase Atlas is a reusable agent skill for building interactive documentation from source. Start with an architecture map, follow a representative journey, and open the exact code behind each step. Search covers the flows, source symbols, and documentation pages.

## Install in a Codex project

Clone this repository and copy the skill directory into the target project's `.agents/skills` directory.

```sh
git clone https://github.com/ktakanopy/codebase-atlas.git
mkdir -p /path/to/project/.agents/skills
cp -R codebase-atlas/skills/codebase-atlas /path/to/project/.agents/skills/
```

In Codex, ask “Use Codebase Atlas to map this project.” The skill inspects the project, writes editable JSON, checks source and navigation links, and builds the atlas.

## Build from existing specs

Use Python 3.11 or newer. From the project root, assuming the specs are in `docs/codebase-atlas`:

```sh
python3 .agents/skills/codebase-atlas/scripts/review_atlas.py \
  docs/codebase-atlas/flows.json docs/codebase-atlas/files.json
python3 .agents/skills/codebase-atlas/scripts/render_atlas.py --web \
  --out docs/codebase-atlas docs/codebase-atlas/flows.json docs/codebase-atlas/files.json
```

Open the generated `docs/codebase-atlas/index.html`. Pass a documentation spec as another input file to include concept pages and runbooks. Source text is embedded in the HTML, so choose source suitable for whoever will read the atlas.

[Skill instructions](skills/codebase-atlas/SKILL.md) · [Input format](skills/codebase-atlas/references/spec.md) · [Review guide](skills/codebase-atlas/references/reviewer.md)

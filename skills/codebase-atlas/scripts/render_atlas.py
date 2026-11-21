import argparse
import ast
import hashlib
import io
import json
import keyword
import os
import re
import subprocess
import textwrap
import tokenize
from collections import defaultdict
from html import escape
from importlib.util import resolve_name
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

from atlas_catalog import catalog_refs, file_card
from review_atlas import review


SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
INK = "#172e3b"
MUTED = "#466072"
PAPER = "#f5f8fa"
RULE = "#c8d7df"
LINK = "#13677e"
TONES = {
    "entry": ("#e5f3fc", "#397a9e"),
    "normal": ("#ffffff", RULE),
    "data": ("#e7f3f2", "#548887"),
    "success": ("#e7f3f2", "#548887"),
    "failure": ("#fff0eb", "#bd6959"),
}
FONT = "system-ui, -apple-system, sans-serif"
MONO = "ui-monospace, Menlo, monospace"
PYTHON_TOKEN_STYLES = {
    "COMMENT": "comment",
    "NUMBER": "number",
    "OP": "operator",
    "STRING": "string",
}


def element(parent, tag, content=None, **attributes):
    node = ET.Element(
        f"{{{SVG}}}{tag}",
        {key.replace("_", "-"): str(value) for key, value in attributes.items()},
    )
    node.text = content
    if parent is not None:
        parent.append(node)
    return node


def text(parent, content, x, y, *, size=16, color=INK, weight=400, family=FONT):
    element(parent, "text", content, x=x, y=y, fill=color, font_size=size,
            font_weight=weight, font_family=family)


def lines(content, width):
    return textwrap.wrap(content, width=width, break_long_words=False, break_on_hyphens=False)


def rectangle(parent, x, y, width, height, *, fill, stroke="none", rx=12, stroke_width=1):
    element(parent, "rect", x=x, y=y, width=width, height=height, rx=rx,
            fill=fill, stroke=stroke, stroke_width=stroke_width)


class SourceLinks:
    def __init__(self, root, output, source_base=None):
        self.root = root.resolve()
        self.output = output.resolve()
        self.source_base = source_base
        self.modules = {}
        self.text = {}

    def read(self, file):
        if file not in self.text:
            relative = Path(file)
            path = (self.root / relative).resolve()
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Use a project-relative source path: {file}")
            if not path.is_relative_to(self.root) or not path.is_file():
                raise ValueError(f"Missing source file inside project: {file}")
            self.text[file] = path.read_text(encoding="utf-8")
        return self.text[file]

    def symbols(self, file):
        if file not in self.modules:
            index = {}
            if Path(file).suffix == ".py":
                tree = ast.parse(self.read(file), filename=file)

                def collect(body, prefix=""):
                    for node in body:
                        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                            key = prefix + node.name
                            index[key] = node.lineno
                            collect(node.body, key + ".")
                        else:
                            collect(ast.iter_child_nodes(node), prefix)

                collect(tree.body)
            self.modules[file] = index
        return self.modules[file]

    def resolve(self, ref):
        file, _, symbol = ref.partition("#")
        source = self.read(file)
        line = None
        if re.fullmatch(r"L[1-9][0-9]*", symbol):
            line = int(symbol[1:])
            if line > source.count("\n") + (not source.endswith("\n")):
                raise ValueError(f"Line outside source file: {ref}")
            symbol = ""
        elif symbol:
            line = self.symbols(file).get(symbol)
            if line is None:
                raise ValueError(f"Unknown definition: {ref}. Use #L<line> for explicit locations.")
        if self.source_base:
            relative = f"{self.source_base.rstrip('/')}/{quote(file)}"
        else:
            relative = quote(Path(os.path.relpath(self.root / file, self.output)).as_posix())
        return {"file": file, "symbol": symbol, "line": line,
                "href": relative + (f"#L{line}" if line else "")}

    def add(self, parent, ref):
        source = self.resolve(ref)
        file, symbol, line = source["file"], source["symbol"], source["line"]
        link = element(parent, "a", href=source["href"])
        location = f"{file}:{line}" if line else file
        element(link, "title", f"{symbol} · {location}" if symbol else location)
        return link, line


def start_svg(view, width, height):
    svg = element(None, "svg", viewBox=f"0 0 {width} {height}", width=width,
                  height=height, role="img", aria_label=view["title"])
    element(svg, "title", view["title"])
    element(svg, "desc", view["subtitle"])
    rectangle(svg, 0, 0, width, height, fill=PAPER, rx=0)
    text(svg, view["title"], 40, 56, size=35, weight=700)
    text(svg, view["subtitle"], 42, 89, size=16, color=MUTED)
    return svg


def draw_edge(parent, edge, boxes, curved=False):
    source, target, *kind = edge
    ax, ay, aw, ah = boxes[source]
    bx, by, bw, bh = boxes[target]
    dashed = kind[:1] == ["async"]
    if ay == by:
        if ax < bx:
            start, end = (ax + aw, ay + ah / 2), (bx, by + bh / 2)
        else:
            start, end = (ax, ay + ah / 2), (bx + bw, by + bh / 2)
        points = [start, end]
    elif dashed and ax == bx == 56:
        source_y, target_y = ay + ah / 2, by + bh / 2
        points = [(ax, source_y), (ax - 14, source_y), (bx - 14, target_y), (bx, target_y)]
    else:
        if ay < by:
            start, end = (ax + aw / 2, ay + ah), (bx + bw / 2, by)
        else:
            start, end = (ax + aw / 2, ay), (bx + bw / 2, by + bh)
        middle = (start[1] + end[1]) / 2
        points = [start, (start[0], middle), (end[0], middle), end]
    attrs = {"stroke_dasharray": "6 5"} if dashed else {}
    style = dict(stroke="#557383", stroke_width=2, fill="none", marker_end="url(#arrow)",
                 data_from=source, data_to=target, data_kind="async" if dashed else "flow", **attrs)
    if curved and ay != by:
        x1, y1 = ax + aw / 2, ay + (ah if ay < by else 0)
        x2, y2 = bx + bw / 2, by + (0 if ay < by else bh)
        mid = (y1 + y2) / 2
        arrow = element(parent, "path", d=f"M{x1},{y1} C{x1},{mid} {x2},{mid} {x2},{y2}", **style)
    else:
        arrow = element(parent, "polyline", points=" ".join(f"{x},{y}" for x, y in points), **style)
    if len(kind) > 1:
        element(arrow, "title", kind[1])


def draw_graph(view, sources):
    columns = view["columns"]
    width = 1430
    row_height = 197
    gap = 40
    card_width = (width - 112 - (columns - 1) * gap) / columns
    height = 172 + len(view["lanes"]) * row_height
    svg = start_svg(view, width, height)
    defs = element(svg, "defs")
    marker = element(defs, "marker", id="arrow", markerWidth=8, markerHeight=8,
                     refX=7, refY=4, orient="auto")
    element(marker, "path", d="M0 0L8 4L0 8Z", fill="#557383")
    boxes = {}
    for index, lane in enumerate(view["lanes"]):
        y = 123 + index * row_height
        rectangle(svg, 40, y, width - 80, 157, fill="#edf3f6", stroke=RULE)
        occupied = set()
        for column, node in enumerate(lane["nodes"]):
            if node is None:
                continue
            slot = node.get("column", column)
            if slot in occupied or not 0 <= slot < columns or node["id"] in boxes:
                raise ValueError(f"Duplicate or invalid node position: {node['id']}")
            occupied.add(slot)
            boxes[node["id"]] = (56 + slot * (card_width + gap), y + 42, card_width, 99)
    for edge in view["edges"]:
        draw_edge(svg, edge, boxes, view.get("topology", False))
    for index, lane in enumerate(view["lanes"]):
        y = 123 + index * row_height
        rectangle(svg, 55, y + 8, 7 + 8 * len(lane["label"]), 25, fill="#edf3f6", rx=2)
        text(svg, lane["label"], 56, y + 26, size=14, color=LINK, weight=700)
        for node in filter(None, lane["nodes"]):
            x, y_card, w, h = boxes[node["id"]]
            group = element(svg, "g", id=node["id"], data_source=node.get("ref", ""))
            fill, stroke = TONES[node.get("tone", "normal")]
            if node.get("ref"):
                group, line = sources.add(group, node["ref"])
            else:
                line = None
            rectangle(group, x, y_card, w, h, fill=fill, stroke=stroke, stroke_width=1.4)
            text(group, node["title"], x + 12, y_card + 24, size=16, weight=700)
            if "ref" in node:
                filename = node["ref"].partition("#")[0].rsplit("/", 1)[-1]
                text(group, f"{filename}:{line}" if line else filename, x + 12,
                     y_card + 43, size=12, color=LINK, family=MONO)
            detail = lines(node["detail"], int((w - 24) / 7))
            if len(detail) > 3:
                raise ValueError(f"Shorten node detail: {view['id']}/{node['id']}")
            for row, body in enumerate(detail):
                text(group, body, x + 12, y_card + 62 + row * 15, size=13, color=MUTED)
    text(svg, view.get("legend", "Solid arrow · Call or control flow  /  Dashed arrow · Async handoff or framework delegation"),
         42, height - 28, size=14, color=MUTED)
    return svg


def draw_catalog(view, sources):
    prepared = []
    for row in view["files"]:
        card = file_card(row)
        description = lines(card["detail"], 76)
        symbol_lines = sum(len(lines(item["detail"], 39)) for item in card["definitions"])
        height = 70 + 18 * len(description) + 20 * len(card["entries"]) + 20 * symbol_lines
        prepared.append((card, description, height))
    rows = [prepared[index:index + 2] for index in range(0, len(prepared), 2)]
    total_height = 152 + sum(max(height for _, _, height in row) + 20 for row in rows)
    svg = start_svg(view, 1430, total_height)
    y = 123
    for row in rows:
        for column, (card, description, height) in enumerate(row):
            file = card["path"]
            x = 40 + column * 685
            group = element(svg, "g", id=file.replace("/", "-"), data_source=file)
            rectangle(group, x, y, 665, height, fill="#ffffff", stroke=RULE)
            link, _ = sources.add(group, file)
            text(link, file, x + 16, y + 27, size=18, weight=700, family=MONO)
            at = y + 50
            for body in description:
                text(group, body, x + 16, at, size=15, color=MUTED)
                at += 18
            at += 7
            for index, entry in enumerate(card["entries"]):
                link, line = sources.add(group, entry["ref"])
                label = f"{entry['label'] or 'Open file'}  /  line {line or 1}"
                text(link, label, x + 16, at, size=14, weight=700,
                     family=MONO, color=LINK)
                if index == 0:
                    text(group, "START HERE", x + 548, at, size=12, color=LINK, weight=700)
                at += 20
            for definition in card["definitions"]:
                link, _ = sources.add(group, definition["ref"])
                _, _, anchor = definition["ref"].partition("#")
                label = definition["label"] if anchor.startswith("L") and anchor[1:].isdigit() else anchor
                text(link, label, x + 16, at, size=13, family=MONO, weight=650)
                description_lines = lines(definition["detail"], 39)
                for index, body in enumerate(description_lines):
                    text(group, body, x + 382, at + 15 * index, size=13, color=MUTED)
                at += 20 * len(description_lines)
        y += max(height for _, _, height in row) + 20
    return svg


def format_code_line(line, spans):
    if not spans:
        return line
    chunks = []
    cursor = 0
    for start, end, style in spans:
        if start > cursor:
            chunks.append(line[cursor:start])
        chunks.append((style, line[start:end]))
        cursor = end
    if cursor < len(line):
        chunks.append(line[cursor:])
    return chunks


def source_lines(path, source):
    lines = source.removesuffix("\n").split("\n")
    if path.suffix != ".py":
        return lines

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError):
        return lines
    spans = [[] for line in lines]
    definition_name = False
    for token in tokens:
        kind = tokenize.tok_name[token.type]
        style = PYTHON_TOKEN_STYLES.get(kind)
        if kind == "NAME":
            if definition_name:
                style = "definition"
            elif keyword.iskeyword(token.string):
                style = "keyword"
            definition_name = token.string in {"def", "class"}
        elif kind.startswith(("FSTRING_", "TSTRING_")):
            style = "string"
        if style is None:
            continue

        first, first_column = token.start
        last, last_column = token.end
        for row in range(first, last + 1):
            start = first_column if row == first else 0
            end = last_column if row == last else len(lines[row - 1])
            if start < end:
                spans[row - 1].append((start, end, style))
    return [format_code_line(line, tokens) for line, tokens in zip(lines, spans, strict=True)]


def import_targets(statement, package, modules):
    if isinstance(statement, ast.Import):
        return [modules[alias.name] for alias in statement.names if alias.name in modules]
    if isinstance(statement, ast.ImportFrom):
        module = statement.module or ""
        if statement.level:
            try:
                module = resolve_name("." * statement.level + module, package)
            except ImportError:
                return []
        return [
            target for alias in statement.names
            if (target := modules.get(f"{module}.{alias.name}", modules.get(module)))
        ]
    return []


def local_imports(resolver, paths):
    by_path = {}
    for path in paths:
        if not path.endswith(".py"):
            continue
        module_parts = Path(path).with_suffix("").parts
        parts = module_parts[:-1] if module_parts[-1] == "__init__" else module_parts
        by_path[path] = parts
    modules = {
        ".".join(parts): path for path, parts in by_path.items()
        if parts and all(part.isidentifier() for part in parts)
    }

    edges = defaultdict(set)
    for path, parts in by_path.items():
        package = ".".join(parts if Path(path).name == "__init__.py" else parts[:-1])
        try:
            tree = ast.parse(resolver.read(path), filename=path)
        except SyntaxError:
            # Line-based links still work when the project's grammar is newer.
            continue
        for statement in ast.walk(tree):
            for target in import_targets(statement, package, modules):
                if target != path:
                    edges[path, target].add(statement.lineno)
    return edges


def revision_links(root, revision_url, paths):
    # The working tree may include files that differ from the published revision.
    revision = revision_url.rstrip("/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not revision_url.startswith("https://"):
        raise ValueError("--revision-url requires an HTTPS source URL ending in a full Git commit SHA")
    entries = subprocess.check_output(["git", "ls-tree", "-rz", revision], cwd=root).split(b"\0")
    blobs = {}
    for entry in filter(None, entries):
        meta, path = entry.split(b"\t", 1)
        blobs[os.fsdecode(path)] = meta.split()[-1].decode()
    result = {}
    for path in paths:
        data = (root / path).read_bytes()
        digest = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        if blobs.get(path) == digest:
            result[path] = f"{revision_url.rstrip('/')}/{quote(path)}"
    return result


def build_web(views, resolver, project, guide_url, revision_url=None):
    flows = [view for view in views if "lanes" in view]
    documents = [view for view in views if "sections" in view]
    catalogs = [
        {**view, "files": [file_card(row) for row in view["files"]]}
        for view in views if "files" in view
    ]
    refs = {
        node["ref"] for view in flows for lane in view["lanes"]
        for node in lane["nodes"] if node and node.get("ref")
    }
    for catalog in catalogs:
        for card in catalog["files"]:
            refs.update(catalog_refs(card))
    refs.update(
        link["ref"] for page in documents for section in page["sections"]
        for link in section.get("links", []) if "ref" in link
    )

    sources = {ref: resolver.resolve(ref) for ref in sorted(refs)}
    paths = sorted({source["file"] for source in sources.values()})
    if revision_url:
        urls = revision_links(resolver.root, revision_url, paths)
        for source in sources.values():
            if url := urls.get(source["file"]):
                source["externalHref"] = url + (f"#L{source['line']}" if source["line"] else "")
    elif resolver.source_base:
        for source in sources.values():
            source["externalHref"] = source["href"]
    catalog_paths = sorted({card["path"] for catalog in catalogs for card in catalog["files"]})
    dependencies = local_imports(resolver, catalog_paths)
    for catalog in catalogs:
        for importer, imported, anchors in catalog.get("dependencies", []):
            dependencies[importer, imported].update(anchors)
    data = {
        "project": project,
        "flows": flows,
        "documents": documents,
        "catalogs": catalogs,
        "sources": sources,
        "sourceFiles": {path: source_lines(Path(path), resolver.read(path)) for path in paths},
        "dependencies": [[source, target, sorted(anchors)] for (source, target), anchors in sorted(dependencies.items())],
    }
    assets = Path(__file__).resolve().parents[1] / "assets" / "web"
    tokens = {
        "TITLE": escape(project),
        "STYLES": (assets / "style.css").read_text(encoding="utf-8"),
        "SCRIPT": (assets / "app.js").read_text(encoding="utf-8"),
        "DATA": json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c"),
        "GUIDE_URL": escape(guide_url),
        "GUIDE_HIDDEN": "" if guide_url else "hidden",
    }
    template = (assets / "page.html").read_text(encoding="utf-8")
    return re.sub(r"@@([A-Z_]+)@@", lambda match: tokens[match[1]], template)


def main():
    parser = argparse.ArgumentParser(description="Render source-linked codebase diagrams from JSON.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root for source references.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--web", action="store_true", help="Generate a standalone interactive index.html.")
    parser.add_argument("--project", help="Project name in the web atlas. Defaults to the project directory.")
    parser.add_argument("--source-base", help="Hosted base URL for links to source paths.")
    parser.add_argument("--revision-url", help="Add web source links for files identical to this Git revision URL.")
    parser.add_argument("--guide-url", help="URL of the atlas guide. Defaults to README.md if present in the output directory.")
    parser.add_argument("spec", type=Path, nargs="+")
    args = parser.parse_args()
    sources = SourceLinks(args.root, args.out, args.source_base)
    rendered = {}
    views = [
        view for spec in args.spec for view in json.loads(spec.read_text(encoding="utf-8"))
    ]
    findings = review(views, sources)
    if findings:
        parser.error("\n".join(findings))
    if not args.web and any("sections" in view for view in views):
        parser.error("Documentation pages require --web.")
    for view in views:
        view_id = view["id"]
        if "sections" in view:
            continue
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", view_id) is None or view_id in rendered:
            raise ValueError(f"Duplicate or invalid view ID: {view_id}")
        draw = draw_graph if "lanes" in view else draw_catalog
        rendered[view_id] = draw(view, sources)
    guide_url = args.guide_url or ("README.md" if (args.out / "README.md").is_file() else "")
    web = build_web(views, sources, args.project or sources.root.name, guide_url, args.revision_url) if args.web else None
    args.out.mkdir(parents=True, exist_ok=True)
    for view_id, svg in rendered.items():
        ET.indent(svg, space="  ")
        target = args.out / f"{view_id}.svg"
        ET.ElementTree(svg).write(target, encoding="utf-8", xml_declaration=True)
        print(target)
    if web is not None:
        target = args.out / "index.html"
        target.write_text(web, encoding="utf-8")
        print(target)


if __name__ == "__main__":
    main()

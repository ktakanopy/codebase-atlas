"""Check source coverage, navigation and evidence in a proposed codebase atlas."""

import argparse
import ast
import json
import re
from pathlib import Path

from atlas_catalog import catalog_refs, file_card


def valid_document_block(block):
    if isinstance(block, str):
        return bool(block.strip())
    if not isinstance(block, dict):
        return False
    if "code" in block:
        return isinstance(block["code"], str) and bool(block["code"].strip())
    if "items" in block:
        return isinstance(block["items"], list) and bool(block["items"]) and all(
            isinstance(item, str) for item in block["items"]
        )
    headers = block.get("headers")
    rows = block.get("rows")
    return isinstance(headers, list) and bool(headers) and all(isinstance(item, str) for item in headers) and (
        isinstance(rows, list) and bool(rows) and all(
            isinstance(row, list) and len(row) == len(headers) and all(isinstance(item, str) for item in row)
            for row in rows
        )
    )


def review(views, resolver, includes=(), services=()):
    findings = []
    steps = {}
    paths = set()
    classes = set()
    mapped_components = set()
    identifiers = set()
    for view in views:
        name = view["id"]
        if name in identifiers or name in {"files", "imports"}:
            findings.append(f"{name}: duplicate or reserved view ID")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            findings.append(f"{name}: invalid view ID")
        identifiers.add(name)
        refs = []
        if sum(key in view for key in ("lanes", "files", "sections")) != 1:
            findings.append(f"{name}: expected exactly one of lanes, files or sections")
        if "lanes" in view:
            columns = view.get("columns")
            if type(columns) is not int or columns < 1:
                findings.append(f"{name}: columns must be a positive integer")
            nodes = [node for lane in view["lanes"] for node in lane["nodes"] if node]
            steps[name] = {node["id"] for node in nodes}
            if len(nodes) != len(steps[name]):
                findings.append(f"{name}: duplicate node")
            for node in nodes:
                if node.get("ref"):
                    refs.append(node["ref"])
                if component := node.get("component"):
                    mapped_components.add(component)
                    if not node.get("ref"):
                        findings.append(f"{name}/{node['id']}: component {component} needs a source reference")
                if node.get("composeService"):
                    service = node["composeService"]
                    mapped_components.add(service)
                    ref = node.get("ref", "")
                    try:
                        source = resolver.resolve(ref)
                        line = source["line"]
                        content = resolver.read(source["file"]).split("\n")
                        if not line or content[line - 1].strip() != service + ":":
                            findings.append(f"{name}/{node['id']}: service {service} needs its declaration line")
                    except (ValueError, OSError, IndexError):
                        findings.append(f"{name}/{node['id']}: invalid service reference {ref}")
            for edge in view["edges"]:
                if not set(edge[:2]) <= steps[name]:
                    findings.append(f"{name}: unknown edge endpoint {edge[:2]}")
            for message in view.get("transcript", []):
                if message["node"] not in steps[name]:
                    findings.append(f"{name}: transcript points to missing node {message['node']}")
        if "sections" in view:
            sections = view["sections"]
            steps[name] = set()
            if not sections:
                findings.append(f"{name}: documentation needs at least one section")
            for section in sections:
                identifier = section["id"]
                if identifier in steps[name] or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
                    findings.append(f"{name}: duplicate or invalid section ID {identifier}")
                steps[name].add(identifier)
                blocks = section.get("blocks")
                if not isinstance(blocks, list) or not blocks or any(not valid_document_block(block) for block in blocks):
                    findings.append(f"{name}/{identifier}: expected nonempty paragraphs, lists, tables or code blocks")
                for link in section.get("links", []):
                    if not link.get("label") or bool(link.get("ref")) == bool(link.get("target")):
                        findings.append(f"{name}/{identifier}: a link needs a label and exactly one source or Atlas target")
                    if link.get("ref"):
                        refs.append(link["ref"])
        for row in view.get("files", []):
            card = file_card(row)
            file = card["path"]
            if file in paths:
                findings.append(f"{file}: duplicate file card")
            paths.add(file)
            refs.extend(catalog_refs(card))
            classes.update((file, symbol["label"]) for symbol in card["definitions"])
        for ref in set(refs):
            try:
                resolver.resolve(ref)
            except (ValueError, OSError, SyntaxError) as error:
                findings.append(f"{name}: {error}")

    flow_ids = {v["id"] for v in views if "lanes" in v}
    parents = {v["id"]: v["parent"] for v in views if "parent" in v}
    for name in parents:
        current = name
        visited = set()
        while current in parents:
            if current in visited:
                findings.append(f"{name}: cyclic layer hierarchy")
                break
            visited.add(current)
            current = parents[current]
            if current not in flow_ids:
                findings.append(f"{name}: missing parent {current}")
                break
    for view in views:
        if "dependencies" in view and "files" not in view:
            findings.append(f"{view['id']}: declare dependencies in a reference view")
        for dependency in view.get("dependencies", []):
            if not isinstance(dependency, list) or len(dependency) != 3:
                findings.append(f"{view['id']}: expected a dependency with source, target and line numbers")
                continue
            source, target, lines = dependency
            if source == target or source not in paths or target not in paths:
                findings.append(f"{view['id']}: dependency requires distinct cataloged files: {source}, {target}")
                continue
            if not isinstance(lines, list) or not lines or any(type(line) is not int or line < 1 for line in lines):
                findings.append(f"{view['id']}: dependency {source} to {target} needs positive source line numbers")
                continue
            for line in lines:
                try:
                    resolver.resolve(f"{source}#L{line}")
                except (ValueError, OSError) as error:
                    findings.append(f"{view['id']}: {error}")
        if "startJourney" in view and view["startJourney"] not in flow_ids:
            findings.append(f"{view['id']}: missing start journey {view['startJourney']}")
        routes = [
            (node["id"], target) for lane in view.get("lanes", [])
            for node in filter(None, lane["nodes"]) for target in node.get("drill", [])
        ]
        routes.extend(
            (section["id"], link["target"]) for section in view.get("sections", [])
            for link in section.get("links", []) if link.get("target")
        )
        for identifier, route in routes:
            target, _, section = route.partition("/")
            if target not in steps or (section and section not in steps[target]):
                findings.append(f"{view['id']}/{identifier}: missing detail {route}")

    for pattern in includes:
        for path in resolver.root.glob(pattern):
            if not path.is_file():
                continue
            file = path.relative_to(resolver.root).as_posix()
            if file not in paths:
                findings.append(f"{file}: missing file card")
            elif path.suffix == ".py":
                try:
                    tree = ast.parse(resolver.read(file), filename=file)
                except (ValueError, OSError, SyntaxError) as error:
                    findings.append(f"{file}: could not check Python class coverage: {error}")
                    continue
                for node in tree.body:
                    if isinstance(node, ast.ClassDef) and (file, node.name) not in classes:
                        findings.append(f"{file}#{node.name}: missing class card")
    for name in sorted(set(services) - mapped_components):
        findings.append(f"{name}: missing architecture component")
    return sorted(set(findings))


def main():
    from render_atlas import SourceLinks

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", nargs="+", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--include", action="append", default=[], help="Project-relative file inventory glob (repeatable).")
    parser.add_argument("--components", "--services", nargs="+", default=[],
                        help="Expected services, processes or other architecture components.")
    args = parser.parse_args()
    views = [v for path in args.spec for v in json.loads(path.read_text(encoding="utf-8"))]
    findings = review(views, SourceLinks(args.root, args.root), args.include, args.components)
    if findings:
        print("\n".join(findings))
        return 1
    print(f"Checked {len(views)} views. Source references, edges and detail links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

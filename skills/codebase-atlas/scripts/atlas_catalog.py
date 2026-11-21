"""Normalize file and symbol cards for rendering and review."""


def source_ref(file, anchor=""):
    return f"{file}#{anchor}" if anchor else file


def file_card(row):
    file, detail, entries, definitions = row
    entry_cards = []
    for entry in entries:
        label, anchor = (entry, entry) if isinstance(entry, str) else entry
        entry_cards.append({"label": label, "ref": source_ref(file, anchor)})

    definition_cards = []
    for name, purpose, *targets in definitions:
        target = targets[0] if targets else ""
        if target.startswith("#"):
            declaration = anchor = target[1:]
        else:
            declaration = name
            anchor = f"{name}.{target}" if target else name
        definition_cards.append({
            "label": name,
            "detail": purpose,
            "ref": source_ref(file, anchor),
            "declaration": source_ref(file, declaration),
        })

    return {"path": file, "detail": detail, "entries": entry_cards, "definitions": definition_cards}


def catalog_refs(card):
    yield card["path"]
    yield from (entry["ref"] for entry in card["entries"])
    for definition in card["definitions"]:
        yield definition["declaration"]
        yield definition["ref"]

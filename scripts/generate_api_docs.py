#!/usr/bin/env python3
"""Generate docs/03-backend-api.md from the FastAPI OpenAPI schema.

Usage:
    python scripts/generate_api_docs.py [output_path]

Default output: docs/03-backend-api.md
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


def _clean_description(text: str) -> str:
    """Strip Python-style docstring sections (Args, Returns, Raises) from FastAPI descriptions."""
    if not text:
        return text
    _SECTION_HEADERS = {"Args:", "Returns:", "Raises:", "Yields:", "Note:", "Notes:", "Example:", "Examples:"}
    lines = text.splitlines()
    result: list[str] = []
    skip_section = False
    for line in lines:
        stripped = line.strip()
        if stripped in _SECTION_HEADERS:
            skip_section = True
            continue
        # A non-indented, non-empty line that isn't a section header ends the skip
        if skip_section and stripped and not line.startswith(" ") and not line.startswith("\t"):
            skip_section = False
        if not skip_section:
            result.append(line)
    return "\n".join(result).strip()


def _resolve_ref(schema: dict, ref: str) -> dict:
    parts = ref.lstrip("#/").split("/")
    node = schema
    for part in parts:
        node = node.get(part, {})
    return node  # type: ignore[return-value]


def _schema_summary(prop_schema: dict, full_schema: dict) -> str:
    if "$ref" in prop_schema:
        resolved = _resolve_ref(full_schema, prop_schema["$ref"])
        return resolved.get("title", prop_schema["$ref"].split("/")[-1])
    anyof = prop_schema.get("anyOf", [])
    if anyof:
        parts = []
        for s in anyof:
            if s.get("type") == "null":
                continue
            parts.append(_schema_summary(s, full_schema))
        return " | ".join(parts) + " | null" if len(anyof) > len(parts) else " | ".join(parts)
    t = prop_schema.get("type", "")
    if t == "array":
        items = prop_schema.get("items", {})
        return f"array[{_schema_summary(items, full_schema)}]"
    return t or "any"


def _body_table(request_body: dict, full_schema: dict) -> list[str]:
    lines: list[str] = []
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    body_schema = json_content.get("schema", {})
    if "$ref" in body_schema:
        body_schema = _resolve_ref(full_schema, body_schema["$ref"])
    props = body_schema.get("properties", {})
    required = body_schema.get("required", [])
    if not props:
        return lines
    lines.append("\n**Request body:**\n")
    lines.append("| Field | Type | Required |")
    lines.append("|---|---|---|")
    for name, prop in props.items():
        typ = _schema_summary(prop, full_schema)
        req = "yes" if name in required else "no"
        lines.append(f"| `{name}` | {typ} | {req} |")
    return lines


def schema_to_markdown(schema: dict) -> str:
    lines: list[str] = [
        "# API Reference\n",
        "> Auto-generated — run `make doc` to update.\n",
        f"**Base URL:** `http://localhost:8123`  \n"
        f"**Interactive docs (Redoc):** [`/api-docs`](http://localhost:8123/api-docs)\n",
    ]

    # Group operations by tag
    tag_ops: dict[str, list[tuple[str, str, dict]]] = {}
    for path, methods in schema.get("paths", {}).items():
        for method, op in methods.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            tags = op.get("tags", ["misc"])
            for tag in tags:
                tag_ops.setdefault(tag, []).append((method.upper(), path, op))

    for tag in sorted(tag_ops):
        lines.append(f"\n## {tag.title()}\n")
        for method, path, op in tag_ops[tag]:
            summary = op.get("summary", "")
            description = _clean_description(op.get("description", ""))
            lines.append(f"### `{method} {path}`\n")
            if summary:
                lines.append(f"{summary}\n")
            if description and description != summary:
                lines.append(f"{description}\n")

            # Request body
            if "requestBody" in op:
                lines.extend(_body_table(op["requestBody"], schema))

            # Path / query parameters
            params = op.get("parameters", [])
            if params:
                lines.append("\n**Parameters:**\n")
                lines.append("| Name | In | Type | Required | Description |")
                lines.append("|---|---|---|---|---|")
                for p in params:
                    p_schema = p.get("schema", {})
                    typ = _schema_summary(p_schema, schema)
                    req = "yes" if p.get("required") else "no"
                    desc = p.get("description", "")
                    lines.append(f"| `{p['name']}` | {p['in']} | {typ} | {req} | {desc} |")

            # Responses
            responses = op.get("responses", {})
            resp_parts = []
            for code, resp in responses.items():
                resp_desc = resp.get("description", "")
                resp_parts.append(f"`{code}` {resp_desc}")
            if resp_parts:
                lines.append(f"\n**Responses:** {' · '.join(resp_parts)}\n")

    return "\n".join(lines)


def main() -> None:
    output = sys.argv[1] if len(sys.argv) > 1 else "docs/03-backend-api.md"

    # Point to a temp data dir so startup doesn't touch real data
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["AUBERGE_DATA_DIR"] = tmp
        os.environ.setdefault("AUBERGE_DISABLE_ADMIN_AUTH", "1")

        repo_root = Path(__file__).parent.parent
        sys.path.insert(0, str(repo_root))

        # Silence startup log noise
        import logging
        logging.disable(logging.CRITICAL)

        from aubergeRP.main import create_app  # noqa: PLC0415

        app = create_app()
        openapi_schema = app.openapi()

    md = schema_to_markdown(openapi_schema)
    out_path = Path(output)
    out_path.write_text(md, encoding="utf-8")
    print(f"API docs written to {out_path}")


if __name__ == "__main__":
    main()

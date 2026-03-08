#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

RESERVED_COLUMNS = {
    "external_key",
    "split",
    "tags",
    "attachments",
}

COMMON_ALIASES = {
    "prompt": "user_prompt",
    "answer": "candidate_answer",
    "response": "candidate_answer",
    "comment": "user_comment",
}


def parse_jsonish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in {"true", "false", "null"}:
        return json.loads(lowered)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def load_rows(path: Path, fmt: str) -> list[dict[str, Any]]:
    actual = fmt
    if fmt == "auto":
        suffix = path.suffix.lower()
        if suffix == ".csv":
            actual = "csv"
        elif suffix in {".jsonl", ".ndjson"}:
            actual = "jsonl"
        else:
            actual = "json"
    if actual == "csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]
    if actual == "jsonl":
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if text:
                    rows.append(json.loads(text))
        return rows
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]
    raise SystemExit("input JSON must be a list of objects or an object with an 'items' list")


def parse_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    parsed = parse_jsonish(value)
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item)]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_attachments(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    parsed = parse_jsonish(value)
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def normalize_split(value: Any, default_split: str) -> str:
    text = str(value or default_split).strip() or default_split
    allowed = {"gold", "test", "unannotated"}
    if text not in allowed:
        raise SystemExit(f"unsupported split '{text}', expected one of {sorted(allowed)}")
    return text


def build_item(
    row: dict[str, Any],
    row_index: int,
    default_split: str,
    payload_fields: list[str] | None,
    rename_map: dict[str, str],
    external_key_field: str,
) -> dict[str, Any]:
    external_key = row.get(external_key_field)
    if external_key in {None, ""}:
        external_key = f"row-{row_index:06d}"
    split = normalize_split(row.get("split"), default_split)
    payload: dict[str, Any] = {}

    if payload_fields:
        selected_fields = payload_fields
    else:
        selected_fields = [key for key in row.keys() if key not in RESERVED_COLUMNS]

    for field in selected_fields:
        if field not in row:
            continue
        target = rename_map.get(field, COMMON_ALIASES.get(field, field))
        payload[target] = parse_jsonish(row[field])

    return {
        "external_key": str(external_key),
        "payload": payload,
        "tags": parse_tags(row.get("tags")),
        "attachments": parse_attachments(row.get("attachments")),
        "split": split,
    }


def build_call_payload(
    mode: str,
    project_id: str | None,
    dataset_id: str | None,
    dataset_name: str | None,
    description: str | None,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    if mode == "register":
        if not project_id or not dataset_name:
            raise SystemExit("register mode requires --project-id and --dataset-name")
        return {
            "tool": "register_dataset",
            "arguments": {
                "payload": {
                    "project_id": project_id,
                    "name": dataset_name,
                    "description": description,
                    "items": items,
                }
            },
        }
    if mode == "upsert":
        if not dataset_id:
            raise SystemExit("upsert mode requires --dataset-id")
        return {
            "tool": "upsert_dataset_items",
            "arguments": {
                "dataset_id": dataset_id,
                "payload": {
                    "items": items,
                },
            },
        }
    raise SystemExit(f"unsupported mode '{mode}'")


def wrap_plan(call_payload: dict[str, Any], env: dict[str, str] | None) -> dict[str, Any]:
    plan = {"calls": [call_payload]}
    if env:
        plan["env"] = env
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Build MCP dataset payloads or plans from CSV/JSON/JSONL files.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--format", choices=["auto", "csv", "json", "jsonl"], default="auto")
    parser.add_argument("--mode", choices=["register", "upsert"], required=True)
    parser.add_argument("--project-id")
    parser.add_argument("--dataset-id")
    parser.add_argument("--dataset-name")
    parser.add_argument("--description")
    parser.add_argument("--default-split", default="unannotated")
    parser.add_argument("--external-key-field", default="external_key")
    parser.add_argument("--payload-field", action="append", default=[])
    parser.add_argument("--rename", action="append", default=[], help="old:new mapping; repeatable")
    parser.add_argument("--output-kind", choices=["call", "plan"], default="call")
    parser.add_argument("--output", required=True)
    parser.add_argument("--env", action="append", default=[], help="KEY=VALUE entries for plan mode")
    args = parser.parse_args()

    rename_map: dict[str, str] = {}
    for item in args.rename:
        if ":" not in item:
            raise SystemExit(f"invalid --rename value '{item}', expected old:new")
        old, new = item.split(":", 1)
        rename_map[old] = new

    env: dict[str, str] = {}
    for item in args.env:
        if "=" not in item:
            raise SystemExit(f"invalid --env value '{item}', expected KEY=VALUE")
        key, value = item.split("=", 1)
        env[key] = value

    rows = load_rows(Path(args.input).resolve(), args.format)
    items = [
        build_item(
            row=row,
            row_index=index,
            default_split=args.default_split,
            payload_fields=args.payload_field or None,
            rename_map=rename_map,
            external_key_field=args.external_key_field,
        )
        for index, row in enumerate(rows, start=1)
    ]

    call_payload = build_call_payload(
        mode=args.mode,
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        dataset_name=args.dataset_name,
        description=args.description,
        items=items,
    )
    output_payload = wrap_plan(call_payload, env) if args.output_kind == "plan" else call_payload
    Path(args.output).write_text(json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

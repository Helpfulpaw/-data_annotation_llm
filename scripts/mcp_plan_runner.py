#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"\{\{([^{}]+)\}\}")


def get_by_path(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise KeyError(path)
    return current


def render_placeholders(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: render_placeholders(inner, context) for key, inner in value.items()}
    if isinstance(value, list):
        return [render_placeholders(item, context) for item in value]
    if not isinstance(value, str):
        return value
    matches = PLACEHOLDER_RE.findall(value)
    if not matches:
        return value
    if value.strip() == f"{{{{{matches[0]}}}}}" and len(matches) == 1:
        return deepcopy(get_by_path(context, matches[0].strip()))

    def replace(match: re.Match[str]) -> str:
        resolved = get_by_path(context, match.group(1).strip())
        if isinstance(resolved, (dict, list)):
            return json.dumps(resolved, ensure_ascii=False)
        return str(resolved)

    return PLACEHOLDER_RE.sub(replace, value)


async def execute_plan(workspace: Path, plan_file: Path) -> dict[str, Any]:
    plan = json.loads(plan_file.read_text())
    for key, value in (plan.get("env") or {}).items():
        os.environ[str(key)] = str(value)

    sys.path.insert(0, str((workspace / "src").resolve()))
    from lan_orchestrator.db import Base, engine  # noqa: WPS433
    from lan_orchestrator.mcp.server import build_mcp_server  # noqa: WPS433

    Base.metadata.create_all(bind=engine)
    server = build_mcp_server()
    context: dict[str, Any] = {}
    outputs: list[dict[str, Any]] = []

    for index, call in enumerate(plan.get("calls", []), start=1):
        tool = call["tool"]
        arguments = render_placeholders(call.get("arguments", {}), context)
        _, payload = await server.call_tool(tool, arguments)
        record = {"index": index, "tool": tool, "arguments": arguments, "payload": payload}
        outputs.append(record)
        save_as = call.get("save_as")
        if save_as:
            context[save_as] = payload

    return {"plan_file": str(plan_file), "results": outputs, "context": context}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an ordered MCP plan file against the LAN orchestrator workspace.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--plan-file", required=True)
    args = parser.parse_args()

    result = asyncio.run(execute_plan(Path(args.workspace).resolve(), Path(args.plan_file).resolve()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

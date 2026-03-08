---
name: lan-orchestrator-mcp
description: Operate the LAN annotation/orchestration service through its MCP surface. Use when Codex needs to manage datasets, build or expand gold/test sets, enqueue unlabeled tasks, update prompt versions and regress them on gold, launch run_all cycles, create or validate annotation graphs, run classical AutoML rounds, distill prompt nodes into ML nodes, switch graph branches into ML-only mode, or estimate whether gold/test size is sufficient.
---

# LAN Orchestrator MCP

Operate the service through MCP only. Do not fall back to REST unless the user explicitly asks for REST.

Do not import or call Python service modules to run business workflows. Do not use internal `lan_orchestrator.*` methods as the control plane. Use MCP tools as the operational interface; keep the business mapping from task to tool sequence in this skill.

## MCP-First Rule

Drive all business operations through MCP tools:
- create or extend datasets
- move items between `gold`, `test`, and `unannotated`
- create prompt versions
- register or validate graphs
- launch runs
- inspect runs
- create adapters, models, and AutoML policies

Use data files for graph payloads, dataset payloads, and plans. Use MCP to apply those files.

## Graph-As-Data Rule

Represent graph topology, prompt versions, run launches, and dataset/split changes as MCP payloads and data files.

Do not patch service code just to:
- add or remove nodes
- change edges or conditions
- switch prompt versions
- change run targeting
- change gold/test composition
- compare graph variants

Patch service code only when a platform capability is actually missing. Otherwise, keep experimentation in data and call MCP tools with that data.

## Readiness

1. Prefer an already-running MCP server on `http://127.0.0.1:8001/mcp`.
2. If MCP is not up, start it from the service workspace:

```bash
PYTHONPATH=src ./.venv-pip/bin/lan-orchestrator-mcp
```

3. If prompt judges or external adapters depend on local LLM execution, start the LLM bridge too:

```bash
PYTHONPATH=src ./.venv-pip/bin/lan-orchestrator-llm-bridge
```

4. Before creating local judge adapters, probe `detect_lmstudio`.

## Tool Calling Rules

Use flat arguments for these tools:
- `create_project`
- `assign_split`
- `detect_lmstudio`
- `create_general_judge_adapter`
- `detect_comfyui_lan`
- `create_comfyui_qwen_adapter`
- `smoke_test_comfyui_qwen`
- `list_runs`
- `inspect_run`
- `render_graph_plantuml`

Wrap request bodies as `payload={...}` for these tools:
- `register_dataset`
- `upsert_dataset_items`
- `create_prompt_part`
- `create_prompt_config_version`
- `create_model`
- `create_adapter`
- `create_automl_policy`
- `register_graph`
- `validate_graph`
- `create_task`
- `run_gold`
- `run_test`
- `run_unannotated`
- `run_all`

## Operating Rules

1. Keep `ground_truth_*` labels in dataset item payloads; keep routing hints in tags.
2. After any prompt, graph, model, or adapter change, run `validate_graph` and then `run_gold` before broader runs.
3. Use `run_all` for standard promotion flow: `gold -> test -> unannotated`.
4. Keep prompt-based and ML-based graphs versioned separately; compare them on the same `gold/test` slices.
5. Persist project id, dataset id, graph ids, run ids, and artifact paths in the final note.

## Workflow Map

Read only the section you need:
- Business tasks mapped to exact MCP tools: [references/business-playbooks.md](references/business-playbooks.md)
- Dataset curation, split maintenance, prompt regression, unlabeled batches, and AutoML rounds: [references/workflows.md](references/workflows.md)
- Common graph patterns and ML-mode transitions: [references/graph-patterns.md](references/graph-patterns.md)
- Bootstrap sufficiency checks and sample-size heuristics: [references/sufficiency.md](references/sufficiency.md)
- CSV/JSON/JSONL ingestion with prompt columns: [references/input-formats.md](references/input-formats.md)

## Helpers

Keep helpers secondary. Helpers may prepare files or estimate dataset sufficiency, but they must not replace MCP as the control plane.

Use the sufficiency helper only when the user asks whether `gold/test` is large enough:

```bash
python3 scripts/bootstrap_sufficiency.py \
  --db-path ./lan_orchestrator.db \
  --run-id <RUN_ID> \
  --truth-field ground_truth_error_present \
  --pred-field error_present
```

Add `--where-field ground_truth_error_present --where-value true` for error-class-only evaluation.

## MCP Plan Runner

Use the bundled plan runner when the user wants graph and run changes to stay fully data-driven:

```bash
python3 scripts/mcp_plan_runner.py \
  --workspace /path/to/service/workspace \
  --plan-file /path/to/plan.json
```

The plan file should contain ordered MCP calls and optional placeholders from prior results. See [references/plan-format.md](references/plan-format.md).

## Dataset Payload Builder

Use the bundled builder when raw data arrives as `CSV`, `JSON`, or `JSONL`:

```bash
python3 scripts/build_dataset_payload.py \
  --input /path/to/input.csv \
  --mode register \
  --project-id <PROJECT_ID> \
  --dataset-name <DATASET_NAME> \
  --output-kind plan \
  --output /path/to/register-plan.json
```

Then execute the generated plan through `scripts/mcp_plan_runner.py`.

Do not treat the builder as the business workflow itself. The business workflow remains the MCP call sequence described in [references/business-playbooks.md](references/business-playbooks.md).

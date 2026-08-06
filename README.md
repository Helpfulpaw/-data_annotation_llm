# LAN Orchestrator MCP Skill

An experimental agent skill for operating a separate annotation, evaluation, and model-promotion service through MCP.

> **Status:** research prototype. This repository contains the skill instructions, operational playbooks, and helper scripts. It does **not** contain the LAN Orchestrator service itself or a hosted MCP endpoint.

## What this package covers

- Registering datasets and maintaining `gold`, `test`, and `unannotated` splits
- Versioning prompts and running regression checks against gold data
- Creating and validating annotation graphs
- Comparing prompt-based and ML-based graph variants
- Running standard `gold -> test -> unannotated` promotion cycles
- Preparing CSV, JSON, and JSONL inputs as MCP payloads
- Estimating whether evaluation slices are large enough for useful comparisons

## Design principles

1. **MCP is the control plane.** Business operations are executed through MCP tools rather than direct service imports.
2. **Graphs and experiments are data.** Topology, prompt versions, run plans, and split changes stay versioned as payloads.
3. **Regression precedes promotion.** Graph, prompt, model, or adapter changes are validated on gold data before broader runs.
4. **Evidence remains inspectable.** Project IDs, dataset IDs, graph versions, run IDs, and artifacts should be retained with every result.

## Repository map

```text
.
├── SKILL.md                         # Main agent operating instructions
├── agents/openai.yaml               # Agent metadata
├── references/
│   ├── business-playbooks.md        # Business tasks mapped to MCP calls
│   ├── workflows.md                 # Dataset, prompt, and AutoML workflows
│   ├── graph-patterns.md            # Common graph structures
│   ├── input-formats.md             # CSV/JSON/JSONL ingestion
│   ├── plan-format.md               # Data-driven MCP plan format
│   └── sufficiency.md               # Evaluation-size heuristics
└── scripts/
    ├── mcp_plan_runner.py           # Executes ordered MCP plans
    ├── build_dataset_payload.py     # Converts source data into MCP payloads
    └── bootstrap_sufficiency.py     # Estimates evaluation uncertainty
```

## Prerequisites

You need a compatible LAN Orchestrator service running separately. The skill expects an MCP endpoint such as:

```text
http://127.0.0.1:8001/mcp
```

Optional local judge and adapter workflows may also require an OpenAI-compatible local model endpoint, for example LM Studio.

## Typical workflow

1. Read [`SKILL.md`](SKILL.md) and the relevant playbook.
2. Prepare or import a dataset payload.
3. Register and validate the annotation graph.
4. Run the graph on the gold split.
5. Review metrics and failures before running test or unlabeled data.
6. Record the resulting IDs and artifact paths for reproducibility.

Example payload preparation:

```bash
python3 scripts/build_dataset_payload.py \
  --input /path/to/input.csv \
  --mode register \
  --project-id <PROJECT_ID> \
  --dataset-name <DATASET_NAME> \
  --output-kind plan \
  --output /path/to/register-plan.json
```

Example plan execution:

```bash
python3 scripts/mcp_plan_runner.py \
  --workspace /path/to/service/workspace \
  --plan-file /path/to/register-plan.json
```

## Current limitations

- The service implementation and deployment configuration are not included.
- There is no public hosted demo or sample MCP server yet.
- Helper scripts do not currently have a published package or compatibility matrix.
- Evaluation-size guidance is heuristic and should not replace domain-specific statistical design.

## Planned cleanup

- Add a minimal reproducible example dataset and run transcript
- Add automated tests for the helper scripts
- Document the compatible service version and MCP tool schema
- Choose and publish an explicit license before encouraging reuse

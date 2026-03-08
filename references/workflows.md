# MCP Workflows

## Graph As Data

Keep graph experimentation out of service code.

Good:
- `register_graph(payload={...})` with a JSON payload file
- `validate_graph(payload={...})`
- `run_gold` / `run_test` / `run_all` using graph ids produced by MCP
- multiple graph payloads for A/B comparison

Bad:
- editing Python source just to try a new branch or node order
- hardcoding a one-off graph variant into the service layer

Exception:
- patch service code only when the platform cannot express the requested node, parser, runtime, or policy yet

## Dataset And Splits

Use this flow for initial dataset creation, gold/test expansion, and late split surgery.

1. `create_project`
2. `register_dataset` with at least one `gold` and one `test` item
3. `upsert_dataset_items` for new batches
4. `assign_split` only for surgical moves or promotions from unlabeled to gold/test

Dataset item conventions:
- Keep model inputs in payload: `source`, `user_prompt`, `candidate_answer`, `user_comment`
- Keep truth in payload: `ground_truth_error_present`, `ground_truth_error_class`, or task-specific labels
- Keep selection/routing hints in tags: `source:...`, `gt:error`, `gt:no_error`, `round:...`

## Add New Unlabeled Tasks

Use this when the user wants to push fresh production cases into the queue without rebuilding the full dataset.

1. `upsert_dataset_items(dataset_id, payload={items:[...]})`
2. Tag them consistently, usually `source:...` and `gt:unlabeled`
3. `run_unannotated(payload={project_id, dataset_id, queue_name, target_ref, target_kind, options})`
4. `inspect_run` to collect predictions and hard negatives for later gold/test expansion

## Update Prompt And Regress On Gold

Use this when a prompt part changes or a new judge instruction is introduced.

1. `create_prompt_part(payload={...})`
2. `create_prompt_config_version(payload={...})`
3. If graph topology changes, `register_graph(payload={...})`
4. `validate_graph(payload={graph_version_id, sample_payload})`
5. `run_gold(payload={...})`
6. If gold is acceptable, `run_test(payload={...})` or `run_all(payload={...})`

Practical rule:
- Do not promote a prompt change straight to `run_all` if gold regresses.

## Multi-Stage Annotation Graph

Use when the user wants coarse detection followed by post-labeling.

Recommended pattern:
1. Base `judge_prompt` or `annotator_prompt`
2. `condition` node on typed output like `error_present == True`
3. Error-only post-labeler nodes
4. Optional `python_function` node to normalize the `no_error` branch

Always validate:
- base judge verdict schema
- post-labeler verdict schema
- branch conditions
- downstream input schemas after merge

## AutoML Round

Use when the user wants a classical baseline or a distilled cheap model.

1. `create_automl_policy(payload={...})`
2. `register_graph(payload={ node_type: classical_automl, automl_policy_id: ... })`
3. `validate_graph(payload={...})`
4. Train on `gold` via policy config `training_split=gold`
5. Score on `test` with `create_task(... split_mode=test ...)` or `run_test`
6. Optionally score on `unannotated` with `run_unannotated`

Recommended initial candidates:
- `majority_class`
- `word_nb`
- `char_nb`

## Graph Selection For Annotation

Use when comparing multiple graph variants for the same dataset.

1. Register each candidate graph as its own graph version
2. Run each graph on the same `gold`
3. Keep only graphs that beat or match the incumbent on the primary metric
4. Break ties by lower cost, lower latency, or simpler topology
5. Retest the shortlisted graph on `test`

Keep graph ids and run ids side by side in the final note.

Prefer storing each candidate graph as a separate payload file and applying it through MCP. That keeps the comparison reproducible and reviewable.

## Distill To ML

Use when the prompt graph is good enough to teach a cheap classifier.

1. Run the prompt graph on `gold` and inspect disagreement
2. Freeze labels in payload under `ground_truth_*`
3. Create a `classical_automl` policy trained on `gold`
4. Register a parallel ML graph
5. Compare prompt graph vs ML graph on `test`
6. If ML is acceptable, keep the prompt graph as teacher and the ML graph as fast path

## Switch Nodes To ML-Only Mode

Use when the user wants part of the graph to stop calling LLMs.

1. Keep the graph contract unchanged if possible
2. Replace prompt node with `classical_automl` node or `python_function`
3. Preserve the same output schema so downstream edges do not need rewriting
4. Re-run `validate_graph`
5. Re-run `run_gold` and `run_test`

## Bootstrap Gold/Test Sufficiency

Use this when deciding whether to keep labeling or stop.

1. Pick the exact run to evaluate
2. Run `scripts/bootstrap_sufficiency.py`
3. Check the half-width of the confidence interval on the primary metric
4. If half-width is too wide, add more labeled cases in the weak area:
   - positive/negative balance for binary detection
   - underrepresented error classes for post-labeling
   - disagreement-heavy segments for routing rules

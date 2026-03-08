# Business Playbooks

Use this file first when the user asks for an operational task. It maps business intent to MCP tools and call order.

Rule:
- execute business workflows through MCP tools
- keep graphs, prompts, and dataset mutations as data payloads
- do not use internal Python service methods as the execution interface

## 1. Create Or Expand Gold/Test Set

Use when the user wants to bootstrap or grow labeled evaluation slices.

Tools:
1. `create_project` if needed
2. `register_dataset` for the first load
3. `upsert_dataset_items` for later additions
4. `assign_split` for promotions or corrections

Data to prepare:
- `external_key`
- `payload` with `user_prompt`, `candidate_answer`, optional `user_comment`
- `ground_truth_*` labels in payload
- `split`
- `tags`

Success condition:
- dataset has both `gold` and `test`
- labels live in payload, not only in comments

## 2. Send New Unlabeled Tasks

Use when the user wants to queue fresh production cases.

Tools:
1. `upsert_dataset_items`
2. `run_unannotated`
3. `inspect_run`

Data to prepare:
- new items with `split=unannotated`
- tags like `source:...` and `gt:unlabeled`

Success condition:
- new run on `unannotated`
- inspected outputs available for review or promotion

## 3. Update Prompt And Regress On Gold

Use when the user changes judge instructions or annotator behavior.

Tools:
1. `create_prompt_part`
2. `create_prompt_config_version`
3. `register_graph` if topology changed
4. `validate_graph`
5. `run_gold`
6. `inspect_run`
7. `run_test` or `run_all` only if gold is acceptable

Success condition:
- new prompt version id recorded
- gold run completed and reviewed before broader rollout

## 4. Expand Graph

Use when the user wants to add nodes, routing, post-labeling, or ML branches.

Tools:
1. `register_graph`
2. `validate_graph`
3. `render_graph_plantuml`
4. `run_gold`
5. `run_test`

Typical graph changes:
- `judge_prompt -> condition -> post-labeler`
- prompt node replaced with `classical_automl`
- extra normalization node on the `no_error` branch

Success condition:
- graph validates
- PlantUML snapshot exists
- gold/test runs complete on the new graph version

## 5. Run Full Promotion Cycle

Use when the user wants standard progression after a graph or prompt update.

Tools:
1. `validate_graph`
2. `run_all`
3. `inspect_run` for child runs
4. `list_runs`

Success condition:
- parent and child runs exist
- `gold`, `test`, and `unannotated` all complete

## 6. Run AutoML Round

Use when the user wants a cheap classical baseline or a distilled model.

Tools:
1. `create_automl_policy`
2. `register_graph` with `node_type=classical_automl`
3. `validate_graph`
4. `create_task` or `run_test` for evaluation
5. `run_unannotated` for cheap batch scoring
6. `inspect_run`

Recommended policy fields:
- `task_type`
- `training_split=gold`
- `label_field`
- `trainer_ref`
- optional candidate list

Success condition:
- model artifact created
- test performance compared against incumbent prompt graph

## 7. Pick Best Graph For Annotation

Use when the user wants graph search or A/B comparison.

Tools:
1. `register_graph` for each candidate
2. `validate_graph` for each candidate
3. `run_gold` for each candidate
4. `inspect_run`
5. `run_test` for the shortlist
6. `render_graph_plantuml`

Comparison rule:
- compare candidates on the same dataset and split
- only promote the same or better graph on the chosen primary metric

Success condition:
- shortlisted graph id and supporting run ids captured

## 8. Distill Prompt Node To ML

Use when the user wants to convert prompt logic into a cheaper ML path.

Tools:
1. `run_gold` and `inspect_run` on the prompt graph
2. freeze labels into `ground_truth_*` fields in dataset payload
3. `create_automl_policy`
4. `register_graph` for the ML student graph
5. `validate_graph`
6. `run_test`
7. compare `inspect_run` outputs between teacher and student

Success condition:
- ML graph is evaluated on the same test slice
- decision recorded: keep teacher only, keep hybrid, or switch branch to ML

## 9. Switch Node Or Branch To ML-Only

Use when the user explicitly wants a process branch to stop calling LLMs.

Tools:
1. `register_graph` with the branch rewritten as `classical_automl` or `python_function`
2. `validate_graph`
3. `run_gold`
4. `run_test`
5. `run_unannotated` if approved

Success condition:
- output schema stays compatible
- test regression is acceptable

## 10. Estimate Whether Gold/Test Is Sufficient

Use when the user asks whether more labeling is needed.

Operational tools:
1. `inspect_run`
2. optionally `list_runs`

Secondary helper:
- `scripts/bootstrap_sufficiency.py`

Interpretation:
- if bootstrap interval is too wide, add more labels before changing prompts or graphs based on weak evidence

Success condition:
- user gets a concrete recommendation: stop, add more positives/negatives, or add more examples for specific classes/segments

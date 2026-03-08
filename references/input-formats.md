# Input Formats

Use the helper `scripts/build_dataset_payload.py` to convert `CSV`, `JSON`, or `JSONL` into MCP-ready dataset calls.

The helper only prepares MCP payloads or plan files. The actual service mutation must still happen through MCP.

## Supported Input Types

- `csv`
- `json` as a list of row objects
- `json` as `{ "items": [...] }`
- `jsonl` / `ndjson`

## Reserved Columns

These columns become MCP item metadata rather than payload fields:
- `external_key`
- `split`
- `tags`
- `attachments`

Everything else becomes payload by default.

## Common Prompt Columns

The helper auto-renames these into the payload shape used by the service:
- `prompt` -> `user_prompt`
- `answer` -> `candidate_answer`
- `response` -> `candidate_answer`
- `comment` -> `user_comment`

Override or add mappings with repeated `--rename old:new`.

## Minimal CSV Example

```csv
external_key,split,tags,source,prompt,answer,comment,ground_truth_error_present
case-001,gold,"source:generate_filters,gt:error",generate_filters,"Нужен DTB в категории электроника YTD 2025","{'metric':['DTB']}","не та дата",true
case-002,test,"source:generate_filters,gt:no_error",generate_filters,"buyers по электронике","{'metric':['buyers'], 'category':['Электроника']}",,false
case-003,unannotated,"source:generate_filters,gt:unlabeled",generate_filters,"конверсия из поиска в контакт","{'metric':['contacts']}",,
```

Build a registration call:

```bash
python3 scripts/build_dataset_payload.py \
  --input ./feedback.csv \
  --mode register \
  --project-id <PROJECT_ID> \
  --dataset-name feedback-generate-filters \
  --description "feedback import" \
  --output-kind plan \
  --output ./register-plan.json
```

Then run it:

```bash
python3 scripts/mcp_plan_runner.py \
  --workspace /path/to/service/workspace \
  --plan-file ./register-plan.json
```

## Minimal JSON Example

```json
[
  {
    "external_key": "case-001",
    "split": "gold",
    "tags": ["source:generate_filters", "gt:error"],
    "source": "generate_filters",
    "prompt": "Нужен DTB в категории электроника YTD 2025",
    "answer": "{'metric':['DTB']}",
    "comment": "не та дата",
    "ground_truth_error_present": true,
    "ground_truth_error_class": "time_window"
  }
]
```

## Prompt-Only CSV Example

If the file contains only prompts and optional ids, omit split to default everything into `unannotated`:

```csv
external_key,source,prompt
prompt-001,generate_filters,"покажи buyers по электронике"
prompt-002,generate_filters,"конверсия из поиска в контакт"
```

Build upsert payload for new unlabeled tasks:

```bash
python3 scripts/build_dataset_payload.py \
  --input ./new-prompts.csv \
  --mode upsert \
  --dataset-id <DATASET_ID> \
  --default-split unannotated \
  --output-kind plan \
  --output ./upsert-prompts-plan.json
```

## Useful Flags

Limit payload fields explicitly:

```bash
--payload-field source \
--payload-field prompt \
--payload-field answer \
--payload-field comment \
--payload-field ground_truth_error_present
```

Rename custom columns:

```bash
--rename query:user_prompt \
--rename completion:candidate_answer \
--rename reviewer_note:user_comment
```

Embed environment for plan execution:

```bash
--env APP_DATABASE_URL=sqlite:////abs/path/demo.db \
--env APP_LOCAL_ARTIFACT_DIR=/abs/path/artifacts
```

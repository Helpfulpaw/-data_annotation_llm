# Plan Format

Use a JSON file to describe ordered MCP calls. Keep graph changes, prompt changes, and run launches in these files instead of embedding them in ad-hoc Python.

## Structure

```json
{
  "env": {
    "APP_DATABASE_URL": "sqlite:////absolute/path/demo.db",
    "APP_ARTIFACT_BACKEND": "filesystem",
    "APP_LOCAL_ARTIFACT_DIR": "/absolute/path/artifacts",
    "APP_RUN_INLINE": "true"
  },
  "calls": [
    {
      "tool": "create_project",
      "arguments": {
        "name": "demo-project",
        "description": "demo"
      },
      "save_as": "project"
    }
  ]
}
```

## Placeholders

Use `{{alias.field}}` placeholders to reference prior call results.

Example:

```json
{
  "tool": "register_dataset",
  "arguments": {
    "payload": {
      "project_id": "{{project.id}}",
      "name": "feedback-demo",
      "items": []
    }
  },
  "save_as": "dataset"
}
```

## Multi-Stage Graph Example

```json
{
  "tool": "register_graph",
  "arguments": {
    "payload": {
      "project_id": "{{project.id}}",
      "graph_name": "multistage-judge",
      "entry_node_key": "base_judge",
      "nodes": [
        {
          "node_key": "base_judge",
          "display_name": "Base Judge",
          "node_type": "judge_prompt",
          "prompt_config_version_id": "{{base_prompt.id}}",
          "adapter_config_id": "{{judge_adapter.id}}",
          "parser_config": {"kind": "json_field", "field": "verdict"},
          "input_schema": {"type": "object"},
          "output_schema": {
            "type": "object",
            "properties": {
              "error_present": {"type": "boolean"},
              "reason": {"type": "string"}
            },
            "required": ["error_present", "reason"]
          },
          "verdict_schema": {
            "type": "object",
            "properties": {
              "error_present": {"type": "boolean"},
              "reason": {"type": "string"}
            },
            "required": ["error_present", "reason"]
          }
        },
        {
          "node_key": "route",
          "display_name": "Route",
          "node_type": "condition",
          "input_schema": {
            "type": "object",
            "properties": {"error_present": {"type": "boolean"}},
            "required": ["error_present"]
          },
          "output_schema": {
            "type": "object",
            "properties": {
              "source": {"type": "string"},
              "user_prompt": {"type": "string"},
              "candidate_answer": {"type": "string"},
              "error_present": {"type": "boolean"},
              "reason": {"type": "string"}
            },
            "required": ["source", "user_prompt", "candidate_answer", "error_present", "reason"]
          }
        }
      ],
      "edges": [
        {"source_node_key": "base_judge", "target_node_key": "route"}
      ]
    }
  },
  "save_as": "graph"
}
```

## Promotion Sequence

Typical plan tail:

1. `validate_graph`
2. `run_gold`
3. `inspect_run`
4. `run_test`
5. `inspect_run`
6. `run_all`
7. `list_runs`

Keep each major phase as a separate call so the outputs can be reused and inspected.

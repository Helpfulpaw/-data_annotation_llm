# Graph Patterns

## 1. Base Judge To Post-Labeler

Use this for `error_present -> error_class` flows.

Pattern:
- `base_judge: judge_prompt`
- `route: condition`
- `no_error: python_function` with a static merge like `error_class=no_error`
- `error_classify: judge_prompt`

Condition expressions:
- `error_present == False`
- `error_present == True`

## 2. Prompt Teacher And ML Student

Use this when the user wants a cheap approximation of a prompt node.

Pattern:
- `teacher_prompt: judge_prompt` or `annotator_prompt`
- offline label freeze into dataset payload
- `student: classical_automl`

Keep the student output schema aligned with the teacher output if the graph may be swapped later.

## 3. Hybrid Fast Path

Use this when ML should handle easy cases and LLM should review hard cases.

Pattern:
- `student: classical_automl`
- `route: condition`
- `accept_fast_path: python_function`
- `escalate_to_llm: judge_prompt`

Typical routing inputs:
- classifier confidence bucket
- predicted error class in a safe subset
- explicit tags like `segment:known-safe`

## 4. Pure ML Mode

Use this when the user explicitly asks to switch a process branch into ML-only mode.

Pattern:
- remove prompt node from that branch
- insert `classical_automl` or `python_function`
- keep the branch output schema stable
- leave a prompt-based teacher graph in parallel for regression testing

## 5. Graph Search

Use when comparing alternative annotation topologies.

Keep changes isolated by axis:
- prompt-only change
- branch/routing change
- post-label taxonomy change
- ML replacement change

Do not compare two graphs that differ in many axes at once if the user wants a clear causal conclusion.

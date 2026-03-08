#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
from pathlib import Path
from typing import Any


def parse_literal(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false", "null"}:
        return json.loads(lowered)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def as_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def get_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def resolve_field(truth_payload: dict[str, Any], pred_payload: dict[str, Any], field: str) -> Any:
    if field.startswith("truth."):
        return get_path(truth_payload, field.removeprefix("truth."))
    if field.startswith("pred."):
        return get_path(pred_payload, field.removeprefix("pred."))
    value = get_path(truth_payload, field)
    if value is not None:
        return value
    return get_path(pred_payload, field)


def confusion(records: list[tuple[Any, Any]], positive_value: Any) -> dict[str, int]:
    tp = tn = fp = fn = 0
    for truth, pred in records:
        truth_pos = truth == positive_value
        pred_pos = pred == positive_value
        if truth_pos and pred_pos:
            tp += 1
        elif truth_pos and not pred_pos:
            fn += 1
        elif not truth_pos and pred_pos:
            fp += 1
        else:
            tn += 1
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn}


def metric_value(records: list[tuple[Any, Any]], metric: str, positive_value: Any) -> float:
    c = confusion(records, positive_value)
    total = c["tp"] + c["tn"] + c["fp"] + c["fn"]
    if total == 0:
        return 0.0
    if metric == "accuracy":
        return (c["tp"] + c["tn"]) / total
    if metric == "precision":
        denom = c["tp"] + c["fp"]
        return c["tp"] / denom if denom else 0.0
    if metric == "recall":
        denom = c["tp"] + c["fn"]
        return c["tp"] / denom if denom else 0.0
    if metric == "specificity":
        denom = c["tn"] + c["fp"]
        return c["tn"] / denom if denom else 0.0
    if metric == "f1":
        precision = metric_value(records, "precision", positive_value)
        recall = metric_value(records, "recall", positive_value)
        return (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    raise ValueError(f"unsupported metric '{metric}'")


def bootstrap_ci(records: list[tuple[Any, Any]], metric: str, positive_value: Any, samples: int, confidence: float, seed: int) -> tuple[float, float, float]:
    rng = random.Random(seed)
    estimates = []
    for _ in range(samples):
        sampled = [records[rng.randrange(len(records))] for _ in range(len(records))]
        estimates.append(metric_value(sampled, metric, positive_value))
    estimates.sort()
    lower_idx = int(((1.0 - confidence) / 2.0) * samples)
    upper_idx = int((1.0 - (1.0 - confidence) / 2.0) * samples) - 1
    lower = estimates[max(0, lower_idx)]
    upper = estimates[min(len(estimates) - 1, upper_idx)]
    point = metric_value(records, metric, positive_value)
    return point, lower, upper


def load_records(db_path: Path, run_id: str, truth_field: str, pred_field: str, where_field: str | None, where_value: Any) -> list[tuple[Any, Any]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute(
        """
        select di.payload, ri.final_output
        from run_items ri
        join dataset_items di on di.id = ri.dataset_item_id
        where ri.run_id = ?
        """,
        (run_id,),
    ).fetchall()
    records: list[tuple[Any, Any]] = []
    for truth_raw, pred_raw in rows:
        truth_payload = as_json(truth_raw) or {}
        pred_payload = as_json(pred_raw) or {}
        if not isinstance(truth_payload, dict) or not isinstance(pred_payload, dict):
            continue
        if where_field is not None:
            where_actual = resolve_field(truth_payload, pred_payload, where_field)
            if where_actual != where_value:
                continue
        truth = resolve_field(truth_payload, pred_payload, truth_field)
        pred = resolve_field(truth_payload, pred_payload, pred_field)
        if truth is None or pred is None:
            continue
        records.append((truth, pred))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap sufficiency estimates for LAN orchestrator runs.")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--truth-field", required=True)
    parser.add_argument("--pred-field", required=True)
    parser.add_argument("--metric", choices=["accuracy", "precision", "recall", "specificity", "f1"], default="accuracy")
    parser.add_argument("--positive-value", default="true")
    parser.add_argument("--where-field")
    parser.add_argument("--where-value")
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--target-half-width", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    positive_value = parse_literal(args.positive_value)
    where_value = parse_literal(args.where_value) if args.where_value is not None else None
    records = load_records(
        Path(args.db_path),
        args.run_id,
        args.truth_field,
        args.pred_field,
        args.where_field,
        where_value,
    )
    if not records:
        raise SystemExit("no comparable records found for the requested fields")

    point, lower, upper = bootstrap_ci(records, args.metric, positive_value, args.samples, args.confidence, args.seed)
    half_width = max(point - lower, upper - point)
    estimated_required_n = len(records)
    if args.target_half_width > 0:
        estimated_required_n = math.ceil(len(records) * (half_width / args.target_half_width) ** 2)

    output = {
        "run_id": args.run_id,
        "metric": args.metric,
        "n": len(records),
        "point_estimate": point,
        "confidence": args.confidence,
        "ci": {"lower": lower, "upper": upper, "half_width": half_width},
        "target_half_width": args.target_half_width,
        "sufficient": half_width <= args.target_half_width,
        "estimated_required_n": estimated_required_n,
        "positive_value": positive_value,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

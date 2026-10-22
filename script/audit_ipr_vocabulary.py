#!/usr/bin/env python3
"""Audit vocabulary overlap between IPR preprocessing and evaluation queries."""

import argparse
import json
import re
from pathlib import Path


def read_queries(path):
    return [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def tokens(text):
    return set(normalize(text).split())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preprocess_vocab", required=True)
    parser.add_argument("--eval_queries", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--require_zero_exact", action="store_true")
    parser.add_argument("--require_zero_phrase_overlap", action="store_true")
    args = parser.parse_args()

    preprocess = read_queries(args.preprocess_vocab)
    evaluation = read_queries(args.eval_queries)
    pre_norm = {normalize(value): value for value in preprocess}
    eval_norm = {normalize(value): value for value in evaluation}
    exact_keys = sorted(set(pre_norm) & set(eval_norm))
    phrase_overlap = []
    for pre_key, pre_value in pre_norm.items():
        for eval_key, eval_value in eval_norm.items():
            if pre_key == eval_key:
                continue
            if pre_key in eval_key or eval_key in pre_key:
                phrase_overlap.append({"preprocess": pre_value, "evaluation": eval_value})
    token_overlap = sorted(
        set().union(*(tokens(value) for value in preprocess))
        & set().union(*(tokens(value) for value in evaluation))
    )
    report = {
        "preprocess_vocabulary_size": len(preprocess),
        "evaluation_query_count": len(evaluation),
        "exact_overlap": [pre_norm[key] for key in exact_keys],
        "phrase_overlap": phrase_overlap,
        "shared_tokens_diagnostic": token_overlap,
        "passes_zero_exact": not exact_keys,
        "passes_zero_phrase_overlap": not phrase_overlap,
        "interpretation": (
            "Exact and phrase overlap are leakage checks. Shared generic tokens are reported as a "
            "diagnostic and do not by themselves imply that evaluation prompts were used."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.require_zero_exact and exact_keys:
        raise SystemExit(2)
    if args.require_zero_phrase_overlap and phrase_overlap:
        raise SystemExit(3)


if __name__ == "__main__":
    main()

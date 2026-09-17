#!/usr/bin/env python3
"""Tiny CPU/GPU smoke test for the training stack (NOT the production 7B run)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "hancock_v1.jsonl"
OUT = ROOT / "outputs" / "hancock-tiny-debug"


def main() -> int:
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
        from trl import SFTTrainer
    except ImportError as exc:
        print(f"[tiny] missing deps: {exc}", file=sys.stderr)
        return 2

    if not DATA.exists():
        print("[tiny] building miniature dataset via pipeline --max-techniques 5")
        from training.pipeline import main as pipe_main

        pipe_main(["--max-techniques", "5"])

    rows = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()][:32]
    model_name = "sshleifer/tiny-gpt2"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model = get_peft_model(
        model,
        LoraConfig(r=4, lora_alpha=8, target_modules=["c_attn"], task_type="CAUSAL_LM"),
    )

    def fmt(ex):
        parts = [f"{m['role']}: {m['content']}" for m in ex["messages"]]
        return {"text": "\n".join(parts)}

    ds = Dataset.from_list(rows).map(fmt)
    OUT.mkdir(parents=True, exist_ok=True)
    targs = TrainingArguments(
        output_dir=str(OUT / "ckpt"),
        per_device_train_batch_size=2,
        max_steps=5,
        logging_steps=1,
        report_to="none",
        learning_rate=1e-4,
    )
    try:
        trainer = SFTTrainer(
            model=model,
            args=targs,
            train_dataset=ds,
            processing_class=tokenizer,
            formatting_func=lambda ex: ex["text"],
        )
    except TypeError:
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            args=targs,
            train_dataset=ds,
            dataset_text_field="text",
            max_seq_length=256,
        )
    trainer.train()
    trainer.model.save_pretrained(OUT)
    print(f"[tiny] ok cuda={torch.cuda.is_available()} -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

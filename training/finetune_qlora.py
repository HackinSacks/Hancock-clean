#!/usr/bin/env python3
"""QLoRA fine-tune Mistral-7B-Instruct-v0.3 for ~12GB VRAM (RTX 5070 class).

Requires: pip install -r requirements-train.txt
Gated model: huggingface-cli login  OR  export HF_TOKEN=...

Blackwell (sm_120): if CUDA kernels missing, install PyTorch CUDA nightly first.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "hancock_v1.jsonl"
DEFAULT_OUT = ROOT / "outputs" / "hancock-lora"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--model", default="mistralai/Mistral-7B-Instruct-v0.3")
    ap.add_argument("--max-seq-length", type=int, default=2048)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--max-steps", type=int, default=-1, help="-1 = full epoch(s)")
    args = ap.parse_args()

    if not args.data.exists():
        print(f"[finetune] missing dataset {args.data}; run: python -m training.pipeline", file=sys.stderr)
        return 2

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
        )
        from trl import SFTTrainer
    except ImportError as exc:
        print(f"[finetune] missing deps: {exc}\nInstall: pip install -r requirements-train.txt", file=sys.stderr)
        return 2

    if not torch.cuda.is_available():
        print(
            "[finetune] CUDA not available. On RTX 5070 (sm_120) you may need a PyTorch nightly CUDA wheel.",
            file=sys.stderr,
        )
        return 3

    print(f"[finetune] GPU: {torch.cuda.get_device_name(0)}")
    print(f"[finetune] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    rows = [json.loads(line) for line in args.data.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"[finetune] loaded {len(rows)} samples from {args.data}")

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    tok_kwargs = {"token": token} if token else {}
    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True, **tok_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb,
        device_map="auto",
        **tok_kwargs,
    )
    model = prepare_model_for_kbit_training(model)

    def to_text(example: dict) -> dict:
        text = tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=False
        )
        return {"text": text}

    ds = Dataset.from_list(rows).map(to_text)
    ds = ds.train_test_split(test_size=0.02, seed=42)

    lora = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_r,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    args.out.mkdir(parents=True, exist_ok=True)
    targs = TrainingArguments(
        output_dir=str(args.out / "checkpoints"),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        learning_rate=args.lr,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        report_to="none",
        gradient_checkpointing=True,
    )

    trainer_kwargs = dict(
        model=model,
        train_dataset=ds["train"],
        eval_dataset=ds["test"],
        peft_config=lora,
        args=targs,
    )
    try:
        trainer = SFTTrainer(
            **trainer_kwargs,
            processing_class=tokenizer,
            formatting_func=lambda ex: ex["text"] if isinstance(ex["text"], str) else ex["text"][0],
        )
    except TypeError:
        trainer = SFTTrainer(
            **trainer_kwargs,
            tokenizer=tokenizer,
            dataset_text_field="text",
            max_seq_length=args.max_seq_length,
        )

    result = trainer.train()
    print(f"[finetune] done loss={getattr(result, 'training_loss', None)}")
    trainer.model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    print(f"[finetune] adapter saved to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

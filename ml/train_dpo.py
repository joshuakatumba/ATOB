"""QLoRA SFT and DPO training script for Civis continuous model improvement."""

import argparse
from pathlib import Path


def run_training(
    stage: str,
    base_model: str,
    dataset_path: Path,
    output_dir: Path,
    epochs: int,
    learning_rate: float,
    batch_size: int,
    max_length: int,
    lora_r: int,
    lora_alpha: int,
) -> None:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import DPOConfig, DPOTrainer, SFTConfig, SFTTrainer

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )

    peft_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )

    dataset = load_dataset("json", data_files=str(dataset_path), split="train")
    output_dir.mkdir(parents=True, exist_ok=True)

    if stage == "sft":
        args = SFTConfig(
            output_dir=str(output_dir),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=learning_rate,
            bf16=True,
            logging_steps=10,
            save_strategy="epoch",
            max_seq_length=max_length,
        )
        trainer = SFTTrainer(
            model=model,
            args=args,
            train_dataset=dataset,
            processing_class=tokenizer,
            peft_config=peft_config,
        )
    else:
        args = DPOConfig(
            output_dir=str(output_dir),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=learning_rate,
            beta=0.1,
            bf16=True,
            logging_steps=10,
            save_strategy="epoch",
            max_length=max_length,
            max_prompt_length=max_length // 2,
        )
        trainer = DPOTrainer(
            model=model,
            args=args,
            train_dataset=dataset,
            processing_class=tokenizer,
            peft_config=peft_config,
        )

    trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Civis SFT or DPO LoRA adapters.")
    parser.add_argument("--stage", choices=["sft", "dpo"], required=True)
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=4096)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    args = parser.parse_args()
    run_training(
        stage=args.stage,
        base_model=args.base_model,
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        batch_size=args.batch_size,
        max_length=args.max_length,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
    )


if __name__ == "__main__":
    main()


# Export LoRA adapter to Ollama

1. Merge adapter into base (on GPU box):

```bash
python - <<'PY'
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
base = "mistralai/Mistral-7B-Instruct-v0.3"
tok = AutoTokenizer.from_pretrained(base)
model = AutoModelForCausalLM.from_pretrained(base, torch_dtype="auto", device_map="cpu")
model = PeftModel.from_pretrained(model, "outputs/hancock-lora")
merged = model.merge_and_unload()
merged.save_pretrained("outputs/hancock-merged")
tok.save_pretrained("outputs/hancock-merged")
print("merged")
PY
```

2. Convert to GGUF (llama.cpp) and quantize `q4_k_m`.

3. Edit `training/Modelfile.template` `FROM` line to your GGUF path.

4. `ollama create hancock -f training/Modelfile.template`

5. Set `OLLAMA_MODEL=hancock` in `.env`.

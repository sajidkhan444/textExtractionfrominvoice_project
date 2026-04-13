"""Model loading utilities."""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

def load_model_and_tokenizer():
    """Load Qwen model and tokenizer."""
    from app.core.constants import MODEL_NAME
    
    print("🔄 Loading Qwen 2.5 3B...")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    print("✅ Qwen Loaded!")
    
    return model, tokenizer
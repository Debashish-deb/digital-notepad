"""Shared helpers for biomedical model microservices."""
from __future__ import annotations

import logging
import os
import time
from typing import Any

LOGGER = logging.getLogger(__name__)

HF_CACHE = os.getenv("HF_HOME", "/models/hf-cache")
LAZY_LOAD = os.getenv("BIOMODEL_LAZY_LOAD", "true").lower() in ("1", "true", "yes")


class ModelHolder:
    """Thread-unsafe lazy holder — one model per service process."""

    def __init__(self, hf_id: str, *, kind: str = "embedding") -> None:
        self.hf_id = hf_id
        self.kind = kind
        self._tokenizer = None
        self._model = None
        self._loaded_at: float | None = None
        self._error: str | None = None

    @property
    def status(self) -> dict[str, Any]:
        return {
            "hf_id": self.hf_id,
            "kind": self.kind,
            "loaded": self._model is not None,
            "loaded_at": self._loaded_at,
            "error": self._error,
        }

    def ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer

            tok = AutoTokenizer.from_pretrained(self.hf_id, cache_dir=HF_CACHE)
            if self.kind == "text-generation":
                model = AutoModelForCausalLM.from_pretrained(
                    self.hf_id,
                    cache_dir=HF_CACHE,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto" if torch.cuda.is_available() else None,
                )
                if not torch.cuda.is_available():
                    model = model.to("cpu")
            else:
                model = AutoModel.from_pretrained(self.hf_id, cache_dir=HF_CACHE)
                model.eval()
                if torch.cuda.is_available():
                    model = model.cuda()
            self._tokenizer = tok
            self._model = model
            self._loaded_at = time.time()
            self._error = None
            LOGGER.info("Loaded model %s", self.hf_id)
        except Exception as exc:
            self._error = str(exc)[:500]
            LOGGER.exception("Failed to load %s", self.hf_id)
            raise

    def embed_texts(self, texts: list[str], *, max_length: int = 512) -> list[list[float]]:
        self.ensure_loaded()
        import torch

        assert self._tokenizer is not None and self._model is not None
        vectors: list[list[float]] = []
        with torch.no_grad():
            for text in texts:
                inputs = self._tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=max_length,
                    padding=True,
                )
                if torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}
                outputs = self._model(**inputs)
                hidden = outputs.last_hidden_state
                mask = inputs["attention_mask"].unsqueeze(-1)
                summed = (hidden * mask).sum(dim=1)
                counts = mask.sum(dim=1).clamp(min=1)
                vec = (summed / counts).squeeze(0).cpu().tolist()
                vectors.append(vec)
        return vectors

    def generate(self, prompt: str, *, max_new_tokens: int = 256) -> str:
        self.ensure_loaded()
        import torch

        assert self._tokenizer is not None and self._model is not None
        inputs = self._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        with torch.no_grad():
            out = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        text = self._tokenizer.decode(out[0], skip_special_tokens=True)
        if text.startswith(prompt):
            return text[len(prompt) :].strip()
        return text.strip()

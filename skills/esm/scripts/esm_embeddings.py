"""Residue-only ESMC embeddings, without loading weights or contacting a service.

Use with esm 3.4.1.post1. Callers supply a loaded model/tokenizer or SDK tensors.
Only nonempty, unaligned, single-chain amino-acid sequences are accepted here.
"""

from collections.abc import Sequence

import torch

AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWYXBZUO")


def validate_sequence(sequence: str) -> None:
    if not isinstance(sequence, str) or not sequence:
        raise ValueError("Expected a nonempty amino-acid sequence")
    if len(sequence) > 2046:
        raise ValueError("ESMC's 2048-token context allows at most 2046 plain residues")
    invalid = set(sequence) - AMINO_ACIDS
    if invalid:
        raise ValueError(f"Unsupported sequence characters: {sorted(invalid)!r}")


def mean_pool_residues(
    hidden: torch.Tensor,
    attention_mask: torch.Tensor,
    special_tokens_mask: torch.Tensor,
) -> torch.Tensor:
    """Pool B,T,D states over actual residues; exclude CLS/EOS/padding.

    Masks must use 0/1 entries. Invalid/padded states are masked before summing,
    so a NaN padding value cannot contaminate a valid sequence embedding.
    """
    if hidden.ndim != 3 or hidden.shape[-1] == 0:
        raise ValueError("Expected nonempty hidden states with shape (B, T, D)")
    if attention_mask.shape != hidden.shape[:2] or special_tokens_mask.shape != hidden.shape[:2]:
        raise ValueError("Masks must match the hidden-state batch and token axes")
    for mask in (attention_mask, special_tokens_mask):
        if not torch.all((mask == 0) | (mask == 1)):
            raise ValueError("Masks must contain only 0 and 1")
    keep = attention_mask.to(hidden.device).bool() & ~special_tokens_mask.to(hidden.device).bool()
    counts = keep.sum(dim=1)
    if torch.any(counts == 0):
        raise ValueError("Each sequence must have at least one residue")
    if not torch.isfinite(hidden[keep]).all():
        raise ValueError("Nonfinite residue embeddings")
    clean = hidden.float().masked_fill(~keep.unsqueeze(-1), 0)
    return clean.sum(dim=1) / counts.unsqueeze(-1)


def embed_sequences(model, tokenizer, sequences: Sequence[str]) -> torch.Tensor:
    """Return CPU (B,D) residue means using the native EsmcForMaskedLM API.

    This is one padded batch. The caller chooses a batch size fitting memory.
    No truncation, implicit sequence cleaning, model loading, or network calls.
    """
    if isinstance(sequences, str) or not sequences:
        raise ValueError("Provide a nonempty collection of sequences")
    for sequence in sequences:
        validate_sequence(sequence)
    if model.training:
        raise ValueError("Put the model in evaluation mode before embedding")
    inputs = tokenizer(
        list(sequences), padding=True, return_tensors="pt",
        return_special_tokens_mask=True, truncation=False,
    )
    special = inputs.pop("special_tokens_mask")
    residue_counts = (inputs["attention_mask"].bool() & ~special.bool()).sum(1)
    if residue_counts.tolist() != [len(sequence) for sequence in sequences]:
        raise ValueError("Tokenizer changed the number of residues")
    device = next(model.parameters()).device
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.inference_mode():
        output = model(**inputs)
        pooled = mean_pool_residues(
            output.last_hidden_state, inputs["attention_mask"], special
        )
    return pooled.cpu()


def sdk_residue_embeddings(
    tokens: torch.Tensor,
    embeddings: torch.Tensor,
    tokenizer,
    sequence_length: int,
) -> torch.Tensor:
    """Extract L,D residues from a single-chain SDK (1,L+2,D) response.

    Reject unexpected layouts instead of silently assigning BOS to residue 1.
    This helper intentionally excludes padded/multichain SDK inputs.
    """
    if sequence_length < 1 or tokens.ndim != 1:
        raise ValueError("Expected a positive sequence length and 1D tokens")
    if tokens.numel() != sequence_length + 2:
        raise ValueError("Expected exactly CLS, L residues, EOS")
    if embeddings.ndim != 3 or embeddings.shape[:2] != (1, tokens.numel()):
        raise ValueError("Expected SDK embeddings with shape (1, L+2, D)")
    if tokens[0].item() != tokenizer.cls_token_id or tokens[-1].item() != tokenizer.eos_token_id:
        raise ValueError("Missing expected CLS/EOS boundary tokens")
    special_ids = set(tokenizer.all_special_ids)
    if any(token in special_ids for token in tokens[1:-1].tolist()):
        raise ValueError("Unexpected special token within sequence")
    residues = embeddings[0, 1:-1].float()
    if not torch.isfinite(residues).all():
        raise ValueError("Nonfinite residue embeddings")
    return residues

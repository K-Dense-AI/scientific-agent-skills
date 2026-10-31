"""Canonical sequon and S/T-density helpers; no occupancy prediction or network calls."""

import math


AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")


def normalize_sequence(sequence: str) -> str:
    """Normalize raw sequence whitespace/case; reject FASTA, gaps and ambiguity."""
    if not isinstance(sequence, str):
        raise TypeError("sequence must be a string of canonical amino acids")
    sequence = "".join(sequence.split())
    if not sequence.isascii():
        raise ValueError("sequence must use ASCII amino-acid letters")
    sequence = sequence.upper()
    if not sequence or set(sequence) - AMINO_ACIDS:
        raise ValueError("provide a nonempty raw sequence using the 20 canonical amino acids")
    return sequence


def _index(sequence: str, position: int, width: int = 1) -> int:
    if isinstance(position, bool) or not isinstance(position, int):
        raise ValueError("position must be a 1-based integer")
    if not 1 <= position <= len(sequence) - width + 1:
        raise ValueError("position must leave enough residues for the complete sequon")
    return position - 1


def find_n_glycosylation_sequons(sequence: str) -> list[dict]:
    """Return overlapping N-X-[ST], X != P, candidates in 1-based coordinates."""
    seq = normalize_sequence(sequence)
    return [
        {
            "position": i + 1,
            "motif": seq[i:i + 3],
            "context": seq[max(0, i - 3):i + 6],
            "sequon_type": "NX" + seq[i + 2],
        }
        for i in range(len(seq) - 2)
        if seq[i] == "N" and seq[i + 1] != "P" and seq[i + 2] in "ST"
    ]


def eliminate_glycosite(sequence: str, position: int, replacement: str = "Q") -> str:
    """Replace the Asn of a canonical sequon, without claiming biological occupancy."""
    seq = normalize_sequence(sequence)
    idx = _index(seq, position, 3)
    replacement = normalize_sequence(replacement)
    if len(replacement) != 1 or replacement == "N":
        raise ValueError("replacement must be one canonical amino acid other than N")
    if not find_n_glycosylation_sequons(seq[idx:idx + 3]):
        raise ValueError("position is not the Asn of a canonical N-glycosylation sequon")
    return seq[:idx] + replacement + seq[idx + 1:]


def add_glycosite(
    sequence: str,
    position: int,
    flanking_context: str = "S",
    *,
    allow_proline_substitution: bool = False,
) -> str:
    """Introduce a complete sequon; P->A at +1 requires explicit opt-in.

    Existing S/T at +2 is preserved. Otherwise +2 becomes flanking_context.
    Up to three residues may change; rescan the entire product for collateral motifs.
    """
    seq = normalize_sequence(sequence)
    idx = _index(seq, position, 3)
    if not isinstance(flanking_context, str) or flanking_context.upper() not in ("S", "T"):
        raise ValueError("flanking_context must be S or T")
    if not isinstance(allow_proline_substitution, bool):
        raise ValueError("allow_proline_substitution must be a boolean")
    if seq[idx + 1] == "P" and not allow_proline_substitution:
        raise ValueError("the +1 Pro requires an explicit P->A substitution decision")
    product = list(seq)
    product[idx] = "N"
    if product[idx + 1] == "P":
        product[idx + 1] = "A"
    if product[idx + 2] not in "ST":
        product[idx + 2] = flanking_context.upper()
    return "".join(product)


def find_st_rich_sites(
    sequence: str, window: int = 7, min_st_fraction: float = 0.4
) -> list[dict]:
    """Describe S/T density at S/T residues; this is not an O-glycosylation score.

    Windows truncate at sequence termini; the denominator is the actual window
    length. Proline at +1 is not an exclusion criterion for O-GalNAc.
    """
    seq = normalize_sequence(sequence)
    if isinstance(window, bool) or not isinstance(window, int) or window < 1 or window % 2 == 0:
        raise ValueError("window must be a positive odd integer")
    if (
        isinstance(min_st_fraction, bool)
        or not isinstance(min_st_fraction, (float, int))
        or not 0 <= min_st_fraction <= 1
        or not math.isfinite(min_st_fraction)
    ):
        raise ValueError("min_st_fraction must be finite and between 0 and 1")
    candidates = []
    half = window // 2
    for i, residue in enumerate(seq):
        if residue not in "ST":
            continue
        start, end = max(0, i - half), min(len(seq), i + half + 1)
        segment = seq[start:end]
        fraction = sum(aa in "ST" for aa in segment) / len(segment)
        if fraction >= min_st_fraction:
            candidates.append({
                "position": i + 1,
                "residue": residue,
                "st_fraction": fraction,
                "window_start": start + 1,
                "window_end": end,
                "segment": segment,
            })
    return candidates


if __name__ == "__main__":
    print(find_n_glycosylation_sequons("NNST"))
    print(find_st_rich_sites("STPST"))

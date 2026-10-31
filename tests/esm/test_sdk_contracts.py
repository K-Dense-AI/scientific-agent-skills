"""CPU and mock-transport checks; no pretrained weights or hosted requests."""
from pathlib import Path
import json
import sys

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("esm")
httpx = pytest.importorskip("httpx")

from esm.models.esmc import EsmcConfig, EsmcForMaskedLM, EsmcTokenizer
from esm.sdk import client, esmc_client, esmfold2_client
from esm.sdk.api import ESMProtein, ESMProteinError, FoldingConfig, GenerationConfig, LogitsConfig
from esm.sdk.forge import ESM3ForgeInferenceClient, ESMCForgeInferenceClient, SequenceStructureForgeInferenceClient
from esm.utils.structure.input_builder import LigandInput, Modification, ProteinInput, StructurePredictionInput
from esm.utils.types import FunctionAnnotation

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "esm"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from esm_embeddings import embed_sequences, mean_pool_residues, sdk_residue_embeddings, validate_sequence


@pytest.fixture(scope="module")
def tiny_model():
    torch.manual_seed(7)
    return EsmcForMaskedLM(EsmcConfig(hidden_size=32, num_attention_heads=4, num_hidden_layers=2)).eval()


@pytest.fixture(scope="module")
def tokenizer():
    return EsmcTokenizer()


def test_native_batch_matches_individual_residue_means(tiny_model, tokenizer):
    sequences = ["MPRT", "AC"]
    together = embed_sequences(tiny_model, tokenizer, sequences)
    separate = torch.cat([embed_sequences(tiny_model, tokenizer, [s]) for s in sequences])
    assert together.shape == (2, 32)
    assert torch.isfinite(together).all()
    torch.testing.assert_close(together, separate, atol=2e-6, rtol=2e-5)


def test_native_hidden_layers_and_attention_axes(tiny_model, tokenizer):
    data = tokenizer(["MPRT", "AC"], padding=True, return_tensors="pt")
    with torch.inference_mode():
        output = tiny_model(**data, output_hidden_states=True, output_attentions=True)
    assert output.logits.shape == (2, 6, 64)
    assert output.hidden_states.shape == (3, 2, 6, 32)
    assert len(output.attentions) == 2
    assert output.attentions[0].shape == (2, 4, 6, 6)
    torch.testing.assert_close(output.hidden_states[-1], output.last_hidden_state)


def test_pooling_excludes_boundary_padding_and_padding_nan():
    hidden = torch.tensor([[[999.0], [2.0], [4.0], [999.0], [float("nan")]]])
    pooled = mean_pool_residues(hidden, torch.tensor([[1, 1, 1, 1, 0]]), torch.tensor([[1, 0, 0, 1, 1]]))
    assert pooled.item() == 3.0
    with pytest.raises(ValueError, match="at least one residue"):
        mean_pool_residues(hidden, torch.zeros(1, 5), torch.ones(1, 5))
    with pytest.raises(ValueError, match="only 0 and 1"):
        mean_pool_residues(hidden, torch.full((1, 5), 2), torch.ones(1, 5))
    with pytest.raises(ValueError, match="Nonfinite"):
        mean_pool_residues(hidden, torch.ones(1, 5), torch.zeros(1, 5))


@pytest.mark.parametrize("sequence", ["", "MPR...", "AC DE", "acde", "AC|DE", "AC_DE", ">id\nACD"])
def test_plain_sequence_rejects_silent_cleanup(sequence):
    with pytest.raises(ValueError):
        validate_sequence(sequence)


def test_sequence_context_limit():
    validate_sequence("A" * 2046)
    with pytest.raises(ValueError, match="2048-token"):
        validate_sequence("A" * 2047)


def test_sdk_boundaries_and_logits_container(tiny_model, tokenizer):
    from esm.models.esmc import ESMC
    with pytest.warns(DeprecationWarning):
        compatibility_model = ESMC(model=tiny_model)
    encoded = compatibility_model.encode(ESMProtein(sequence="MPRT"))
    output = compatibility_model.logits(encoded, LogitsConfig(sequence=True, return_embeddings=True))
    residues = sdk_residue_embeddings(encoded.sequence, output.embeddings, tokenizer, 4)
    assert residues.shape == (4, 32)
    assert output.logits.sequence.shape == (1, 6, 64)
    torch.testing.assert_close(residues.mean(0), embed_sequences(tiny_model, tokenizer, ["MPRT"])[0])
    with pytest.raises(ValueError, match="CLS, L residues, EOS"):
        sdk_residue_embeddings(encoded.sequence, output.embeddings, tokenizer, 3)


def protein_response(sequence):
    return {"outputs": dict(sequence=sequence, secondary_structure=None, sasa=None,
        function=None, coordinates=None, plddt=None, ptm=None, pae=None,
        crmsd=None, globularity=None, interface_ptm=None)}


def test_esm3_actual_transport_payload_and_error_value():
    recorded = []
    def handler(request):
        recorded.append(request)
        if len(recorded) == 1:
            return httpx.Response(200, json={"data": protein_response("MPRTAKAKEND")})
        return httpx.Response(401, json={"message": "synthetic unauthorized"})
    with ESM3ForgeInferenceClient(model="esm3-medium-2024-08", token="test-only", request_timeout=13, max_retry_attempts=1) as remote:
        remote._client = httpx.Client(transport=httpx.MockTransport(handler))
        result = remote.generate(ESMProtein(sequence="MPRT___KEND"), GenerationConfig(track="sequence", num_steps=3))
        assert result.sequence == "MPRTAKAKEND"
        failure = remote.generate(ESMProtein(sequence="MPRT___KEND"), GenerationConfig(track="sequence", num_steps=3))
        assert isinstance(failure, ESMProteinError) and failure.error_code == 401
    request = recorded[0]
    assert str(request.url) == "https://biohub.ai/api/v1/generate"
    assert request.headers["Authorization"] == "Bearer test-only"
    assert request.extensions["timeout"]["read"] == 13
    body = json.loads(request.content)
    assert body["inputs"]["sequence"] == "MPRT___KEND"
    assert body["track"] == "sequence" and body["num_steps"] == 3
    assert body["top_p"] == 1.0 and body["temperature_annealing"] is True


def test_esmc_encode_logits_decode_transport(tokenizer):
    seen = []
    token_ids = tokenizer("ACD")["input_ids"]
    def handler(request):
        body = json.loads(request.content)
        seen.append((request.url.path, body))
        if request.url.path.endswith("/encode"):
            return httpx.Response(200, json={"outputs": {"sequence": token_ids}, "potential_sequence_of_concern": False})
        if request.url.path.endswith("/decode"):
            return httpx.Response(200, json={"outputs": {"sequence": "ACD"}})
        return httpx.Response(200, json={"logits": {"sequence": [[[0.0] * 64] * 5]},
            "embeddings": [[[float(i)] * 4 for i in range(5)]], "hidden_states": None,
            "mean_embedding": None, "mean_hidden_state": None, "sae_outputs": None})
    with ESMCForgeInferenceClient(model="esmc-300m-2024-12", token="test-only", max_retry_attempts=1) as remote:
        remote._client = httpx.Client(transport=httpx.MockTransport(handler))
        encoded = remote.encode(ESMProtein(sequence="ACD"))
        output = remote.logits(encoded, LogitsConfig(sequence=True, return_embeddings=True), return_bytes=False)
        decoded = remote.decode(encoded)
    assert decoded.sequence == "ACD"
    assert output.logits.sequence.shape == (1, 5, 64)
    residues = sdk_residue_embeddings(encoded.sequence, output.embeddings, tokenizer, 3)
    torch.testing.assert_close(residues.mean(0), torch.full((4,), 2.0))
    assert [p for p, _ in seen] == ["/api/v1/encode", "/api/v1/logits", "/api/v1/decode"]
    assert seen[1][1]["inputs"]["sequence"] == token_ids
    assert seen[1][1]["logits_config"]["return_embeddings"] is True


def test_factories_select_distinct_clients_without_network():
    with client(token="test-only", request_timeout=5) as c:
        assert isinstance(c, ESM3ForgeInferenceClient) and c.url == "https://biohub.ai"
    with esmc_client(token="test-only", request_timeout=5) as c:
        assert isinstance(c, ESMCForgeInferenceClient)
    with esmfold2_client(token="test-only", request_timeout=5) as c:
        assert isinstance(c, SequenceStructureForgeInferenceClient)
    with pytest.raises(ValueError):
        client("esmc-300m-2024-12", token="test-only")


def test_folding_serialization_and_unsupported_flags():
    prompt = StructurePredictionInput(sequences=[ProteinInput(id="A", sequence="ACD", modifications=[Modification(position=0, ccd="MSE")])])
    config = FoldingConfig(include_pae=True, include_pair_chains_iptm=True)
    body = SequenceStructureForgeInferenceClient._process_fold_all_atom_request(prompt, config, "esmfold2-fast-2026-05")
    assert body["all_atom_input"]["sequences"][0]["modifications"][0]["position"] == 0
    assert body["num_loops"] == 20 and body["num_sampling_steps"] == 100
    assert body["include_pae"] is True and body["lm_mask_pct"] == 0.1
    assert "include_pair_chains_iptm" not in body  # Released serializer limitation.
    with pytest.raises(ValueError, match="include_distogram"):
        SequenceStructureForgeInferenceClient._process_fold_all_atom_request(prompt, FoldingConfig(include_distogram=True))
    with pytest.raises(TypeError, match="list"):
        LigandInput(id="L", ccd="SAH")
    assert FunctionAnnotation("example", start=1, end=3).to_tuple() == ("example", 1, 3)
    assert len(FunctionAnnotation("example", start=1, end=3)) == 3


def test_fold_endpoint_failure_is_returned():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(400, json={"message": "synthetic invalid input"})
    prompt = StructurePredictionInput(sequences=[ProteinInput(id="A", sequence="ACD")])
    with SequenceStructureForgeInferenceClient(model="esmfold2-fast-2026-05", token="test-only", max_retry_attempts=1) as remote:
        remote._client = httpx.Client(transport=httpx.MockTransport(handler))
        result = remote.fold_all_atom(prompt, config=FoldingConfig(include_pae=True))
    assert isinstance(result, ESMProteinError) and result.error_code == 400
    assert str(requests[0].url) == "https://biohub.ai/api/v1/fold_all_atom"
    body = json.loads(requests[0].content)
    assert body["all_atom_input"]["sequences"][0]["id"] == "A"
    assert body["include_pae"] is True


def test_pdb_single_chain_roundtrip(tmp_path):
    coords = torch.full((2, 37, 3), float("nan"))
    coords[0, :3] = torch.tensor([[0., 0., 0.], [1.4, 0., 0.], [2., 1.3, 0.]])
    coords[1, :3] = torch.tensor([[3., 1.3, 0.], [4.4, 1.3, 0.], [5., 2.6, 0.]])
    protein = ESMProtein(sequence="AG", coordinates=coords)
    path = tmp_path / "two_residues.pdb"
    protein.to_pdb(path)
    restored = ESMProtein.from_pdb(path, chain_id="A")
    assert restored.sequence == "AG" and restored.coordinates.shape == (2, 37, 3)
    torch.testing.assert_close(restored.coordinates[:, :3], coords[:, :3])
    assert "ATOM" in protein.to_pdb_string()


def test_native_tiny_checkpoint_roundtrip(tiny_model, tokenizer, tmp_path):
    tiny_model.save_pretrained(tmp_path)
    restored = EsmcForMaskedLM.from_pretrained(str(tmp_path), device="cpu").eval()
    expected = embed_sequences(tiny_model, tokenizer, ["MPRT"])
    actual = embed_sequences(restored, tokenizer, ["MPRT"])
    torch.testing.assert_close(actual, expected)

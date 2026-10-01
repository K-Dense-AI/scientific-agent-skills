"""Behavioral checks for sequence edits and the public accession lookup contract."""
from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pytest
import requests
import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "glycoengineering"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from glycoengineering_tools import (
    normalize_sequence, find_n_glycosylation_sequons, eliminate_glycosite,
    add_glycosite, find_st_rich_sites,
)
from glytoucan_lookup import lookup_wurcs, ENDPOINT

DemoBlockTests = skill_contract.cli.demo_test_case(SKILL_ROOT, ("glycoengineering_tools.py",))


def test_overlap_and_canonical_constraints():
    sites = find_n_glycosylation_sequons(" nNst\nNPsNAT ")
    assert [(s["position"], s["motif"], s["sequon_type"]) for s in sites] == [
        (1, "NNS", "NXS"), (2, "NST", "NXT"), (8, "NAT", "NXT")]
    assert find_n_glycosylation_sequons("NPSTNN") == []
    assert find_n_glycosylation_sequons("N") == []


@pytest.mark.parametrize("sequence", ["", " \n", ">id\nNST", "NXST", "N-ST", "N1ST", "NUST", "ß"])
def test_invalid_sequences_do_not_shift_or_invent_coordinates(sequence):
    with pytest.raises(ValueError):
        normalize_sequence(sequence)


def test_nonstring_sequence():
    with pytest.raises(TypeError):
        normalize_sequence(None)


@pytest.mark.parametrize("position", [0, -1, 3, 4, 5, True, 1.0, "1"])
def test_mutations_reject_incomplete_or_invalid_positions(position):
    for mutate in (eliminate_glycosite, add_glycosite):
        with pytest.raises(ValueError):
            mutate("NNST", position)


def test_elimination_preserves_overlap_and_length():
    product = eliminate_glycosite("NNST", 1, "q")
    assert product == "QNST"
    assert [s["position"] for s in find_n_glycosylation_sequons(product)] == [2]
    assert eliminate_glycosite("NNST", 2) == "NQST"
    assert [s["position"] for s in find_n_glycosylation_sequons("NQST")] == [1]


@pytest.mark.parametrize("replacement", ["N", "QQ", "X", "", "*"])
def test_elimination_requires_one_valid_changed_residue(replacement):
    with pytest.raises(ValueError):
        eliminate_glycosite("NST", 1, replacement)


@pytest.mark.parametrize("sequence", ["NPST", "NAAT", "ASST"])
def test_elimination_requires_a_canonical_site(sequence):
    with pytest.raises(ValueError):
        eliminate_glycosite(sequence, 1)


def test_addition_requires_explicit_proline_change():
    with pytest.raises(ValueError, match="Pro"):
        add_glycosite("APA", 1, "T")
    assert add_glycosite("APA", 1, "t", allow_proline_substitution=True) == "NAT"
    assert add_glycosite("AAT", 1, "S") == "NAT"
    assert add_glycosite("AAA", 1) == "NAS"


@pytest.mark.parametrize("flank", ["ST", "X", "", 3, None])
def test_addition_rejects_invalid_target_residue(flank):
    with pytest.raises(ValueError):
        add_glycosite("AAA", 1, flank)


def test_addition_rejects_truthy_nonboolean_opt_in():
    with pytest.raises(ValueError):
        add_glycosite("APA", 1, allow_proline_substitution="false")


def test_density_keeps_proline_neighbor_and_terminal_denominator():
    sites = find_st_rich_sites("STPST", window=7)
    assert [s["position"] for s in sites] == [1, 2, 4, 5]
    assert sites[0]["st_fraction"] == 3 / 4
    assert sites[1]["st_fraction"] == 4 / 5
    assert (sites[0]["window_start"], sites[0]["window_end"]) == (1, 4)
    assert find_st_rich_sites("AAAAA") == []
    assert find_st_rich_sites("S", window=1)[0]["st_fraction"] == 1


@pytest.mark.parametrize("window", [0, -1, 2, 4, True, 3.0, "7"])
def test_density_invalid_window_is_not_silently_reset(window):
    with pytest.raises(ValueError):
        find_st_rich_sites("STPST", window=window)


@pytest.mark.parametrize("fraction", [-0.1, 1.1, float("nan"), float("inf"), True, "0.4", 10**500])
def test_density_rejects_invalid_threshold(fraction):
    with pytest.raises(ValueError):
        find_st_rich_sites("STPST", min_st_fraction=fraction)


def response_with(rows):
    response = Mock()
    response.headers = {"Content-Type": "application/sparql-results+json; charset=utf-8"}
    response.json.return_value = {"head": {"vars": ["PrimaryId", "Sequence"]},
                                  "results": {"bindings": rows}}
    return response


def binding(accession="G00055MO", value="WURCS=2.0/example"):
    return {"PrimaryId": {"type": "literal", "value": accession},
            "Sequence": {"type": "literal", "value": value}}


def test_lookup_request_and_response_contract():
    response = response_with([binding(), binding()])
    with patch("glytoucan_lookup.requests.get", return_value=response) as get:
        assert lookup_wurcs("G00055MO") == ["WURCS=2.0/example"]
    args, kwargs = get.call_args
    assert args == (ENDPOINT,)
    assert 'VALUES ?PrimaryId { "G00055MO" }' in kwargs["params"]["query"]
    assert kwargs["params"]["format"] == "application/sparql-results+json"
    assert kwargs["headers"]["Accept"] == "application/sparql-results+json"
    assert kwargs["timeout"] == (10, 45)
    response.raise_for_status.assert_called_once()


def test_no_wurcs_match_is_explicit_empty_list():
    with patch("glytoucan_lookup.requests.get", return_value=response_with([])):
        assert lookup_wurcs("G00055MO") == []


@pytest.mark.parametrize("accession", ["", None, "G00055mo", "G00055MO/", 'G00055MO" } UNION {'])
def test_invalid_accession_does_not_contact_service(accession):
    with patch("glytoucan_lookup.requests.get") as get, pytest.raises(ValueError):
        lookup_wurcs(accession)
    get.assert_not_called()


@pytest.mark.parametrize("rows", [[None], [binding("G00051MO")], [binding(value="")],
                                  [{"PrimaryId": "G00055MO", "Sequence": {}}], {}])
def test_malformed_or_mismatched_bindings_are_not_absence(rows):
    with patch("glytoucan_lookup.requests.get", return_value=response_with(rows)), pytest.raises(ValueError):
        lookup_wurcs("G00055MO")


def test_bad_json_and_http_errors_propagate():
    response = response_with([])
    response.raise_for_status.side_effect = requests.HTTPError("503")
    with patch("glytoucan_lookup.requests.get", return_value=response), pytest.raises(requests.HTTPError):
        lookup_wurcs("G00055MO")
    response.raise_for_status.side_effect = None
    response.json.side_effect = ValueError("bad json")
    with patch("glytoucan_lookup.requests.get", return_value=response), pytest.raises(ValueError):
        lookup_wurcs("G00055MO")


def test_timeouts_and_html_are_not_absence():
    with patch("glytoucan_lookup.requests.get", side_effect=requests.Timeout), pytest.raises(requests.Timeout):
        lookup_wurcs("G00055MO")
    response = response_with([])
    response.headers["Content-Type"] = "text/html"
    with patch("glytoucan_lookup.requests.get", return_value=response), pytest.raises(ValueError):
        lookup_wurcs("G00055MO")

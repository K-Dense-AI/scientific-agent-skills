"""Dependency-free, network-free tests for the generate-image helper CLI."""

from __future__ import annotations

import argparse
import base64
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "generate-image"
SCRIPT = SKILL_ROOT / "scripts" / "generate_image.py"


def load_module():
    """Import the CLI under a unique name so it cannot collide with other skills.

    Bytecode writing is suppressed: a __pycache__ left inside the skill directory
    would ship as an artifact the agent never loads.
    """
    spec = importlib.util.spec_from_file_location("generate_image_skill_cli", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


gi = load_module()


def make_args(**overrides) -> argparse.Namespace:
    defaults = dict(
        prompt="a prompt",
        model=gi.DEFAULT_MODEL,
        output=None,
        input=None,
        n=None,
        aspect_ratio=None,
        resolution=None,
        quality=None,
        output_format=None,
        background=None,
        output_compression=None,
        seed=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# A trimmed stand-in for GET /api/v1/images/models, carrying the shapes that
# matter: enum values, ranges, and a bare capability flag.
CATALOGUE = {
    "google/gemini-3.1-flash-image": {
        "id": "google/gemini-3.1-flash-image",
        "supported_parameters": {
            "aspect_ratio": {"type": "enum", "values": ["1:1", "16:9", "21:9"]},
            "resolution": {"type": "enum", "values": ["512", "1K", "2K", "4K"]},
            "n": {"type": "range", "min": 1, "max": 1},
            "input_references": {"type": "range", "min": 0, "max": 14},
        },
    },
    "openai/gpt-image-2": {
        "id": "openai/gpt-image-2",
        "supported_parameters": {
            "background": {"type": "enum", "values": ["auto", "opaque"]},
            "quality": {"type": "enum", "values": ["auto", "low", "medium", "high"]},
            "n": {"type": "range", "min": 1, "max": 10},
            "input_references": {"type": "range", "min": 0, "max": 16},
        },
    },
    "openai/gpt-image-1": {
        "id": "openai/gpt-image-1",
        "supported_parameters": {
            "background": {"type": "enum", "values": ["auto", "transparent", "opaque"]},
            "n": {"type": "range", "min": 1, "max": 10},
            "input_references": {"type": "range", "min": 0, "max": 16},
        },
    },
    "bytedance-seed/seedream-4.5": {
        "id": "bytedance-seed/seedream-4.5",
        "supported_parameters": {
            "seed": {"type": "boolean"},
            "n": {"type": "range", "min": 1, "max": 10},
            "input_references": {"type": "range", "min": 0, "max": 14},
        },
    },
    "black-forest-labs/flux.2-pro": {
        "id": "black-forest-labs/flux.2-pro",
        "supported_parameters": {
            "seed": {"type": "boolean"},
            "input_references": {"type": "range", "min": 0, "max": 8},
        },
    },
}


class CliSurfaceTests(unittest.TestCase):
    def test_help_exits_zero(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--help"],
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("usage:", completed.stdout.lower())

    def test_missing_prompt_is_an_error(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT)],
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("prompt is required", completed.stderr)

    def test_dry_run_prints_the_payload_without_network_or_key(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "a cat", "--aspect-ratio", "16:9",
             "--no-preflight", "--dry-run"],
            text=True, capture_output=True, timeout=20, check=False,
            env={**os.environ, "OPENROUTER_API_KEY": ""},
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"aspect_ratio": "16:9"', completed.stdout)
        self.assertIn("nothing billed", completed.stdout)

    def test_size_flag_is_gone(self):
        """The bundled CLI rejects unsupported flags before making a request."""
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "a cat", "--size", "2048x2048",
             "--no-preflight", "--dry-run"],
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("unrecognized arguments", completed.stderr)

    def test_output_format_does_not_offer_svg(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "a cat", "--output-format", "svg",
             "--no-preflight", "--dry-run"],
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid choice", completed.stderr)

    def test_out_of_range_compression_is_rejected_locally(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "a cat", "--output-compression", "150",
             "--no-preflight", "--dry-run"],
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("between 0 and 100", completed.stderr)

    def test_targets_the_images_endpoint_not_chat_completions(self):
        self.assertEqual(gi.IMAGES_URL, "https://openrouter.ai/api/v1/images")
        self.assertEqual(gi.MODELS_URL, "https://openrouter.ai/api/v1/images/models")
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("chat/completions", source)
        self.assertNotIn("modalities", source)

    def test_uses_only_the_standard_library(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for third_party in ("import requests", "import httpx", "from requests"):
            self.assertNotIn(third_party, source)


class ApiKeyResolutionTests(unittest.TestCase):
    def test_explicit_key_wins(self):
        self.assertEqual(gi.find_api_key("explicit-key"), "explicit-key")

    def test_environment_variable_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                os.environ["OPENROUTER_API_KEY"] = "env-key"
                self.assertEqual(gi.find_api_key(None), "env-key")
            finally:
                os.environ.pop("OPENROUTER_API_KEY", None)
                os.chdir(previous)

    def test_dotenv_is_read_when_environment_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".env").write_text(
                "# comment\nOTHER=1\nOPENROUTER_API_KEY=\"dotenv-key\"\n", encoding="utf-8"
            )
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                os.environ.pop("OPENROUTER_API_KEY", None)
                self.assertEqual(gi.find_api_key(None), "dotenv-key")
            finally:
                os.chdir(previous)

    def test_dotenv_export_prefix_is_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".env").write_text(
                "export OPENROUTER_API_KEY=exported-key\n", encoding="utf-8"
            )
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                os.environ.pop("OPENROUTER_API_KEY", None)
                self.assertEqual(gi.find_api_key(None), "exported-key")
            finally:
                os.chdir(previous)

    def test_absent_key_raises_with_guidance(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                os.environ.pop("OPENROUTER_API_KEY", None)
                with self.assertRaises(gi.ApiError) as caught:
                    gi.find_api_key(None)
                self.assertIn("OPENROUTER_API_KEY", str(caught.exception))
            finally:
                os.chdir(previous)


class PayloadTests(unittest.TestCase):
    def test_unset_parameters_are_omitted(self):
        payload = gi.build_payload(make_args())
        self.assertEqual(set(payload), {"model", "prompt"})

    def test_set_parameters_are_included(self):
        payload = gi.build_payload(make_args(aspect_ratio="16:9", seed=42, n=3))
        self.assertEqual(payload["aspect_ratio"], "16:9")
        self.assertEqual(payload["seed"], 42)
        self.assertEqual(payload["n"], 3)
        self.assertNotIn("quality", payload)

    def test_zero_seed_survives_omission_filtering(self):
        payload = gi.build_payload(make_args(seed=0))
        self.assertEqual(payload["seed"], 0)

    def test_references_use_the_input_references_shape(self):
        payload = gi.build_payload(make_args(input=["https://example.com/a.png"]))
        self.assertEqual(
            payload["input_references"],
            [{"type": "image_url", "image_url": {"url": "https://example.com/a.png"}}],
        )

    def test_printed_payload_shortens_base64_references(self):
        blob = "data:image/png;base64," + "A" * 500
        payload = {"model": "m", "prompt": "p",
                   "input_references": [{"type": "image_url", "image_url": {"url": blob}}]}
        shown = gi.redacted_payload(payload)
        url = shown["input_references"][0]["image_url"]["url"]
        self.assertLess(len(url), 80)
        self.assertIn("chars of base64", url)
        # The original is untouched, so the request still carries the real bytes.
        self.assertEqual(payload["input_references"][0]["image_url"]["url"], blob)


class PreflightTests(unittest.TestCase):
    """The check that turns per-model parameter rules into free local errors."""

    def test_valid_request_passes(self):
        payload = gi.build_payload(make_args(aspect_ratio="16:9", resolution="2K"))
        gi.preflight(payload, CATALOGUE)

    def test_unsupported_parameter_is_caught(self):
        payload = gi.build_payload(make_args(seed=42))
        with self.assertRaises(gi.RequestRejected) as caught:
            gi.preflight(payload, CATALOGUE)
        self.assertIn("seed is not supported", str(caught.exception))

    def test_value_outside_the_model_enum_is_caught(self):
        payload = gi.build_payload(
            make_args(model="openai/gpt-image-2", background="transparent")
        )
        with self.assertRaises(gi.RequestRejected) as caught:
            gi.preflight(payload, CATALOGUE)
        message = str(caught.exception)
        self.assertIn("background=transparent is not allowed", message)
        self.assertIn("auto, opaque", message)

    def test_n_above_the_model_maximum_is_caught(self):
        payload = gi.build_payload(make_args(n=4))
        with self.assertRaises(gi.RequestRejected) as caught:
            gi.preflight(payload, CATALOGUE)
        self.assertIn("exceeds this model's maximum of 1", str(caught.exception))

    def test_too_many_reference_images_are_caught(self):
        payload = gi.build_payload(
            make_args(model="black-forest-labs/flux.2-pro",
                      input=[f"https://e.com/{i}.png" for i in range(9)])
        )
        with self.assertRaises(gi.RequestRejected) as caught:
            gi.preflight(payload, CATALOGUE)
        self.assertIn("accepts at most 8", str(caught.exception))

    def test_every_problem_is_reported_at_once(self):
        payload = gi.build_payload(make_args(aspect_ratio="3:2", seed=1, n=9))
        with self.assertRaises(gi.RequestRejected) as caught:
            gi.preflight(payload, CATALOGUE)
        self.assertIn("3 problems", str(caught.exception))

    def test_unknown_model_suggests_close_matches(self):
        payload = gi.build_payload(make_args(model="google/gemini-3.1-flash-imag"))
        with self.assertRaises(gi.RequestRejected) as caught:
            gi.preflight(payload, CATALOGUE)
        self.assertIn("google/gemini-3.1-flash-image", str(caught.exception))

    def test_suggestions_name_a_model_that_accepts_the_value(self):
        payload = gi.build_payload(
            make_args(model="openai/gpt-image-2", background="transparent")
        )
        with self.assertRaises(gi.RequestRejected):
            gi.preflight(payload, CATALOGUE)
        supporting = gi.models_supporting(CATALOGUE, "background", "transparent")
        self.assertIn("openai/gpt-image-1", supporting)
        self.assertNotIn("openai/gpt-image-2", supporting)

    def test_suggestions_skip_undocumented_families(self):
        """FLUX is in the live catalogue but outside this skill's documented set."""
        supporting = gi.models_supporting(CATALOGUE, "seed")
        self.assertIn("bytedance-seed/seedream-4.5", supporting)
        self.assertNotIn("black-forest-labs/flux.2-pro", supporting)


class SpecDescriptionTests(unittest.TestCase):
    def test_enum_lists_its_values(self):
        self.assertEqual(
            gi.describe_spec({"type": "enum", "values": ["1K", "2K"]}), "1K, 2K"
        )

    def test_range_shows_its_bounds(self):
        self.assertEqual(gi.describe_spec({"type": "range", "min": 0, "max": 16}), "0-16")

    def test_bare_capability_reads_as_supported(self):
        self.assertEqual(gi.describe_spec({"type": "boolean"}), "supported")


class RetryTests(unittest.TestCase):
    def test_retry_after_header_is_honoured(self):
        self.assertEqual(gi.retry_delay("7", 0), 7.0)

    def test_absurd_retry_after_is_capped(self):
        self.assertEqual(gi.retry_delay("99999", 0), 60.0)

    def test_unparsable_retry_after_falls_back_to_backoff(self):
        self.assertEqual(gi.retry_delay("in a bit", 2), 4.0)

    def test_backoff_grows(self):
        self.assertEqual([gi.retry_delay(None, i) for i in range(3)], [1.0, 2.0, 4.0])

    def test_only_transient_statuses_retry(self):
        self.assertIn(429, gi.RETRY_STATUS)
        self.assertIn(503, gi.RETRY_STATUS)
        self.assertNotIn(400, gi.RETRY_STATUS)
        self.assertNotIn(401, gi.RETRY_STATUS)


class ErrorMessageTests(unittest.TestCase):
    def test_bad_request_points_at_model_info(self):
        detail = gi.error_detail(400, '{"error": {"message": "unsupported parameter"}}')
        self.assertIn("unsupported parameter", detail)
        self.assertIn("--model-info", detail)

    def test_auth_failure_mentions_the_key_and_content_policy(self):
        detail = gi.error_detail(403, '{"error": {"message": "forbidden"}}')
        self.assertIn("openrouter.ai/keys", detail)
        self.assertIn("content-policy", detail)

    def test_non_json_body_is_passed_through(self):
        self.assertIn("gateway timeout", gi.error_detail(504, "gateway timeout"))


class CostReportingTests(unittest.TestCase):
    def test_reports_the_billed_cost(self):
        lines = gi.cost_lines({"cost": 0.0672})
        self.assertEqual(lines[0], "Cost: $0.0672")

    def test_byok_upstream_cost_is_not_reported_as_free(self):
        """usage.cost is 0 on a BYOK key; the real spend is upstream."""
        lines = gi.cost_lines(
            {"cost": 0, "is_byok": True,
             "cost_details": {"upstream_inference_cost": 0.03360275}}
        )
        self.assertIn("$0.03360275", lines[0])
        self.assertIn("BYOK", lines[0])

    def test_genuinely_free_generation_says_so(self):
        self.assertEqual(gi.cost_lines({"cost": 0}), ["Cost: $0 reported"])

    def test_image_tokens_are_reported_when_present(self):
        lines = gi.cost_lines(
            {"cost": 0.0672, "completion_tokens_details": {"image_tokens": 1120}}
        )
        self.assertIn("Image tokens: 1120", lines)

    def test_missing_usage_reports_nothing(self):
        self.assertEqual(gi.cost_lines({}), [])

    def test_cost_never_prints_in_scientific_notation(self):
        self.assertEqual(gi.format_cost(3e-05), "0.00003")
        self.assertEqual(gi.format_cost(0.3), "0.3")


class ReferenceEncodingTests(unittest.TestCase):
    def test_urls_and_data_urls_pass_through(self):
        for value in ("https://e.com/a.png", "http://e.com/a.png", "data:image/png;base64,AAA"):
            self.assertEqual(gi.encode_reference(value), value)

    def test_local_file_becomes_a_data_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pic.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
            encoded = gi.encode_reference(str(path))
            self.assertTrue(encoded.startswith("data:image/png;base64,"))
            self.assertEqual(
                base64.b64decode(encoded.split(",", 1)[1]), b"\x89PNG\r\n\x1a\nfake"
            )

    def test_jpeg_extension_maps_to_jpeg_mime(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pic.jpg"
            path.write_bytes(b"jpegbytes")
            self.assertTrue(gi.encode_reference(str(path)).startswith("data:image/jpeg;base64,"))

    def test_missing_file_raises(self):
        with self.assertRaises(gi.ApiError):
            gi.encode_reference("/nonexistent/nope.png")

    def test_unsupported_extension_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pic.tiff"
            path.write_bytes(b"x")
            with self.assertRaises(gi.ApiError):
                gi.encode_reference(str(path))


class OutputPathTests(unittest.TestCase):
    def test_default_name_follows_media_type(self):
        self.assertEqual(gi.output_paths(None, "image/png", 1), [Path("generated_image.png")])
        self.assertEqual(gi.output_paths(None, "image/svg+xml", 1), [Path("generated_image.svg")])
        self.assertEqual(gi.output_paths(None, "image/jpeg", 1), [Path("generated_image.jpg")])

    def test_unknown_media_type_falls_back_to_png(self):
        self.assertEqual(gi.output_paths(None, "image/unheard-of", 1), [Path("generated_image.png")])

    def test_media_type_parameters_are_ignored(self):
        self.assertEqual(gi.output_paths(None, "IMAGE/PNG; charset=binary", 1),
                         [Path("generated_image.png")])

    def test_explicit_output_is_respected(self):
        self.assertEqual(gi.output_paths("art.png", "image/png", 1), [Path("art.png")])

    def test_multiple_images_are_numbered(self):
        self.assertEqual(
            gi.output_paths("out.png", "image/png", 3),
            [Path("out_1.png"), Path("out_2.png"), Path("out_3.png")],
        )

    def test_jpeg_spelling_is_not_a_mismatch(self):
        """`-o out.jpeg` names an image/jpeg response correctly, so say nothing."""
        self.assertEqual(gi.acceptable_suffixes("image/jpeg"), {".jpg", ".jpeg"})


class SaveImageTests(unittest.TestCase):
    def test_saves_base64_payload(self):
        payload = base64.b64encode(b"imagebytes").decode("ascii")
        response = {"data": [{"b64_json": payload, "media_type": "image/png"}]}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.png"
            written = gi.save_images(response, str(target))
            self.assertEqual(written, [target])
            self.assertEqual(target.read_bytes(), b"imagebytes")

    def test_creates_missing_parent_directories(self):
        payload = base64.b64encode(b"x").decode("ascii")
        response = {"data": [{"b64_json": payload, "media_type": "image/png"}]}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "dir" / "out.png"
            gi.save_images(response, str(target))
            self.assertTrue(target.is_file())

    def test_numbering_has_no_gaps_when_an_entry_is_empty(self):
        good = base64.b64encode(b"x").decode("ascii")
        response = {"data": [
            {"b64_json": good, "media_type": "image/png"},
            {"media_type": "image/png"},
            {"b64_json": good, "media_type": "image/png"},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.png"
            written = gi.save_images(response, str(target))
            self.assertEqual([p.name for p in written], ["out_1.png", "out_2.png"])

    def test_empty_data_raises(self):
        with self.assertRaises(gi.ApiError):
            gi.save_images({"data": []}, None)

    def test_entries_without_any_image_data_raise(self):
        with self.assertRaises(gi.ApiError):
            gi.save_images({"data": [{"media_type": "image/png"}]}, None)

    def test_non_https_url_in_a_response_is_refused(self):
        """The URL comes from the response, not the caller, so it is not trusted."""
        with self.assertRaises(gi.ApiError) as caught:
            gi.image_bytes({"url": "http://evil.example/x.png"}, 5.0)
        self.assertIn("non-HTTPS", str(caught.exception))

    def test_downloaded_images_are_size_capped(self):
        self.assertGreater(gi.MAX_DOWNLOAD_BYTES, 0)


class SkillDocumentTests(unittest.TestCase):
    def test_frontmatter_version_matches_expected(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(text, r'\n  version: "\d+\.\d+"\n')

    def test_documented_default_model_matches_the_script(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(gi.DEFAULT_MODEL, text)

    def test_reference_file_is_present(self):
        self.assertTrue((SKILL_ROOT / "references" / "models.md").is_file())

    def test_documentation_does_not_promise_a_size_parameter(self):
        for name in ("SKILL.md", "references/models.md"):
            with self.subTest(document=name):
                text = (SKILL_ROOT / name).read_text(encoding="utf-8")
                for disclaimer in ("There is no `--size`", "has no `--size`"):
                    text = text.replace(disclaimer, "")
                self.assertNotIn("--size", text)

    def test_transparent_background_is_not_offered_on_models_that_refuse_it(self):
        """gpt-image-2 allows only auto and opaque; recommending it wastes a call."""
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            # `$ ...` lines demonstrate the rejection itself, and prose that says
            # the combination is unavailable is the warning, not a recommendation.
            if stripped.startswith("$ ") or "not available" in stripped:
                continue
            if "--background transparent" in stripped:
                self.assertNotIn("gpt-image-2", stripped)

    def test_text_and_integrity_caveats_are_documented(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("never evidence", text)
        self.assertIn("cannot be trusted with text", text)


if __name__ == "__main__":
    unittest.main()

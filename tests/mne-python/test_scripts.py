"""Tests for the mne-python skill's bundled scripts.

The helper tests need only the standard library (plus NumPy for the numerical
helpers). The pipeline tests need MNE and run every CLI end to end on simulated
recordings whose ground truth is known -- injected bad channels, blinks, a P3
that is larger for targets, a 10 Hz alpha rhythm -- so they check that each
script recovers the right answer, not merely that it exits cleanly.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import skill_contract

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "mne-python"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _common  # noqa: E402

CliHelpTests = skill_contract.cli.help_test_case(SKILL_ROOT)


def run(script: str, *args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    environment = {**os.environ, "MPLBACKEND": "Agg", "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=environment,
        timeout=900,
    )
    if check and result.returncode != 0:
        pytest.fail(f"{script} {' '.join(args)} exited {result.returncode}:\n{result.stderr}")
    return result


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------


class TestChannelNames:
    @pytest.mark.parametrize(
        ("raw", "clean"),
        [
            ("EEG FP1-REF", "FP1"),
            ("EEG T3-LE", "T3"),
            ("Fp1-A1", "Fp1"),
            ("Fc5.", "Fc5"),
            ("Cz..", "Cz"),
            ("Fp1-F7", "Fp1-F7"),  # bipolar derivation: untouched
            ("Cz", "Cz"),
        ],
    )
    def test_clean_channel_name(self, raw: str, clean: str) -> None:
        assert _common.clean_channel_name(raw) == clean

    @pytest.mark.parametrize(
        ("name", "kind"),
        [
            ("VEOG", "eog"),
            ("HEOG", "eog"),
            ("EOG ROC-REF", "eog"),
            ("LOC", "eog"),
            ("EKG", "ecg"),
            ("ECG1", "ecg"),
            ("EMG chin", "emg"),
            ("Status", "stim"),
            ("STI 014", "stim"),
            ("TRIGGER", "stim"),
            ("GSR", "gsr"),
            ("Resp", "resp"),
            ("Temp", "temperature"),
            ("Fp1", None),
            ("E1", None),  # EGI electrode, not AASM EOG
            ("E128", None),
        ],
    )
    def test_suggest_channel_type(self, name: str, kind: str | None) -> None:
        assert _common.suggest_channel_type(name) == kind

    def test_match_montage_names(self) -> None:
        montage = ["Fp1", "Cz", "T3", "FC5", "Pz"]
        renames, unmatched = _common.match_montage_names(
            ["FP1", "EEG T3-REF", "Fc5.", "Pz", "XYZ", "Cz", "cz"], montage
        )
        assert renames == {"FP1": "Fp1", "EEG T3-REF": "T3", "Fc5.": "FC5"}
        # 'Cz' and 'cz' would collapse onto one montage name: neither is trusted.
        assert sorted(unmatched) == ["Cz", "XYZ", "cz"]


class TestParsers:
    def test_parse_window(self) -> None:
        window = _common.parse_window("P3=0.30:0.50:pos")
        assert (window.name, window.tmin, window.tmax, window.polarity) == ("P3", 0.3, 0.5, "pos")
        assert _common.parse_window("N1=0.08:0.14").polarity == "abs"

    @pytest.mark.parametrize("text", ["P3=0.5:0.3", "P3=0.3:0.5:up", "N1=80:120", "P3", "=0.1:0.2"])
    def test_parse_window_rejects(self, text: str) -> None:
        with pytest.raises(_common.CliError):
            _common.parse_window(text)

    def test_parse_condition_keeps_label_spacing(self) -> None:
        name, labels = _common.parse_condition("target=Stimulus/S  2|Stimulus/S  3")
        assert name == "target"
        assert labels == ["Stimulus/S  2", "Stimulus/S  3"]

    def test_split_contrast_with_hyphenated_names(self) -> None:
        known = {"go-left", "go-right"}
        assert _common.split_contrast("go-left-go-right", known) == ("go-left", "go-right")
        with pytest.raises(_common.CliError):
            _common.split_contrast("go-left-stop", known)

    def test_parse_band_group_mapping(self) -> None:
        assert _common.parse_band("alpha=8:13") == ("alpha", 8.0, 13.0)
        assert _common.parse_group("roi=P3, Pz,P4", what="--roi") == ("roi", ["P3", "Pz", "P4"])
        assert _common.parse_mapping("VEOG=eog, ECG=ecg", what="x") == {"VEOG": "eog", "ECG": "ecg"}
        for bad in ("alpha=13:8", "alpha", "alpha=a:b"):
            with pytest.raises(_common.CliError):
                _common.parse_band(bad)
        with pytest.raises(_common.CliError):
            _common.parse_mapping("VEOG", what="x")

    @pytest.mark.parametrize(
        ("text", "value"), [("auto", "auto"), ("0", None), ("off", None), ("150", 150.0)]
    )
    def test_parse_threshold_uv(self, text: str, value: object) -> None:
        assert _common.parse_threshold_uv(text, what="x") == value

    @pytest.mark.parametrize("text", ["-5", "abc"])
    def test_parse_threshold_uv_rejects(self, text: str) -> None:
        with pytest.raises(_common.CliError):
            _common.parse_threshold_uv(text, what="x")

    @pytest.mark.parametrize(
        ("name", "stem"),
        [
            ("sub-01_task-oddball_eeg.edf", "sub-01_task-oddball"),
            ("sim_desc-clean_eeg.fif", "sim"),
            ("recording_raw.fif", "recording"),
            ("odd name (1).vhdr", "odd_name_1"),
        ],
    )
    def test_recording_stem(self, name: str, stem: str) -> None:
        assert _common.recording_stem(Path(name)) == stem

    def test_prepare_outputs_refuses_to_overwrite(self, tmp_path: Path) -> None:
        target = tmp_path / "out.json"
        target.write_text("{}", encoding="utf-8")
        with pytest.raises(_common.CliError, match="--overwrite"):
            _common.prepare_outputs(tmp_path, [target], overwrite=False)
        _common.prepare_outputs(tmp_path, [target], overwrite=True)

    def test_checked_input_rejects_urls(self) -> None:
        with pytest.raises(_common.CliError):
            _common.checked_input("https://example.org/recording.edf")


@pytest.fixture
def np():
    return pytest.importorskip("numpy", reason="numerical helpers need numpy")


class TestNumericalHelpers:
    def test_units_verdict(self, np) -> None:
        assert _common.units_verdict(1e-5)["status"] == "plausible"
        stored_uv = _common.units_verdict(10.0)
        assert stored_uv["status"] == "too_large" and stored_uv["suggested_scale"] == pytest.approx(1e-6)
        stored_mv = _common.units_verdict(0.02)
        assert stored_mv["status"] == "too_large" and stored_mv["suggested_scale"] == pytest.approx(1e-3)
        assert _common.units_verdict(1e-11)["suggested_scale"] == pytest.approx(1e6)
        assert _common.units_verdict(None)["status"] == "unknown"

    def test_robust_statistics(self, np) -> None:
        rng = np.random.default_rng(0)
        data = rng.normal(0, 2.0, (3, 20000))
        assert _common.robust_std(data, axis=1) == pytest.approx([2.0] * 3, rel=0.05)
        assert _common.robust_z([1.0, 1.0, 1.0]).tolist() == [0.0, 0.0, 0.0]
        values = np.r_[np.full(50, 100.0), 1000.0]
        ceiling = _common.robust_ceiling(values)
        assert 150.0 <= ceiling < 1000.0  # the ratio floor keeps all clean values

    def test_line_noise_db(self, np) -> None:
        freqs = np.arange(0, 100, 0.25)
        psd = np.ones_like(freqs)
        psd[np.abs(freqs - 50) < 0.3] = 100.0
        assert _common.line_noise_db(freqs, psd, 50.0) == pytest.approx(20.0)
        assert _common.line_noise_db(freqs, psd, 60.0) == pytest.approx(0.0)


# --------------------------------------------------------------------------
# End-to-end pipelines on simulated recordings (need MNE)
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mne():
    module = pytest.importorskip("mne", reason="pipeline tests need MNE-Python")
    module.set_log_level("ERROR")
    return module


@pytest.fixture(scope="module")
def workdir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("mne_python")


@pytest.fixture(scope="module")
def simulated(mne, workdir: Path) -> dict:
    run("simulate_eeg.py", "--out", "sim_raw.fif", "--seed", "7", cwd=workdir)
    truth = json.loads((workdir / "sim_raw_truth.json").read_text(encoding="utf-8"))
    return {"path": workdir / "sim_raw.fif", "truth": truth}


@pytest.fixture(scope="module")
def preprocessed(simulated: dict, workdir: Path) -> dict:
    run("preprocess_eeg.py", "sim_raw.fif", "--out-dir", "pre", cwd=workdir)
    log = json.loads((workdir / "pre" / "sim_desc-preproc_log.json").read_text(encoding="utf-8"))
    return {"clean": workdir / "pre" / "sim_desc-clean_eeg.fif", "log": log}


@pytest.fixture(scope="module")
def erp(preprocessed: dict, workdir: Path) -> dict:
    result = run(
        "erp_analysis.py", str(preprocessed["clean"]), "--out-dir", "erp",
        "--condition", "standard=standard", "--condition", "target=target",
        "--roi", "parietal=P3,Pz,P4", "--channels", "Cz,Pz",
        "--window", "N1=0.08:0.14:neg", "--window", "P3=0.25:0.45:pos",
        "--contrast", "target-standard", "--single-trial", "--report",
        cwd=workdir,
    )
    out = workdir / "erp"
    return {
        "stdout": result.stdout,
        "dir": out,
        "rows": read_csv(out / "sim_erp_measures.csv"),
        "summary": json.loads((out / "sim_erp_summary.json").read_text(encoding="utf-8")),
    }


def measure(rows: list[dict], source: str, roi: str, window: str) -> dict:
    (row,) = [r for r in rows if (r["source"], r["roi"], r["window"]) == (source, roi, window)]
    return row


class TestSimulation:
    def test_recording_matches_truth(self, mne, simulated: dict) -> None:
        raw = mne.io.read_raw(simulated["path"], preload=True)
        truth = simulated["truth"]
        assert raw.get_channel_types().count("eeg") == 32
        assert raw.get_channel_types(picks=["VEOG"]) == ["eog"]
        labels = list(raw.annotations.description)
        assert labels.count("target") == truth["events"]["counts"]["target"]
        assert labels.count("standard") == truth["events"]["counts"]["standard"]
        assert truth["bad_channels"] == {"FC5": "noisy", "T8": "flat"}
        assert 1e-6 < raw.get_data(picks="Cz").std() < 1e-4  # volts, scalp-EEG scale

    def test_rejects_unknown_extension(self, workdir: Path) -> None:
        result = run("simulate_eeg.py", "--out", "x.txt", cwd=workdir, check=False)
        assert result.returncode == 2 and "--out must end with" in result.stderr


class TestInspect:
    def test_flags_injected_faults(self, simulated: dict, workdir: Path) -> None:
        result = run("inspect_recording.py", "sim_raw.fif", "--format", "json", cwd=workdir)
        report = json.loads(result.stdout)
        quality = report["quality"]
        assert quality["flat_channels"] == ["T8"]
        assert quality["extreme_channels"] == ["FC5"]
        assert quality["units_check"]["status"] == "plausible"
        assert quality["line_noise"]["detected_hz"] == 50
        assert report["montage"]["with_positions"] == 32
        assert report["montage"]["best_matches"][0]["matched"] == 32
        assert report["events"]["annotation_labels"] == simulated["truth"]["events"]["counts"]
        assert "sim_raw.fif" == report["file"]["name"]
        assert str(workdir) not in result.stdout  # no absolute paths leak

    def test_detects_microvolts_stored_as_volts(self, mne, workdir: Path) -> None:
        run("simulate_eeg.py", "--out", "uv_raw.fif", "--microvolts-as-volts", cwd=workdir)
        result = run("inspect_recording.py", "uv_raw.fif", "--format", "json", cwd=workdir)
        units = json.loads(result.stdout)["quality"]["units_check"]
        assert units["status"] == "too_large"
        assert units["suggested_scale"] == pytest.approx(1e-6)

    def test_edf_names_types_and_montage(self, mne, simulated: dict, workdir: Path) -> None:
        pytest.importorskip("edfio", reason="EDF export needs edfio")
        raw = mne.io.read_raw(simulated["path"], preload=True)
        old = {"T7": "T3", "T8": "T4", "P7": "T5", "P8": "T6"}
        raw.rename_channels(
            {ch: "EOG ROC-REF" if ch == "VEOG" else f"EEG {old.get(ch, ch).upper()}-REF" for ch in raw.ch_names}
        )
        raw.set_channel_types({ch: "eeg" for ch in raw.ch_names})
        raw.set_montage(None)
        mne.export.export_raw(workdir / "tuh.edf", raw, overwrite=True)
        report = json.loads(
            run("inspect_recording.py", "tuh.edf", "--format", "json", cwd=workdir).stdout
        )
        assert report["channel_type_suggestions"] == {"EOG ROC-REF": "eog"}
        montage = report["montage"]
        assert montage["with_positions"] == 0
        assert montage["best_matches"][0]["matched"] == 32
        assert montage["renames"]["EEG FP1-REF"] == "Fp1"
        assert montage["renames"]["EEG T5-REF"] == "T5"  # colin27 keeps the 10-20 names
        assert any("set_montage" in tip for tip in report["recommendations"])

    @pytest.mark.parametrize(("suffix", "package"), [(".vhdr", "pybv"), (".set", "eeglabio")])
    def test_reads_exported_formats(self, mne, workdir: Path, suffix: str, package: str) -> None:
        pytest.importorskip(package)
        name = f"fmt_{package}{suffix}"
        run("simulate_eeg.py", "--out", name, "--duration", "60", cwd=workdir)
        report = json.loads(run("inspect_recording.py", name, "--format", "json", cwd=workdir).stdout)
        labels = report["events"]["annotation_labels"]
        assert sum(labels.values()) == report["annotations"]["count"] > 0
        assert report["channel_type_suggestions"] == {"VEOG": "eog"}


class TestPreprocess:
    def test_recovers_ground_truth(self, preprocessed: dict) -> None:
        log = preprocessed["log"]
        assert log["status"] == "ok"
        assert set(log["bad_channels"]["detected"]) == {"FC5", "T8"}
        assert log["bad_channels"]["detected"]["T8"]["reasons"] == ["flat"]
        assert "deviation" in log["bad_channels"]["detected"]["FC5"]["reasons"]
        assert sorted(log["interpolation"]["interpolated"]) == ["FC5", "T8"]
        ica = log["ica"]
        assert ica["applied"] and ica["eog"]["channels"] == ["VEOG"]
        assert any("eog" in reasons for reasons in ica["excluded"].values())
        assert ica["blink_reduction"] >= 0.8
        assert ica["blink_p2p_uv"]["before"] == pytest.approx(150, rel=0.2)
        assert log["filtering"]["notch_hz"] == []  # 50 Hz sits in the 40 Hz low-pass stop band
        assert log["filtering"]["line_freq_hz"] == 50.0

    def test_outputs_are_clean_and_average_referenced(self, mne, preprocessed: dict) -> None:
        out = preprocessed["clean"].parent
        for name in ("sim_ica.fif", "sim_desc-preproc_report.html", "sim_desc-preproc_log.json"):
            assert (out / name).is_file()
        raw = mne.io.read_raw(preprocessed["clean"], preload=True)
        assert raw.info["bads"] == []
        eeg = raw.get_data(picks="eeg")
        assert abs(eeg.mean(axis=0)).max() < 1e-6 * abs(eeg).max()  # average reference (float32 FIF)
        assert raw.info["highpass"] == pytest.approx(0.1) and raw.info["lowpass"] == pytest.approx(40.0)
        ica = mne.preprocessing.read_ica(out / "sim_ica.fif")
        assert ica.exclude

    def test_refuses_to_overwrite(self, preprocessed: dict, workdir: Path) -> None:
        result = run("preprocess_eeg.py", "sim_raw.fif", "--out-dir", "pre", cwd=workdir, check=False)
        assert result.returncode == 2 and "--overwrite" in result.stderr

    def test_quality_gate_stops_and_logs(self, simulated: dict, workdir: Path) -> None:
        result = run(
            "preprocess_eeg.py", "sim_raw.fif", "--out-dir", "gate", "--no-report",
            "--corr-threshold", "0.999", "--corr-bad-fraction", "0.0", cwd=workdir, check=False,
        )
        assert result.returncode == 2 and "max-bad-fraction" in result.stderr
        log = json.loads((workdir / "gate" / "sim_desc-preproc_log.json").read_text(encoding="utf-8"))
        assert log["status"] == "failed_quality_gate"
        assert not (workdir / "gate" / "sim_desc-clean_eeg.fif").exists()

    @pytest.mark.parametrize("meas_date", [False, True])
    def test_stim_events_survive_crop_and_resample(self, mne, workdir: Path, meas_date: bool) -> None:
        """Events on a stim channel are converted to annotations before resampling; their
        timing must survive a crop (first_samp > 0) with and without a measurement date."""
        import datetime

        tag = f"stim{int(meas_date)}"
        run("simulate_eeg.py", "--out", f"{tag}_raw.fif", "--events", "stim", "--ecg", cwd=workdir)
        truth = json.loads((workdir / f"{tag}_raw_truth.json").read_text(encoding="utf-8"))
        if meas_date:
            raw = mne.io.read_raw(workdir / f"{tag}_raw.fif", preload=True)
            raw.set_meas_date(datetime.datetime(2024, 5, 1, 9, 30, tzinfo=datetime.timezone.utc))
            raw.save(workdir / f"{tag}_raw.fif", overwrite=True)
        run(
            "preprocess_eeg.py", f"{tag}_raw.fif", "--out-dir", tag, "--crop", "10", "200",
            "--resample", "125", "--no-report", cwd=workdir,
        )
        log = json.loads((workdir / tag / f"{tag}_desc-preproc_log.json").read_text(encoding="utf-8"))
        assert log["events"]["dropped_after_conversion"] == ["STI 014"]
        assert "ecg" in log["ica"]
        raw = mne.io.read_raw(workdir / tag / f"{tag}_desc-clean_eeg.fif")
        assert raw.info["sfreq"] == 125
        events, event_id = mne.events_from_annotations(raw)
        got = sorted((events[:, 0] - raw.first_samp) / raw.info["sfreq"])
        want = sorted(
            t - 10.0
            for label in ("standard", "target")
            for t in truth["events"]["onsets_s"][label]
            if 10.0 <= t <= 200.0
        )
        assert len(got) == len(want) == log["events"]["converted"]
        assert max(abs(a - b) for a, b in zip(got, want)) <= 1.0 / 125
        assert set(event_id) == {"1", "2"}


class TestErp:
    def test_components_match_truth(self, erp: dict, simulated: dict) -> None:
        rows = erp["rows"]
        target = measure(rows, "target", "Pz", "P3")
        standard = measure(rows, "standard", "Pz", "P3")
        assert float(target["mean_amplitude_uv"]) - float(standard["mean_amplitude_uv"]) > 2.0
        assert 300 <= float(target["peak_latency_ms"]) <= 400
        assert target["peak_at_window_edge"] == "False"
        for condition in ("standard", "target"):
            n1 = measure(rows, condition, "Cz", "N1")
            assert float(n1["mean_amplitude_uv"]) < 0
            assert 80 <= float(n1["peak_latency_ms"]) <= 130
            assert float(n1["sme_uv"]) > 0
        counts = simulated["truth"]["events"]["counts"]
        assert int(target["n_trials"]) == counts["target"]
        assert int(standard["n_trials"]) == counts["standard"]
        contrast = measure(rows, "target-standard", "parietal", "P3")
        assert contrast["kind"] == "contrast" and float(contrast["mean_amplitude_uv"]) > 1.0

    def test_outputs_and_trial_bookkeeping(self, erp: dict, simulated: dict) -> None:
        out, summary = erp["dir"], erp["summary"]
        counts = simulated["truth"]["events"]["counts"]
        for name, entry in summary["trials"].items():
            assert entry["n_events"] == counts[name]
            assert entry["n_kept"] + entry["n_dropped"] == entry["n_events"]
        trials = read_csv(out / "sim_erp_single_trials.csv")
        assert len(trials) == sum(counts.values()) * 3 * 2  # 3 ROIs x 2 windows
        for name in ("sim_epo.fif", "sim_ave.fif", "sim_erp_report.html", "sim_erp_Pz.png",
                     "sim_topomap_target_-_standard.png"):
            assert (out / name).is_file(), name
        assert summary["epoch"]["reject_eeg_uv"]["applied"] == 100.0

    def test_measures_agree_with_mne_stats_erp(self, mne, erp: dict) -> None:
        from mne.stats import erp as mne_erp

        if not hasattr(mne_erp, "compute_frac_area_latency"):
            pytest.skip("mne.stats.erp measures need MNE >= 1.13")
        out = erp["dir"]
        evoked = mne.read_evokeds(out / "sim_ave.fif", condition="target")
        epochs = mne.read_epochs(out / "sim_epo.fif")
        row = measure(erp["rows"], "target", "Pz", "P3")
        peak = mne_erp.compute_peak(evoked, 0.25, 0.45, picks="Pz", mode="pos")
        assert float(row["peak_latency_ms"]) == pytest.approx(peak["latency"][0] * 1e3, abs=0.01)
        assert float(row["peak_amplitude_uv"]) == pytest.approx(peak["amplitude"][0] * 1e6, abs=1e-3)
        frac = mne_erp.compute_frac_area_latency(evoked, 0.5, 0.25, 0.45, picks="Pz", mode="pos")
        assert float(row["frac_area_latency_ms"]) == pytest.approx(
            frac["fractional_area_latency"][0] * 1e3, abs=0.01
        )
        # compute_sme slices with Epochs.get_data(tmin, tmax), which excludes the tmax
        # sample; compute_peak/compute_area (and the script) use a closed window.
        # Half a sample more makes compute_sme cover the same samples.
        target = epochs[epochs.events[:, 2] == epochs.event_id["target"]]
        stop = 0.45 + 0.5 / epochs.info["sfreq"]
        sme = mne_erp.compute_sme(target.copy().pick("Pz"), 0.25, stop)
        assert float(row["sme_uv"]) == pytest.approx(sme[0] * 1e6, abs=1e-3)

    def test_list_events_and_input_errors(self, preprocessed: dict, workdir: Path) -> None:
        clean = str(preprocessed["clean"])
        listing = run("erp_analysis.py", clean, "--out-dir", "x", "--list-events", cwd=workdir)
        assert "'standard'" in listing.stdout and "'target'" in listing.stdout
        cases = [
            (["--condition", "odd=nope"], "not found"),
            (["--window", "P3=0.3:1.5"], "outside the epoch"),
            (["--condition", "a=standard", "--condition", "b=target", "--contrast", "a-c"], "--contrast"),
        ]
        for extra, message in cases:
            result = run("erp_analysis.py", clean, "--out-dir", "bad", *extra, cwd=workdir, check=False)
            assert result.returncode == 2 and message in result.stderr, result.stderr

    def test_auto_rejection_threshold(self, preprocessed: dict, workdir: Path) -> None:
        run(
            "erp_analysis.py", str(preprocessed["clean"]), "--out-dir", "auto", "--no-figures",
            "--reject-uv", "auto", "--window", "P3=0.25:0.45:pos", "--channels", "Pz", cwd=workdir,
        )
        summary = json.loads((workdir / "auto" / "sim_erp_summary.json").read_text(encoding="utf-8"))
        applied = summary["epoch"]["reject_eeg_uv"]["applied"]
        assert isinstance(applied, float) and applied > 0


class TestBandPower:
    def test_recovers_alpha(self, preprocessed: dict, workdir: Path) -> None:
        result = run("band_power.py", str(preprocessed["clean"]), "--out-dir", "spec", cwd=workdir)
        summary = json.loads((workdir / "spec" / "sim_spectral_summary.json").read_text(encoding="utf-8"))
        iaf = summary["individual_alpha_frequency"]
        assert iaf["peak_hz"] == pytest.approx(10.0, abs=0.25)
        assert iaf["center_of_gravity_hz"] == pytest.approx(10.0, abs=0.5)
        rows = read_csv(workdir / "spec" / "sim_band_power.csv")
        alpha = {r["channel"]: float(r["rel_power"]) for r in rows if r["band"] == "alpha"}
        assert max(alpha, key=alpha.get) in {"O1", "Oz", "O2"}
        totals: dict[str, float] = {}
        for r in rows:
            totals[r["channel"]] = totals.get(r["channel"], 0.0) + float(r["rel_power"])
        assert all(total == pytest.approx(1.0, abs=1e-4) for total in totals.values())
        assert set(summary["asymmetry"]["index_ln_right_minus_ln_left"]) >= {"F4:F3", "O2:O1"}
        assert summary["segments"]["kept_seconds"] <= 240.0
        assert any("low-pass" in note for note in summary["notes"])  # gamma band vs 40 Hz filter
        assert "alpha peak" in result.stdout
        assert (workdir / "spec" / "sim_psd.png").is_file()

    def test_tracks_a_different_alpha_frequency(self, mne, workdir: Path) -> None:
        run("simulate_eeg.py", "--out", "a9_raw.fif", "--alpha-freq", "9.0", "--duration", "120",
            "--no-bad-channels", cwd=workdir)
        run("band_power.py", "a9_raw.fif", "--out-dir", "a9", "--no-figures", cwd=workdir)
        summary = json.loads((workdir / "a9" / "a9_spectral_summary.json").read_text(encoding="utf-8"))
        assert summary["individual_alpha_frequency"]["peak_hz"] == pytest.approx(9.0, abs=0.25)

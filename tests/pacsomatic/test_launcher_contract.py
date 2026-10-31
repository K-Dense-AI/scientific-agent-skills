"""Local synthetic and mocked launch contracts; no genomic computation or scheduler."""
import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pacsomatic"
spec = importlib.util.spec_from_file_location("pacsomatic_contract", SKILL_ROOT / "scripts/run_pacsomatic.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


@pytest.fixture
def args(tmp_path):
    tumor = tmp_path / "tumor.bam"
    normal = tmp_path / "normal.bam"
    tumor.write_bytes(b"synthetic-placeholder-not-a-BAM")
    normal.write_bytes(b"different-synthetic-placeholder")
    argv = ["helper", "--tumor-bam", str(tumor), "--normal-bam", str(normal),
            "--patient-id", "P1", "--tumor-sample-id", "P1T", "--normal-sample-id", "P1N",
            "--outdir", str(tmp_path / "out"), "--genome", "GRCh38", "--use-current-path"]
    with patch.object(sys, "argv", argv):
        value = mod.parse_args()
    value.runtime_prefix = None
    value.generated_params_file = ""
    mod.normalize_paths(value)
    return value


@pytest.mark.parametrize("field,value", [
    ("patient_id", ""), ("tumor_sample_id", "P1\nT"), ("normal_sample_id", "P1T"),
    ("cpus", 0), ("memory_gb", float("nan")), ("memory_gb", float("inf")),
    ("memory_gb", -1), ("walltime", "48:60"), ("walltime", "0:00:00"),
    ("extra_args", "--input=/unreviewed.csv"), ("extra_args", "-r dev"),
])
def test_invalid_inputs_rejected(args, field, value):
    setattr(args, field, value)
    with pytest.raises(SystemExit):
        mod.validate_inputs(args)


def test_reference_exclusivity(args):
    args.fasta = "/some.fa"
    with pytest.raises(SystemExit):
        mod.validate_inputs(args)


@pytest.mark.parametrize("field", ["run", "submit", "create_conda_env", "checkout_dir"])
def test_dry_run_forbids_mutating_modes(args, field):
    args.dry_run = True
    setattr(args, field, True)
    with pytest.raises(SystemExit):
        mod.validate_inputs(args)


@pytest.mark.parametrize("kind", ["empty", "directory", "same", "hardlink"])
def test_invalid_bam_inputs(args, tmp_path, kind):
    if kind == "empty":
        Path(args.tumor_bam).write_bytes(b"")
    elif kind == "directory":
        Path(args.tumor_bam).unlink()
        Path(args.tumor_bam).mkdir()
    elif kind == "same":
        args.tumor_bam = args.normal_bam
    else:
        Path(args.tumor_bam).unlink()
        Path(args.tumor_bam).hardlink_to(args.normal_bam)
    with pytest.raises(SystemExit):
        mod.validate_inputs(args)


def test_remote_bam_still_checks_local_pbi(args):
    args.tumor_bam = "https://example.org/tumor.bam"
    args.tumor_pbi = "/missing/tumor.bam.pbi"
    with pytest.raises(SystemExit):
        mod.validate_inputs(args)
    args.tumor_pbi = "s3://bucket/tumor.bam.pbi"
    mod.validate_inputs(args)


def test_optional_pbi_is_not_coordinate_index(args):
    args.tumor_pbi = args.tumor_bam + ".bai"
    with pytest.raises(SystemExit):
        mod.validate_inputs(args)


@pytest.mark.parametrize("executor", ["lsf", "slurm", "pbs", "sge"])
def test_scheduler_directive_injection_blocked(args, executor):
    args.executor = executor
    args.job_name = "safe\necho pwned"
    with pytest.raises(SystemExit):
        mod.validate_inputs(args)


def test_scheduler_walltime_memory_and_log_tokens(args):
    args.executor = "slurm"
    lines = mod.scheduler_header_lines(args)
    assert "#SBATCH --time=48:00:00" in lines
    assert any("launcher%j.out" in line for line in lines)
    args.executor = "lsf"
    lines = mod.scheduler_header_lines(args)
    assert "#BSUB -W 48:00" in lines
    assert "#BSUB -M 65536MB" in lines
    args.walltime = "48:00:01"
    with pytest.raises(SystemExit):
        mod.validate_inputs(args)
    args.executor = "pbs"
    args.memory_gb = 0.5
    assert "#PBS -l select=1:ncpus=16:mem=512mb" in mod.scheduler_header_lines(args)
    args.executor = "sge"
    args.memory_gb = 1.001
    assert "#$ -l h_vmem=65M" in mod.scheduler_header_lines(args)


def test_yaml_values_roundtrip_special_characters(args):
    args.outdir = '/tmp/a: b#c"d'
    args.genome = "true"
    text = mod.build_generated_params_content(args, "/tmp/sheet.csv")
    values = {line.split(": ", 1)[0]: json.loads(line.split(": ", 1)[1]) for line in text.splitlines()}
    assert values == {"input": "/tmp/sheet.csv", "outdir": args.outdir, "genome": "true"}


def test_artifacts_cannot_alias_inputs_or_each_other(args):
    args.overwrite = True
    with pytest.raises(SystemExit):
        mod.validate_artifact_targets(args, args.tumor_bam, str(Path(args.outdir) / "run.sh"))
    with pytest.raises(SystemExit):
        mod.validate_artifact_targets(args, args.normal_bam, args.normal_bam)
    args.config_name = "../escape.yaml"
    with pytest.raises(SystemExit):
        mod.validate_artifact_targets(args, "/tmp/sheet.csv", "/tmp/run.sh")


def test_existing_artifacts_need_overwrite(args, tmp_path):
    sheet = tmp_path / "sheet.csv"
    sheet.write_text("review me")
    with pytest.raises(SystemExit):
        mod.validate_artifact_targets(args, str(sheet), str(tmp_path / "run.sh"))
    args.overwrite = True
    mod.validate_artifact_targets(args, str(sheet), str(tmp_path / "run.sh"))


def test_nextflow_command_keeps_params_and_infrastructure_distinct(args):
    args.pipeline_version = mod.REVIEWED_REVISION
    args.params_file = "/tmp/params.yaml"
    args.nextflow_config = "/tmp/site.config"
    cmd = mod.build_nextflow_command(args, "/tmp/sheet.csv")
    assert cmd[cmd.index("-r") + 1] == mod.REVIEWED_REVISION
    assert cmd[cmd.index("-params-file") + 1] == args.params_file
    assert cmd[cmd.index("-c") + 1] == args.nextflow_config
    assert "-process.executor" not in cmd


@pytest.mark.parametrize("executor,output,job_id", [
    ("lsf", "Job <123> is submitted to queue <normal>.", "123"),
    ("slurm", "Submitted batch job 234", "234"),
    ("pbs", "345.server.example", "345.server.example"),
    ("sge", 'Your job 456 ("demo") has been submitted', "456"),
])
def test_mock_scheduler_submission(args, tmp_path, executor, output, job_id, capsys):
    args.executor = executor
    script = tmp_path / "script;literal.sh"
    script.write_text("#!/bin/bash\ntrue\n")
    result = subprocess.CompletedProcess([], 0, output, "scheduler warning")
    with patch.object(mod.subprocess, "run", return_value=result) as run:
        mod.execute_launch(args, str(script))
    argv = run.call_args.args[0]
    assert argv[0] == mod.SCHEDULER_CMDS[executor]
    assert not run.call_args.kwargs.get("shell", False)
    assert ("stdin" in run.call_args.kwargs) == (executor == "lsf")
    assert mod.extract_job_id(executor, output) == job_id
    captured = capsys.readouterr()
    assert "pipeline completion not verified" in captured.out
    assert "scheduler warning" in captured.err


def test_old_nextflow_fails_run(args):
    args.run = True
    with patch.object(mod.shutil, "which", return_value="/bin/nextflow"), patch.object(mod.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "nextflow version 21.10.5", "")):
        with pytest.raises(SystemExit):
            mod.ensure_runtime_tools(args)


def test_runtime_profile_does_not_alias_singularity_apptainer(args):
    args.run = True
    args.profile = "singularity"
    def which(name):
        return "/bin/" + name if name == "apptainer" else None
    with patch.object(mod, "detect_java_major_version", return_value=21), patch.object(mod.shutil, "which", side_effect=which):
        with pytest.raises(SystemExit):
            mod.ensure_dependency_tools(args)
        args.profile = "apptainer"
        mod.ensure_dependency_tools(args)


def test_java_cmd_environment_is_honored(monkeypatch):
    monkeypatch.setenv("JAVA_CMD", "/runtime/bin/java")
    with patch.object(mod.shutil, "which", return_value="/runtime/bin/java"), patch.object(mod.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", 'openjdk version "21.0.12"')) as run:
        assert mod.detect_java_major_version() == 21
        assert run.call_args.args[0] == ["/runtime/bin/java", "-version"]


def test_generated_script_uses_absolute_paths_and_stable_cwd(args, tmp_path):
    Path(args.outdir).mkdir()
    sheet = str(Path(args.outdir) / "samplesheet.csv")
    mod.build_samplesheet(args, sheet)
    rows = list(csv.DictReader(Path(sheet).open()))
    assert [row["status"] for row in rows] == ["1", "0"]
    assert all(Path(row["bam"]).is_absolute() for row in rows)
    script = tmp_path / "run.sh"
    mod.write_launch_script(args, str(script), ["printf", "%s\\n", "literal;not-code"])
    result = subprocess.run(["bash", str(script)], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout == "literal;not-code\n"
    assert f"cd {args.outdir}" in script.read_text()


def test_local_execution_streams_output(args):
    with patch.object(mod.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
        mod.execute_launch(args, "/tmp/run.sh")
    assert "capture_output" not in run.call_args.kwargs


def test_extreme_finite_memory_is_rejected_before_conversion(args):
    args.memory_gb = 1e308
    with pytest.raises(SystemExit):
        mod.validate_inputs(args)


def test_default_generation_pins_reviewed_remote_revision(args):
    with patch.object(mod, "parse_args", return_value=args), patch.object(mod, "ensure_runtime_tools"), patch.object(mod, "ensure_dependency_tools"):
        mod.main()
    script = Path(args.outdir, "run_pacsomatic.local.sh").read_text()
    assert f"-r {mod.REVIEWED_REVISION}" in script
    assert "nextflow run nf-core/pacsomatic" in script


def test_conflicting_modes_fail_before_any_artifact_or_runtime_work(args):
    args.dry_run = True
    args.submit = True
    with patch.object(mod, "parse_args", return_value=args), patch.object(mod, "resolve_runtime") as runtime:
        with pytest.raises(SystemExit):
            mod.main()
    runtime.assert_not_called()
    assert not Path(args.outdir).exists()


def test_new_clone_checks_out_revision_and_does_not_pass_local_r(args, tmp_path):
    args.checkout_dir = str(tmp_path / "checkout")
    args.pipeline_version = mod.REVIEWED_REVISION
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        if argv[1] == "clone":
            Path(argv[-1]).mkdir(parents=True)
            Path(argv[-1], "main.nf").write_text("workflow {}")
        return subprocess.CompletedProcess(argv, 0)
    with patch.object(mod.shutil, "which", return_value="git"), patch.object(mod.subprocess, "run", side_effect=run):
        mod.ensure_pipeline_repo(args)
    assert calls[1][-3:] == ["checkout", "--detach", mod.REVIEWED_REVISION]
    assert args.pipeline_version == ""
    assert Path(args.pipeline, "main.nf").is_file()


def test_existing_clone_revision_mismatch_is_not_mutated(args, tmp_path):
    args.checkout_dir = str(tmp_path)
    target = tmp_path / args.repo_name
    target.mkdir()
    (target / "main.nf").write_text("workflow {}")
    args.pipeline_version = mod.REVIEWED_REVISION
    with patch.object(mod.shutil, "which", return_value="git"), patch.object(mod.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "other\nrequested\n", "")) as run:
        with pytest.raises(SystemExit):
            mod.ensure_pipeline_repo(args)
    assert run.call_count == 1
    assert "rev-parse" in run.call_args.args[0]


def test_local_repo_rejects_remote_revision_argument(args, tmp_path):
    (tmp_path / "main.nf").write_text("workflow {}")
    args.repo_path = str(tmp_path)
    args.pipeline_version = "dev"
    with pytest.raises(SystemExit):
        mod.ensure_pipeline_repo(args)


def test_environment_creation_requires_explicit_yaml(args):
    args.use_current_path = False
    args.create_conda_env = True
    with patch.object(mod, "find_conda_env_prefix", return_value=None), patch.object(mod, "create_conda_env") as create:
        with pytest.raises(SystemExit):
            mod.resolve_runtime(args)
    create.assert_not_called()


@pytest.mark.parametrize("raw", ["module load x\necho bad", "echo bad", "module load $(id)", "module load x | cat"])
def test_module_load_rejects_shell_injection(raw):
    with pytest.raises(SystemExit):
        mod.normalize_module_load(raw)


def test_module_load_preserves_plain_sequence():
    assert mod.normalize_module_load("module purge; module load nextflow/26.04.6") == "module purge && module load nextflow/26.04.6"

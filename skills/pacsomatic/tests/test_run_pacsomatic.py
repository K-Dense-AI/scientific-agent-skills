import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "run_pacsomatic.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_pacsomatic", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load run_pacsomatic module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunPacsomaticUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def test_normalize_walltime_hhmm(self):
        got = self.mod.normalize_walltime_hhmmss("48:00", "walltime")
        self.assertEqual(got, "48:00:00")

    def test_normalize_walltime_hhmmss(self):
        got = self.mod.normalize_walltime_hhmmss("12:34:56", "walltime")
        self.assertEqual(got, "12:34:56")

    def test_extract_job_id_slurm(self):
        out = "Submitted batch job 123456"
        got = self.mod.extract_job_id("slurm", out)
        self.assertEqual(got, "123456")

    def test_extract_job_id_lsf(self):
        out = "Job <998877> is submitted to queue <normal>."
        got = self.mod.extract_job_id("lsf", out)
        self.assertEqual(got, "998877")

    def test_build_generated_params_content_genome(self):
        args = SimpleNamespace(outdir="/tmp/out", fasta="", genome="GRCh38")
        text = self.mod.build_generated_params_content(args, "/tmp/out/samplesheet.csv")
        self.assertIn("input: /tmp/out/samplesheet.csv", text)
        self.assertIn("outdir: /tmp/out", text)
        self.assertIn("genome: GRCh38", text)

    def test_build_generated_params_content_fasta(self):
        args = SimpleNamespace(outdir="/tmp/out", fasta="/ref/genome.fa", genome="")
        text = self.mod.build_generated_params_content(args, "/tmp/out/samplesheet.csv")
        self.assertIn("fasta: /ref/genome.fa", text)

    def test_build_samplesheet_status_values(self):
        args = SimpleNamespace(
            patient_id="P001",
            tumor_sample_id="P001_T",
            normal_sample_id="P001_N",
            tumor_bam="/data/tumor.bam",
            normal_bam="/data/normal.bam",
            tumor_pbi="",
            normal_pbi="",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "samplesheet.csv"
            self.mod.build_samplesheet(args, str(path))
            content = path.read_text(encoding="utf-8")

        self.assertIn("patient,sample,status,bam,pbi", content)
        self.assertIn("P001,P001_T,1,/data/tumor.bam,", content)
        self.assertIn("P001,P001_N,0,/data/normal.bam,", content)


if __name__ == "__main__":
    unittest.main()

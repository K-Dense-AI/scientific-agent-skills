#!/usr/bin/env python3
"""
DiffDock Environment Setup Checker

This script verifies that the DiffDock environment is properly configured
and all dependencies are available.

Usage:
    python /path/to/skill/scripts/setup_check.py
    python /path/to/skill/scripts/setup_check.py --verbose
"""

import argparse
import sys
import os
from pathlib import Path


def check_python_version():
    """Check Python version."""
    import sys
    version = sys.version_info

    print("Checking Python version...")
    if version.major == 3 and version.minor == 9:
        print(f"  [OK] Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  [FAIL] Python {version.major}.{version.minor}.{version.micro} "
              f"(upstream environment.yml targets Python 3.9.18; other minors are not verified)")
        return False


def check_package(package_name, import_name=None, version_attr='__version__'):
    """Check if a Python package is installed."""
    if import_name is None:
        import_name = package_name

    try:
        module = __import__(import_name)
        version = module
        for attr in version_attr.split('.'):
            version = getattr(version, attr, None)
            if version is None:
                version = 'unknown'
                break
        print(f"  [OK] {package_name:20s} (version: {version})")
        return True
    except ImportError:
        print(f"  [FAIL] {package_name:20s} (not installed)")
        return False


def check_pytorch():
    """Check PyTorch installation and CUDA availability."""
    print("\nChecking PyTorch...")
    try:
        import torch
        print(f"  [OK] PyTorch version: {torch.__version__}")

        # Check CUDA
        if torch.cuda.is_available():
            print(f"  [OK] CUDA available: {torch.cuda.get_device_name(0)}")
            print(f"    - CUDA version: {torch.version.cuda}")
            print(f"    - Number of GPUs: {torch.cuda.device_count()}")
            return True, True
        else:
            print(f"  [WARN] CUDA not available (will run on CPU)")
            return True, False
    except ImportError:
        print(f"  [FAIL] PyTorch not installed")
        return False, False


def check_pytorch_geometric():
    """Check PyTorch Geometric installation."""
    print("\nChecking PyTorch Geometric...")
    packages = [
        ('torch-geometric', 'torch_geometric'),
        ('torch-scatter', 'torch_scatter'),
        ('torch-sparse', 'torch_sparse'),
        ('torch-cluster', 'torch_cluster'),
    ]

    all_ok = True
    for pkg_name, import_name in packages:
        if not check_package(pkg_name, import_name):
            all_ok = False

    return all_ok


def check_core_dependencies():
    """Check core DiffDock dependencies."""
    print("\nChecking core dependencies...")

    dependencies = [
        ('numpy', 'numpy'),
        ('scipy', 'scipy'),
        ('pandas', 'pandas'),
        ('rdkit', 'rdkit', '__version__'),
        ('biopython', 'Bio', '__version__'),
        ('pytorch-lightning', 'pytorch_lightning'),
        ('PyYAML', 'yaml'),
        ('ProDy', 'prody'),
        ('e3nn', 'e3nn'),
    ]

    all_ok = True
    for dep in dependencies:
        pkg_name = dep[0]
        import_name = dep[1]
        version_attr = dep[2] if len(dep) > 2 else '__version__'

        if not check_package(pkg_name, import_name, version_attr):
            all_ok = False

    return all_ok


def check_esm():
    """Check ESM (protein language model) installation."""
    print("\nChecking fair-esm (ESM2 embeddings for all inputs; ESMFold for sequences)...")
    try:
        import esm
        if not hasattr(esm, 'FastaBatchedDataset') or not hasattr(getattr(esm, 'pretrained', None), 'load_model_and_alphabet'):
            print("  [FAIL] Wrong/incomplete esm module; DiffDock requires fair-esm==2.0.0")
            return False
        print(f"  [OK] ESM installed (version: {esm.__version__ if hasattr(esm, '__version__') else 'unknown'})")
        return True
    except ImportError:
        print(f"  [FAIL] fair-esm not installed (required for PDB embeddings and protein sequence folding)")
        print(f"    Use the upstream environment.yml fair-esm[esmfold]==2.0.0 pin")
        return False


def check_diffdock_installation():
    """Check if DiffDock is properly installed/cloned."""
    print("\nChecking DiffDock installation...")

    # Look for key files
    key_files = [
        'inference.py',
        'default_inference_args.yaml',
        'environment.yml',
    ]

    found_files = []
    missing_files = []

    for filename in key_files:
        if Path(filename).is_file():
            found_files.append(filename)
        else:
            missing_files.append(filename)

    if found_files:
        print(f"  [OK] Found DiffDock files in current directory:")
        for f in found_files:
            print(f"    - {f}")
    else:
        print(f"  [WARN] DiffDock files not found in current directory")
        print(f"    Current directory: {os.getcwd()}")
        print(f"    Make sure you're in the DiffDock repository root")

    # Check for model checkpoints
    model_dir = Path('./workdir/v1.1/score_model')
    confidence_dir = Path('./workdir/v1.1/confidence_model')

    checkpoint_files = [model_dir / 'model_parameters.yml', model_dir / 'best_ema_inference_epoch_model.pt', confidence_dir / 'model_parameters.yml', confidence_dir / 'best_model_epoch75.pt']
    if all(path.is_file() and path.stat().st_size > 0 for path in checkpoint_files):
        print(f"  [OK] Model checkpoints found")
    else:
        print(f"  [WARN] Model checkpoints not found in ./workdir/v1.1/")
        print(f"    Models are downloaded on first run only if the score-model directory is absent; repair partial downloads")

    if missing_files:
        print(f"  [FAIL] Missing checkout files: {', '.join(missing_files)}")
    return not missing_files


def print_installation_instructions():
    """Print installation instructions if setup is incomplete."""
    print("\n" + "="*80)
    print("Installation Instructions")
    print("="*80)

    print("""
If DiffDock is not installed, follow these steps:

1. Clone the repository:
   git clone --branch v1.1.3 --depth 1 https://github.com/gcorso/DiffDock.git
   cd DiffDock

2. Create conda environment:
   conda env create --file environment.yml
   conda activate diffdock

3. Verify installation:
   python /path/to/skill/scripts/setup_check.py

For Docker installation:
   docker pull rbgcsail/diffdock
   docker run -it --gpus all --entrypoint /bin/bash rbgcsail/diffdock
   micromamba activate diffdock

For more information, visit: https://github.com/gcorso/DiffDock
    """)


def print_performance_notes(has_cuda):
    """Print performance notes based on available hardware."""
    print("\n" + "="*80)
    print("Performance Notes")
    print("="*80)

    if has_cuda:
        print("[OK] GPU detected; benchmark runtime and memory on your inputs.")
    else:
        print("[WARN] No GPU detected; PDB inference may be SIGNIFICANTLY slower on CPU.")
        print("Sequence folding in v1.1.3 calls CUDA unconditionally; provide a PDB on CPU.")
    print("First use can build lookup tables and download docking, ESM2 and ESMFold weights.")
    print("Import checks do not establish checkpoint compatibility or successful docking.")


def main():
    parser = argparse.ArgumentParser(
        description='Check DiffDock environment setup',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed version information')

    args = parser.parse_args()

    print("="*80)
    print("DiffDock Environment Setup Checker")
    print("="*80)

    checks = []

    # Run all checks
    checks.append(("Python version", check_python_version()))

    pytorch_ok, has_cuda = check_pytorch()
    checks.append(("PyTorch", pytorch_ok))

    checks.append(("PyTorch Geometric", check_pytorch_geometric()))
    checks.append(("Core dependencies", check_core_dependencies()))
    checks.append(("ESM", check_esm()))
    checks.append(("DiffDock files", check_diffdock_installation()))

    # Summary
    print("\n" + "="*80)
    print("Summary")
    print("="*80)

    all_passed = all(result for _, result in checks)

    for check_name, result in checks:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status:8s} - {check_name}")

    if all_passed:
        print("\n[OK] Dependency imports and checkout checks passed; verify pinned versions and run a small docking smoke test.")
        print_performance_notes(has_cuda)
        return 0
    else:
        print("\n[FAIL] Some checks failed. Please install missing dependencies.")
        print_installation_instructions()
        return 1


if __name__ == '__main__':
    sys.exit(main())

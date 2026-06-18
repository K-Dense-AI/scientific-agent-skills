# R Interoperability for Scanpy

Many single-cell datasets arrive as R objects (`.rds`, `.RData`, Seurat, or SingleCellExperiment) even when the downstream analysis should happen in Scanpy. Agents should convert these inputs to AnnData `.h5ad` first, then continue with normal Scanpy workflows.

## Operating Principles

1. **Do not parse Seurat `.rds` directly in Python.** Use R to deserialize R objects and write `.h5ad`.
2. **Prefer `.h5ad` as the Python handoff format.** After conversion, all QC, clustering, plotting, and exports should use Scanpy/AnnData.
3. **Inspect before converting.** Determine whether the R object is Seurat, SingleCellExperiment, or a list/container; do not assume from the filename.
4. **Preserve raw counts and metadata.** Keep cell metadata (`obs`), gene metadata (`var`), raw counts/layers, and dimensional reductions when available.
5. **Use noninteractive commands.** Agents should use `Rscript -e` or script files, set CRAN repos explicitly, and pass `ask = FALSE`, `update = FALSE` for Bioconductor installs.

## Detect R and the Platform

Use these checks before installing anything:

```bash
uname -s 2>/dev/null || true
command -v Rscript || command -v R || true
Rscript --version 2>/dev/null || R --version 2>/dev/null || true
```

On Windows from PowerShell:

```powershell
Get-Command Rscript -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
Get-Command R -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
```

If Git Bash cannot find R on Windows, query PowerShell or common install paths:

```powershell
Get-ChildItem "C:\Program Files\R" -Filter Rscript.exe -Recurse -ErrorAction SilentlyContinue |
  Select-Object -First 1 -ExpandProperty FullName
```

Then call the discovered executable with quotes, for example:

```bash
"/c/Program Files/R/R-4.6.0/bin/Rscript.exe" --version
```

## Install R by OS

Prefer existing system package managers. If installation requires GUI approval, admin credentials, or an unavailable package manager, stop and report the blocker.

### macOS

Use Homebrew when available:

```bash
brew install --cask r
```

For packages with compiled code, install command-line build tools if the system asks for compilers:

```bash
xcode-select --install
```

Some R packages with Fortran code may require the CRAN macOS toolchain from `https://mac.R-project.org/tools/`. Prefer CRAN binary packages where possible to avoid compiler work.

### Linux

Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y \
  r-base r-base-dev build-essential gfortran \
  libcurl4-openssl-dev libssl-dev libxml2-dev libhdf5-dev \
  libharfbuzz-dev libfribidi-dev libfontconfig1-dev libfreetype6-dev \
  libpng-dev libtiff5-dev libjpeg-dev
```

Fedora/RHEL-like systems:

```bash
sudo dnf install -y \
  R R-devel gcc gcc-c++ gcc-gfortran make \
  libcurl-devel openssl-devel libxml2-devel hdf5-devel \
  harfbuzz-devel fribidi-devel fontconfig-devel freetype-devel \
  libpng-devel libtiff-devel libjpeg-turbo-devel
```

If `sudo` is unavailable, use a managed environment such as Conda/Mamba if already present:

```bash
conda install -c conda-forge r-base r-essentials
```

### Windows

Use `winget` from PowerShell when available:

```powershell
winget install --id RProject.R -e
```

Install Rtools only if packages need compilation:

```powershell
winget install --id RProject.Rtools -e
```

After installation, open a new shell or locate `Rscript.exe` under `C:\Program Files\R\R-*\bin\`. In Git Bash, call Windows executables through quoted paths or PowerShell; do not assume `/usr/bin/R` exists.

## Install Conversion Packages

Create a project-local R library when you do not want to alter the user's global R library:

```bash
mkdir -p .r-lib
export R_LIBS_USER="$PWD/.r-lib"
```

Install the core conversion stack:

```bash
Rscript -e 'options(repos = c(CRAN = "https://cloud.r-project.org")); install.packages(c("BiocManager", "remotes"), Ncpus = max(1, parallel::detectCores() - 1)); BiocManager::install(c("SingleCellExperiment", "zellkonverter"), ask = FALSE, update = FALSE)'
```

Install Seurat support only when the input is a Seurat object:

```bash
Rscript -e 'options(repos = c(CRAN = "https://cloud.r-project.org")); install.packages(c("Seurat", "SeuratObject"), Ncpus = max(1, parallel::detectCores() - 1))'
```

Optional SeuratDisk fallback for h5Seurat-to-h5ad conversion:

```bash
Rscript -e 'options(repos = c(CRAN = "https://cloud.r-project.org")); if (!requireNamespace("remotes", quietly = TRUE)) install.packages("remotes"); remotes::install_github("mojaveazure/seurat-disk", upgrade = "never")'
```

Avoid `sceasy` as the first choice. It can work, but it depends on `reticulate`/Python environment coupling and has more version-specific failure modes. Use it only after `zellkonverter` and SeuratDisk paths fail.

## Inspect R Inputs

For `.rds` files:

```bash
Rscript -e 'obj <- readRDS("input.rds"); print(class(obj)); if (is.list(obj) && !is.data.frame(obj)) print(names(obj))'
```

For `.RData`/`.rda` files:

```bash
Rscript -e 'e <- new.env(parent = emptyenv()); load("input.RData", envir = e); print(ls(e)); print(lapply(as.list(e), class))'
```

If multiple objects are present, choose the object with class `Seurat`, `SingleCellExperiment`, or `SummarizedExperiment`. If there is ambiguity, ask the user which object to convert.

## Convert `.rds` to `.h5ad`

Use this script as the default conversion path. It handles SingleCellExperiment directly and converts Seurat objects through SingleCellExperiment before writing `.h5ad`.

```r
#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript convert_rds_to_h5ad.R input.rds output.h5ad [assay]", call. = FALSE)
}

input <- normalizePath(args[[1]], mustWork = TRUE)
output <- args[[2]]
assay <- if (length(args) >= 3) args[[3]] else NULL

options(repos = c(CRAN = "https://cloud.r-project.org"))

ensure_pkg <- function(pkg, bioc = FALSE) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    if (bioc) {
      if (!requireNamespace("BiocManager", quietly = TRUE)) {
        install.packages("BiocManager")
      }
      BiocManager::install(pkg, ask = FALSE, update = FALSE)
    } else {
      install.packages(pkg)
    }
  }
}

ensure_pkg("SingleCellExperiment", bioc = TRUE)
ensure_pkg("SummarizedExperiment", bioc = TRUE)
ensure_pkg("zellkonverter", bioc = TRUE)

obj <- readRDS(input)
message("Input classes: ", paste(class(obj), collapse = ", "))

if (inherits(obj, "SingleCellExperiment")) {
  sce <- obj
} else if (inherits(obj, "Seurat")) {
  ensure_pkg("Seurat")
  ensure_pkg("SeuratObject")

  obj <- Seurat::UpdateSeuratObject(obj, verbose = FALSE)
  if (is.null(assay)) {
    assay <- SeuratObject::DefaultAssay(obj)
  }

  if ("JoinLayers" %in% getNamespaceExports("SeuratObject")) {
    obj <- tryCatch(SeuratObject::JoinLayers(obj, assay = assay), error = function(e) obj)
  }

  sce <- Seurat::as.SingleCellExperiment(obj, assay = assay)
} else {
  stop("Unsupported RDS class: ", paste(class(obj), collapse = ", "), call. = FALSE)
}

x_name <- if ("counts" %in% SummarizedExperiment::assayNames(sce)) "counts" else NULL
zellkonverter::writeH5AD(sce, output, X_name = x_name)
message("Wrote: ", normalizePath(output, mustWork = FALSE))
```

Run it:

```bash
Rscript convert_rds_to_h5ad.R input.rds output.h5ad
```

If the Seurat object has multiple assays and the user specified one, pass it explicitly:

```bash
Rscript convert_rds_to_h5ad.R input.rds output.h5ad RNA
```

## SeuratDisk Fallback

If Seurat-to-SingleCellExperiment conversion fails, try SeuratDisk:

```r
library(Seurat)
library(SeuratDisk)

obj <- readRDS("input.rds")
obj <- UpdateSeuratObject(obj)
DefaultAssay(obj) <- "RNA"
SaveH5Seurat(obj, filename = "output.h5Seurat", overwrite = TRUE)
Convert("output.h5Seurat", dest = "h5ad", overwrite = TRUE)
```

Be aware that SeuratDisk chooses which assay/layer becomes AnnData `.X` based on the available Seurat slots. If raw counts are essential, validate where counts landed after conversion and copy them into `adata.layers["counts"]` if needed.

## Validate in Python

After conversion, always validate with Scanpy before continuing:

```python
import scanpy as sc

adata = sc.read_h5ad("output.h5ad")
adata.var_names_make_unique()

print(adata)
print(adata.obs.head())
print(adata.var.head())
print("layers:", list(adata.layers.keys()))
print("obsm:", list(adata.obsm.keys()))

adata.write_h5ad("output.validated.h5ad", compression="gzip")
```

If the user requested metadata and expression exports:

```python
import scipy.io as sio

adata.obs.to_csv("cell_metadata.csv")
adata.var.to_csv("gene_metadata.csv")
sio.mmwrite("expression_matrix.mtx", adata.X)
```

For very large datasets, avoid dense CSV expression exports unless the user explicitly asks. Prefer `.h5ad`, Matrix Market (`.mtx`), or sparse-aware downstream analysis.

## Troubleshooting

- **`Rscript: command not found`**: R is not installed or not on PATH. Use the OS-specific install steps above, then reopen the shell or call the full `Rscript` path.
- **Windows Git Bash cannot find R**: Use PowerShell to locate `Rscript.exe` and invoke the quoted path from Git Bash.
- **Package compilation fails**: Install system build dependencies (`r-base-dev`, compilers, HDF5/libcurl/OpenSSL/XML headers, Rtools on Windows, or macOS command-line tools).
- **Bioconductor version mismatch**: Upgrade R when possible. Bioconductor packages are tied to compatible R releases; avoid forcing incompatible versions.
- **Seurat v5 layer issues**: Try `SeuratObject::JoinLayers()` before conversion, pass the assay explicitly, or use SeuratDisk fallback.
- **Counts missing or normalized data in `.X`**: Inspect `adata.layers`, `adata.raw`, and value ranges. Keep raw counts in `adata.layers["counts"]` before normalization if available.
- **Memory pressure**: Convert on a machine with enough RAM, avoid dense exports, and write compressed `.h5ad` checkpoints after successful conversion.

## Sources Checked

- R Project and CRAN installation pages: `https://www.r-project.org/`, `https://cran.r-project.org/bin/macosx`, `https://cran.r-project.org/bin/windows/base/rw-FAQ.html`
- Bioconductor install guidance and BiocManager documentation: `https://www.bioconductor.org/install/`, `https://cran.r-project.org/web/packages/BiocManager/vignettes/BiocManager.html`
- zellkonverter project and package documentation: `https://www.bioconductor.org/packages/release/bioc/html/zellkonverter.html`, `https://github.com/theislab/zellkonverter`
- SeuratDisk documentation and repository: `https://mojaveazure.github.io/seurat-disk/`, `https://github.com/mojaveazure/seurat-disk`
- sceasy repository for fallback context: `https://github.com/cellgeni/sceasy`

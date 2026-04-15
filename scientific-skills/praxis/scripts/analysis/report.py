"""Auto-generate markdown summary reports of analyses performed.

Collects results from fitting, peaks, statistics, XRD, and custom sections,
then renders a clean, professional markdown document.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

class AnalysisReport:
    """Collects analysis results and generates a markdown report.

    Usage
    -----
    >>> report = AnalysisReport("My Experiment")
    >>> report.add_fit_result(fit)
    >>> report.add_peak_results(peaks)
    >>> md = report.generate("output/report.md")
    """

    def __init__(self, title: str = "Analysis Report"):
        self.title = title
        self.sections: list[dict] = []
        self._created = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def add_section(
        self,
        title: str,
        content: str,
        figures: Optional[list[str]] = None,
        tables: Optional[list[dict]] = None,
    ) -> None:
        """Add a free-form section.

        Parameters
        ----------
        title : str
            Section heading.
        content : str
            Markdown body text.
        figures : list of str, optional
            Paths to figure images.
        tables : list of dict, optional
            Each dict has 'data' (list-of-lists or dict) and optional 'caption'.
        """
        self.sections.append({
            "type": "custom",
            "title": title,
            "content": content,
            "figures": figures or [],
            "tables": tables or [],
        })

    def add_fit_result(self, fit_result: Any, section_title: str = "Curve Fitting") -> None:
        """Add a FitResult from analysis.fitting.

        Parameters
        ----------
        fit_result : FitResult
            Result object from ``fit_curve()``.
        section_title : str
            Section heading.
        """
        params_table = {
            "headers": ["Parameter", "Value", "Uncertainty"],
            "rows": [],
        }
        for name, value in fit_result.params.items():
            unc = fit_result.uncertainties.get(name)
            unc_str = f"{unc:.4e}" if unc is not None else "N/A"
            params_table["rows"].append([name, f"{value:.6e}", unc_str])

        self.sections.append({
            "type": "fit",
            "title": section_title,
            "model": fit_result.model_name,
            "r_squared": fit_result.r_squared,
            "reduced_chi_sq": fit_result.reduced_chi_squared,
            "aic": fit_result.aic,
            "bic": fit_result.bic,
            "params_table": params_table,
        })

    def add_peak_results(self, peak_results: Any, section_title: str = "Peak Analysis") -> None:
        """Add PeakResults from analysis.peaks.

        Parameters
        ----------
        peak_results : PeakResults
            Result object from ``find_peaks_auto()``.
        section_title : str
            Section heading.
        """
        rows = []
        for i, p in enumerate(peak_results.peaks, 1):
            fwhm = f"{p.fwhm:.4f}" if p.fwhm is not None else "N/A"
            area = f"{p.area:.4e}" if p.area is not None else "N/A"
            prom = f"{p.prominence:.4e}" if p.prominence is not None else "N/A"
            rows.append([str(i), f"{p.position:.4f}", f"{p.height:.4e}", fwhm, area, prom])

        self.sections.append({
            "type": "peaks",
            "title": section_title,
            "n_peaks": peak_results.n_peaks,
            "table": {
                "headers": ["#", "Position", "Height", "FWHM", "Area", "Prominence"],
                "rows": rows,
            },
        })

    def add_descriptive_stats(
        self, stats: Any, section_title: str = "Descriptive Statistics"
    ) -> None:
        """Add DescriptiveStats from analysis.statistics.

        Parameters
        ----------
        stats : DescriptiveStats
            Result object from ``descriptive()``.
        section_title : str
            Section heading.
        """
        rows = [
            ["N", str(stats.n)],
            ["Mean", f"{stats.mean:.6g}"],
            ["Std Dev", f"{stats.std:.6g}"],
            ["SEM", f"{stats.sem:.6g}"],
            ["Median", f"{stats.median:.6g}"],
            ["Q1", f"{stats.q1:.6g}"],
            ["Q3", f"{stats.q3:.6g}"],
            ["IQR", f"{stats.iqr:.6g}"],
            ["Min", f"{stats.min:.6g}"],
            ["Max", f"{stats.max:.6g}"],
            ["Range", f"{stats.range:.6g}"],
            ["Skewness", f"{stats.skewness:.4f}"],
            ["Kurtosis", f"{stats.kurtosis:.4f}"],
            ["CV (%)", f"{stats.cv:.2f}"],
            ["95% CI", f"({stats.ci_95[0]:.6g}, {stats.ci_95[1]:.6g})"],
        ]

        self.sections.append({
            "type": "stats",
            "title": section_title,
            "table": {
                "headers": ["Statistic", "Value"],
                "rows": rows,
            },
        })

    def add_xrd_results(self, xrd_results: Any, section_title: str = "XRD Analysis") -> None:
        """Add XRDResults from techniques.xrd.

        Parameters
        ----------
        xrd_results : XRDResults
            Result object from XRD analysis functions.
        section_title : str
            Section heading.
        """
        rows = []
        for i, p in enumerate(xrd_results.peaks, 1):
            fwhm = f"{p.fwhm:.4f}" if p.fwhm is not None else "N/A"
            size = f"{p.crystallite_size:.1f}" if p.crystallite_size is not None else "N/A"
            hkl = p.hkl or "N/A"
            rows.append([
                str(i),
                f"{p.two_theta:.4f}",
                f"{p.d_spacing:.4f}",
                fwhm,
                size,
                f"{p.intensity:.1f}",
                hkl,
            ])

        section = {
            "type": "xrd",
            "title": section_title,
            "wavelength": xrd_results.wavelength,
            "wavelength_name": xrd_results.wavelength_name,
            "n_peaks": len(xrd_results.peaks),
            "table": {
                "headers": ["#", "2th (deg)", "d (A)", "FWHM (deg)", "Size (nm)", "Intensity", "hkl"],
                "rows": rows,
            },
        }

        # Williamson-Hall results if available
        if xrd_results.wh_slope is not None:
            section["wh_slope"] = xrd_results.wh_slope
            section["wh_intercept"] = xrd_results.wh_intercept
            section["wh_r_squared"] = xrd_results.wh_r_squared

        self.sections.append(section)

    def add_figure(self, fig_path: str, caption: str = "") -> None:
        """Add a standalone figure reference.

        Parameters
        ----------
        fig_path : str
            Path to the figure image file.
        caption : str
            Figure caption.
        """
        self.sections.append({
            "type": "figure",
            "path": fig_path,
            "caption": caption,
        })

    def add_table(self, df_or_dict: Any, caption: str = "") -> None:
        """Add a standalone data table.

        Parameters
        ----------
        df_or_dict : DataFrame or dict
            If a dict, keys become column headers and values become columns.
            If a DataFrame, it is converted to a dict first.
        caption : str
            Table caption.
        """
        headers, rows = _parse_table_data(df_or_dict)
        self.sections.append({
            "type": "table",
            "caption": caption,
            "headers": headers,
            "rows": rows,
        })

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def generate(self, output_path: Optional[str] = None, output_dir: str = ".") -> str:
        """Generate the full markdown report.

        Parameters
        ----------
        output_path : str, optional
            If given, write the report to this file path.
        output_dir : str
            Directory for auto-generated filename (used only if
            *output_path* is None and you want to write to disk later).

        Returns
        -------
        str
            The complete markdown string.
        """
        lines: list[str] = []

        # Header
        lines.append(f"# {self.title}")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Table of contents
        if len(self.sections) > 1:
            lines.append("## Contents")
            lines.append("")
            toc_idx = 1
            for section in self.sections:
                if section["type"] == "figure":
                    continue
                title = section.get("title", section.get("caption", f"Section {toc_idx}"))
                anchor = title.lower().replace(" ", "-").replace("(", "").replace(")", "")
                lines.append(f"{toc_idx}. [{title}](#{anchor})")
                toc_idx += 1
            lines.append("")
            lines.append("---")
            lines.append("")

        # Sections
        for section in self.sections:
            section_type = section["type"]

            if section_type == "custom":
                lines.extend(_render_custom(section))
            elif section_type == "fit":
                lines.extend(_render_fit(section))
            elif section_type == "peaks":
                lines.extend(_render_peaks(section))
            elif section_type == "stats":
                lines.extend(_render_stats(section))
            elif section_type == "xrd":
                lines.extend(_render_xrd(section))
            elif section_type == "figure":
                lines.extend(_render_figure(section))
            elif section_type == "table":
                lines.extend(_render_standalone_table(section))

            lines.append("")

        # Summary
        lines.append("---")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(self.summary())
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by Praxis.*")

        md = "\n".join(lines)

        if output_path is not None:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(md, encoding="utf-8")
            print(f"[Praxis] Report written to {p}")

        return md

    def summary(self) -> str:
        """Quick one-paragraph summary of all analyses performed."""
        parts = []

        for section in self.sections:
            st = section["type"]
            if st == "fit":
                model = section.get("model", "unknown")
                r2 = section.get("r_squared", 0)
                parts.append(f"{section['title']}: {model} model (R2={r2:.4f})")
            elif st == "peaks":
                n = section.get("n_peaks", 0)
                parts.append(f"{section['title']}: {n} peak(s) detected")
            elif st == "stats":
                parts.append(f"{section['title']}: descriptive statistics computed")
            elif st == "xrd":
                n = section.get("n_peaks", 0)
                wl = section.get("wavelength_name", "")
                parts.append(f"{section['title']}: {n} peak(s), {wl}")
            elif st == "custom":
                parts.append(section["title"])
            elif st == "table":
                cap = section.get("caption", "Data table")
                parts.append(cap)

        if not parts:
            return "No analyses recorded."

        return (
            f"This report contains {len(self.sections)} section(s). "
            + ". ".join(parts)
            + "."
        )


# ---------------------------------------------------------------------------
# Section renderers (private)
# ---------------------------------------------------------------------------

def _render_custom(section: dict) -> list[str]:
    lines = [f"## {section['title']}", "", section["content"], ""]
    for fig in section.get("figures", []):
        lines.append(f"![{section['title']}]({fig})")
        lines.append("")
    for tbl in section.get("tables", []):
        data = tbl.get("data", tbl)
        caption = tbl.get("caption", "")
        headers, rows = _parse_table_data(data)
        if caption:
            lines.append(f"*{caption}*")
            lines.append("")
        lines.extend(_format_md_table(headers, rows))
        lines.append("")
    return lines


def _render_fit(section: dict) -> list[str]:
    lines = [
        f"## {section['title']}",
        "",
        f"**Model:** {section['model']}",
        "",
        f"| Metric | Value |",
        f"| --- | --- |",
        f"| R2 | {section['r_squared']:.6f} |",
        f"| Reduced chi2 | {section['reduced_chi_sq']:.4e} |",
        f"| AIC | {section['aic']:.2f} |",
        f"| BIC | {section['bic']:.2f} |",
        "",
        "**Fitted Parameters:**",
        "",
    ]
    tbl = section["params_table"]
    lines.extend(_format_md_table(tbl["headers"], tbl["rows"]))
    return lines


def _render_peaks(section: dict) -> list[str]:
    lines = [
        f"## {section['title']}",
        "",
        f"**Peaks detected:** {section['n_peaks']}",
        "",
    ]
    tbl = section["table"]
    lines.extend(_format_md_table(tbl["headers"], tbl["rows"]))
    return lines


def _render_stats(section: dict) -> list[str]:
    lines = [f"## {section['title']}", ""]
    tbl = section["table"]
    lines.extend(_format_md_table(tbl["headers"], tbl["rows"]))
    return lines


def _render_xrd(section: dict) -> list[str]:
    lines = [
        f"## {section['title']}",
        "",
        f"**Wavelength:** {section['wavelength']:.4f} A ({section['wavelength_name']})",
        f"**Peaks indexed:** {section['n_peaks']}",
        "",
    ]
    tbl = section["table"]
    lines.extend(_format_md_table(tbl["headers"], tbl["rows"]))

    if "wh_slope" in section:
        lines.append("")
        lines.append("**Williamson-Hall Analysis:**")
        lines.append("")
        lines.append(f"| Parameter | Value |")
        lines.append(f"| --- | --- |")
        lines.append(f"| Slope (strain) | {section['wh_slope']:.6g} |")
        lines.append(f"| Intercept (size) | {section['wh_intercept']:.6g} |")
        lines.append(f"| R2 | {section['wh_r_squared']:.4f} |")

    return lines


def _render_figure(section: dict) -> list[str]:
    lines = []
    caption = section.get("caption", "")
    lines.append(f"![{caption}]({section['path']})")
    if caption:
        lines.append(f"*{caption}*")
    lines.append("")
    return lines


def _render_standalone_table(section: dict) -> list[str]:
    lines = []
    caption = section.get("caption", "")
    if caption:
        lines.append(f"### {caption}")
        lines.append("")
    lines.extend(_format_md_table(section["headers"], section["rows"]))
    return lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Render a markdown table from headers and row data."""
    if not headers:
        return []

    lines = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        # Pad row to match header length
        padded = list(row) + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(str(c) for c in padded[:len(headers)]) + " |")
    return lines


def _parse_table_data(data: Any) -> tuple[list[str], list[list[str]]]:
    """Convert a DataFrame or dict to (headers, rows) lists.

    Supports:
    - dict of lists: keys become headers, values become columns.
    - pandas DataFrame: uses df.columns and df.values.
    - list of dicts: keys from first dict become headers.
    """
    # pandas DataFrame
    try:
        import pandas as pd
        if isinstance(data, pd.DataFrame):
            headers = [str(c) for c in data.columns]
            rows = [[str(v) for v in row] for row in data.values]
            return headers, rows
    except ImportError:
        pass

    if isinstance(data, dict):
        headers = list(data.keys())
        # dict of lists (column-oriented)
        if headers and isinstance(data[headers[0]], (list, tuple)):
            n_rows = max(len(v) for v in data.values())
            rows = []
            for i in range(n_rows):
                row = []
                for h in headers:
                    col = data[h]
                    row.append(str(col[i]) if i < len(col) else "")
                rows.append(row)
            return [str(h) for h in headers], rows
        # dict of scalars (single row)
        return [str(h) for h in headers], [[str(v) for v in data.values()]]

    if isinstance(data, list) and data and isinstance(data[0], dict):
        headers = list(data[0].keys())
        rows = [[str(row.get(h, "")) for h in headers] for row in data]
        return [str(h) for h in headers], rows

    return [], []

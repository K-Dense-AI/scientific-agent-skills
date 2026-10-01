"""Dependency-free help and exact-stack synthetic tests for local GeoPandas CLIs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from importlib.metadata import version
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "geopandas"
SCRIPTS = SKILL_ROOT / "scripts"
CLI_NAMES = (
    "crs_reprojection_plan.py",
    "export_plan.py",
    "geometry_validity_report.py",
    "sensitive_coordinates_checklist.py",
    "spatial_join_audit.py",
    "vector_inventory.py",
)
PINNED = {
    "geopandas": "1.2.0",
    "numpy": "2.5.3",
    "packaging": "26.3",
    "pandas": "3.0.6",
    "pyarrow": "25.0.1",
    "pyogrio": "0.13.0",
    "pyproj": "3.8.0",
    "shapely": "2.1.2",
}


def run_script(
    name: str,
    *arguments: str,
    cwd: Path | None = None,
    no_site: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PROJ_NETWORK"] = "OFF"
    command = [sys.executable]
    if no_site:
        command.append("-S")
    command.extend([str(SCRIPTS / name), *map(str, arguments)])
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        cwd=cwd,
        env=environment,
        text=True,
        timeout=90,
    )


def payload(result: subprocess.CompletedProcess[str]) -> dict:
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"invalid JSON\nstdout={result.stdout}\nstderr={result.stderr}"
        ) from exc


def require_stack() -> tuple[object, object, object, object, object]:
    try:
        import geopandas
        import pyarrow
        import pyogrio
        import pyproj
        import shapely
    except ImportError as exc:
        raise unittest.SkipTest("run with the pinned GeoPandas stack") from exc
    return geopandas, pyarrow, pyogrio, pyproj, shapely


def write_join_fixtures(root: Path) -> tuple[Path, Path]:
    geopandas, _, _, _, shapely = require_stack()
    from shapely.geometry import Point, box

    points = geopandas.GeoDataFrame(
        {
            "point_id": ["p-1", "p-2", "p-3"],
            "geometry": [Point(0.5, 0.5), Point(1.0, 0.5), Point(3.0, 3.0)],
        },
        crs="EPSG:3857",
    )
    zones = geopandas.GeoDataFrame(
        {
            "zone_id": ["duplicate", "duplicate"],
            "geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1)],
        },
        crs="EPSG:3857",
    )
    points_path = root / "synthetic-points.geojson"
    zones_path = root / "synthetic-zones.geojson"
    points.to_file(points_path, driver="GeoJSON", engine="pyogrio", index=False)
    zones.to_file(zones_path, driver="GeoJSON", engine="pyogrio", index=False)
    del shapely
    return points_path, zones_path


class DependencyFreeHelpTests(unittest.TestCase):
    def test_all_cli_helps_succeed_without_site_packages(self) -> None:
        for name in CLI_NAMES:
            with self.subTest(name=name):
                result = run_script(name, "--help", no_site=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.casefold())

    def test_nonlocal_and_archive_paths_fail_closed(self) -> None:
        remote = run_script("vector_inventory.py", "https://example.invalid/data.gpkg")
        self.assertEqual(remote.returncode, 2)
        self.assertIn("local path", payload(remote)["error"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data.zip").write_bytes(b"synthetic")
            archive = run_script(
                "vector_inventory.py",
                "data.zip",
                "--root",
                ".",
                cwd=root,
            )
            self.assertEqual(archive.returncode, 2)
            self.assertIn("archive", payload(archive)["error"])


class ExactPinnedStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gpd, cls.pyarrow, cls.pyogrio, cls.pyproj, cls.shapely = require_stack()

    def test_exact_package_and_native_versions(self) -> None:
        self.assertEqual({name: version(name) for name in PINNED}, PINNED)
        self.assertEqual(
            ".".join(map(str, self.pyogrio.__gdal_version__)),
            "3.12.4",
        )
        self.assertEqual(self.shapely.geos_version_string, "3.13.1")
        self.assertEqual(self.pyproj.proj_version_str, "9.8.1")

    def test_core_geometry_join_overlay_dissolve_and_arrow_apis(self) -> None:
        from shapely.geometry import Point, Polygon, box

        coverage = self.gpd.GeoDataFrame(
            {
                "group": ["a", "a"],
                "geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1)],
            },
            crs="EPSG:3857",
        )
        points = self.gpd.GeoDataFrame(
            {"geometry": [Point(0.5, 0.5), Point(1.0, 0.5)]},
            crs=coverage.crs,
        )
        self.assertTrue(coverage.geometry.is_valid_coverage())
        self.assertTrue(coverage.geometry.union_all(method="coverage").is_valid)
        dissolved = coverage.dissolve(
            by="group",
            method="unary",
            grid_size=0.001,
        )
        self.assertTrue(dissolved.geometry.is_valid.all())
        self.assertEqual(
            len(self.gpd.sjoin(points, coverage, predicate="intersects")),
            3,
        )
        self.assertEqual(
            len(
                self.gpd.overlay(
                    coverage.iloc[[0]],
                    coverage.iloc[[1]],
                    how="union",
                    keep_geom_type=False,
                )
            ),
            3,
        )
        self.assertEqual(
            len(self.gpd.clip(points, (0.0, 0.0, 1.0, 1.0))),
            2,
        )

        invalid = self.gpd.GeoSeries(
            [Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])],
            crs=coverage.crs,
        )
        repaired = invalid.make_valid(method="structure", keep_collapsed=True)
        self.assertTrue(repaired.is_valid.all())
        snapped = coverage.geometry.set_precision(0.001)
        self.assertEqual(float(snapped.get_precision().min()), 0.001)

        arrow_table = coverage.to_arrow(geometry_encoding="WKB")
        arrow_roundtrip = self.gpd.GeoDataFrame.from_arrow(arrow_table)
        self.assertEqual(len(arrow_roundtrip), len(coverage))
        self.assertTrue(arrow_roundtrip.crs.equals(coverage.crs))

    def test_geoparquet_11_bbox_roundtrip(self) -> None:
        from shapely.geometry import box

        frame = self.gpd.GeoDataFrame(
            {
                "feature_id": ["a", "b"],
                "geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1)],
            },
            crs="EPSG:3857",
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.parquet"
            frame.to_parquet(
                path,
                index=False,
                schema_version="1.1.0",
                geometry_encoding="WKB",
                write_covering_bbox=True,
            )
            filtered = self.gpd.read_parquet(path, bbox=(0, 0, 0.5, 0.5))
            self.assertEqual(filtered["feature_id"].tolist(), ["a"])


class LocalCliSyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        require_stack()

    def test_inventory_and_join_cardinality_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            points, zones = write_join_fixtures(root)
            inventory = run_script(
                "vector_inventory.py",
                points.name,
                "--root",
                ".",
                "--max-features",
                "10",
                cwd=root,
            )
            self.assertEqual(inventory.returncode, 0, inventory.stderr)
            inventory_report = payload(inventory)
            self.assertFalse(inventory_report["coordinates_emitted"])
            self.assertFalse(
                inventory_report["technical_inventory"]["feature_data_loaded"]
            )
            self.assertNotIn(str(root), inventory.stdout)
            self.assertNotIn("point_id", inventory.stdout)

            intersects = run_script(
                "spatial_join_audit.py",
                points.name,
                zones.name,
                "--root",
                ".",
                "--predicate",
                "intersects",
                "--left-id",
                "point_id",
                "--right-id",
                "zone_id",
                "--max-features",
                "10",
                cwd=root,
            )
            self.assertEqual(intersects.returncode, 0, intersects.stderr)
            joined = payload(intersects)
            self.assertEqual(joined["pair_audit"]["pair_count"], 3)
            self.assertEqual(
                joined["pair_audit"]["left"]["features_with_multiple_matches"],
                1,
            )
            self.assertEqual(
                joined["right"]["stable_id_audit"]["duplicate_rows"],
                2,
            )
            self.assertTrue(joined["pair_audit"]["many_to_many_observed"])
            self.assertNotIn('"duplicate"', intersects.stdout)

            within = run_script(
                "spatial_join_audit.py",
                points.name,
                zones.name,
                "--root",
                ".",
                "--predicate",
                "within",
                "--max-features",
                "10",
                cwd=root,
            )
            self.assertEqual(within.returncode, 0, within.stderr)
            self.assertEqual(payload(within)["pair_audit"]["pair_count"], 1)

    def test_validity_dry_run_and_new_output_only(self) -> None:
        geopandas, _, _, _, _ = require_stack()
        from shapely.geometry import Polygon

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "invalid.gpkg"
            frame = geopandas.GeoDataFrame(
                {
                    "feature_id": ["invalid", "empty", "missing"],
                    "geometry": [
                        Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)]),
                        Polygon(),
                        None,
                    ],
                },
                crs="EPSG:3857",
            )
            frame.to_file(
                source,
                layer="input",
                driver="GPKG",
                engine="pyogrio",
                index=False,
            )
            before_bytes = source.read_bytes()
            dry = run_script(
                "geometry_validity_report.py",
                source.name,
                "--root",
                ".",
                "--layer",
                "input",
                "--id-column",
                "feature_id",
                "--method",
                "structure",
                "--max-features",
                "10",
                cwd=root,
            )
            self.assertEqual(dry.returncode, 0, dry.stderr)
            dry_report = payload(dry)
            self.assertTrue(dry_report["dry_run"])
            self.assertEqual(dry_report["before"]["invalid"], 1)
            self.assertEqual(dry_report["simulated_after"]["invalid"], 0)
            self.assertEqual(source.read_bytes(), before_bytes)

            written = run_script(
                "geometry_validity_report.py",
                source.name,
                "--root",
                ".",
                "--layer",
                "input",
                "--method",
                "structure",
                "--repair-output",
                "repaired.gpkg",
                "--max-features",
                "10",
                cwd=root,
            )
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertTrue((root / "repaired.gpkg").is_file())
            repaired_bytes = (root / "repaired.gpkg").read_bytes()
            second = run_script(
                "geometry_validity_report.py",
                source.name,
                "--root",
                ".",
                "--layer",
                "input",
                "--method",
                "structure",
                "--repair-output",
                "repaired.gpkg",
                "--max-features",
                "10",
                cwd=root,
            )
            self.assertEqual(second.returncode, 2)
            self.assertEqual((root / "repaired.gpkg").read_bytes(), repaired_bytes)

    def test_crs_export_and_privacy_planners(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            points, _ = write_join_fixtures(root)
            crs = run_script(
                "crs_reprojection_plan.py",
                "--source-crs",
                "EPSG:4326",
                "--target-crs",
                "EPSG:32631",
                "--operation",
                "distance",
                "--bbox",
                "-1",
                "40",
                "1",
                "42",
                cwd=root,
            )
            self.assertEqual(crs.returncode, 0, crs.stderr)
            crs_report = payload(crs)
            self.assertTrue(crs_report["source_crs"]["geographic"])
            self.assertTrue(crs_report["target_crs"]["projected"])
            self.assertFalse(crs_report["operation_policy"]["proj_network_enabled"])
            self.assertFalse(crs_report["bbox"]["values_emitted"])

            dateline = run_script(
                "crs_reprojection_plan.py",
                "--source-crs",
                "EPSG:4326",
                "--target-crs",
                "EPSG:3857",
                "--bbox",
                "170",
                "-10",
                "-170",
                "10",
                cwd=root,
            )
            self.assertIn(dateline.returncode, (0, 2))
            self.assertTrue(payload(dateline)["bbox"]["crosses_antimeridian"])

            export = run_script(
                "export_plan.py",
                points.name,
                "result.parquet",
                "--root",
                ".",
                "--format",
                "geoparquet",
                "--stable-id-column",
                "point_id",
                "--id-unique-verified",
                cwd=root,
            )
            self.assertEqual(export.returncode, 0, export.stderr)
            export_report = payload(export)
            self.assertFalse(export_report["executed"])
            self.assertFalse((root / "result.parquet").exists())
            self.assertTrue(
                export_report["geoparquet"]["default_stable_contract"]
            )

            bad_schema = run_script(
                "export_plan.py",
                points.name,
                "native.parquet",
                "--root",
                ".",
                "--stable-id-column",
                "point_id",
                "--id-unique-verified",
                "--geometry-encoding",
                "geoarrow",
                "--schema-version",
                "1.0.0",
                cwd=root,
            )
            self.assertEqual(bad_schema.returncode, 2)
            self.assertIn(
                "schema 1.1.0",
                " ".join(payload(bad_schema)["blockers"]),
            )

            blocked = run_script(
                "sensitive_coordinates_checklist.py",
                "--public-output",
                "--precise-points",
                "--contains-addresses",
                cwd=root,
            )
            self.assertEqual(blocked.returncode, 2)
            self.assertTrue(payload(blocked)["blockers"])

            ready = run_script(
                "sensitive_coordinates_checklist.py",
                "--public-output",
                "--precise-points",
                "--contains-addresses",
                "--generalization",
                "aggregate",
                "--generalization",
                "remove-sensitive-fields",
                "--generalization",
                "suppress-small-groups",
                "--minimum-group-size",
                "10",
                "--direct-identifiers-removed",
                "--attribute-review-complete",
                "--reidentification-review-complete",
                "--visual-review-complete",
                "--provenance-recorded",
                "--tile-and-cdn-access-disabled",
                cwd=root,
            )
            self.assertEqual(ready.returncode, 0, ready.stderr)
            self.assertTrue(payload(ready)["ok"])


class Release120RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gpd, cls.pa, cls.pyogrio, _, _ = require_stack()

    def test_geoparquet_default_attrs_and_native_point_filter(self) -> None:
        from pyarrow import parquet
        from shapely import Point

        frame = self.gpd.GeoDataFrame(
            {"feature_id": [1, 2], "geometry": [Point(0, 0), Point(2, 2)]},
            crs="EPSG:3857",
        )
        frame.attrs = {"private_note": "DO_NOT_EMIT_STUDY_LOCATION"}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "points.parquet"
            frame.to_parquet(path, index=False)
            metadata = json.loads(parquet.read_metadata(path).metadata[b"geo"])
            self.assertEqual(metadata["version"], "1.1.0")
            self.assertEqual(self.gpd.read_parquet(path).attrs, frame.attrs)
            result = run_script("vector_inventory.py", path.name, cwd=root)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(payload(result)["technical_inventory"]["dataframe_attrs_present"])
            self.assertNotIn("DO_NOT_EMIT", result.stdout)
            frame.to_parquet(path, geometry_encoding="geoarrow", schema_version="1.1.0")
            selected = self.gpd.read_parquet(path, bbox=(-1, -1, 1, 1))
            self.assertEqual(selected.feature_id.tolist(), [1])

    def test_geoparquet_20_is_explicit_wkb_only(self) -> None:
        from shapely import box

        frame = self.gpd.GeoDataFrame(
            {"feature_id": [1, 2], "geometry": [box(0, 0, 1, 1), box(5, 5, 6, 6)]},
            crs="EPSG:3857",
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "logical.parquet"
            frame.to_parquet(path, schema_version="2.0.0", geometry_encoding="WKB")
            selected = self.gpd.read_parquet(path, bbox=(0, 0, 0.5, 0.5))
            self.assertEqual(selected.feature_id.tolist(), [1])
            with self.assertRaises(ValueError):
                frame.to_parquet(path, schema_version="2.0.0", geometry_encoding="geoarrow")

    def test_inventory_rejects_absent_primary_geometry(self) -> None:
        from pyarrow import parquet

        metadata = {"version": "1.1.0", "primary_column": "missing", "columns": {}}
        table = self.pa.table({"value": [1]}).replace_schema_metadata(
            {b"geo": json.dumps(metadata).encode()}
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parquet.write_table(table, root / "bad.parquet")
            result = run_script("vector_inventory.py", "bad.parquet", cwd=root)
            self.assertEqual(result.returncode, 2)
            self.assertIn("primary geometry", payload(result)["error"])

    def test_crs_bbox_is_degrees_not_projected_units(self) -> None:
        for source, bbox in (
            ("EPSG:3857", (0, 0, 1, 1)),
            ("EPSG:4807", (0, 0, 1, 1)),  # geographic, but grad axes
            ("EPSG:32631", (500000, 4000000, 501000, 4001000)),
            ("EPSG:4326", (0, -95, 1, 20)),
            ("EPSG:4326", (-181, 0, 10, 20)),
        ):
            with self.subTest(source=source, bbox=bbox):
                result = run_script(
                    "crs_reprojection_plan.py", "--source-crs", source,
                    "--target-crs", "EPSG:32631", "--bbox", *map(str, bbox),
                )
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertFalse(payload(result)["network_accessed"])

    def test_fixed_precision_buffer_and_query_orientation(self) -> None:
        from shapely import Point, box

        polygons = self.gpd.GeoSeries([box(0, 0, 1, 1), box(1, 0, 2, 1)], crs="EPSG:3857")
        queries = self.gpd.GeoSeries([Point(.5, .5), Point(1, .5), Point(4, 4)])
        indices = polygons.sindex.query(queries, predicate="intersects", output_format="indices")
        dense = polygons.sindex.query(queries, predicate="intersects", output_format="dense")
        self.assertEqual(indices.tolist(), [[0, 1, 1], [0, 0, 1]])
        self.assertEqual(dense.shape, (2, 3))
        result = polygons.intersection(box(.46, 0, 1.54, 1), grid_size=.1)
        self.assertEqual(result.area.tolist(), [.5, .5])
        buffered = self.gpd.GeoSeries([Point(0, 0)], crs=polygons.crs).buffer(1, quad_segs=4)
        self.assertEqual(len(buffered.iloc[0].exterior.coords), 17)

    def test_metadata_alias_and_reserved_join_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            points, zones = write_join_fixtures(root)
            info = self.gpd.read_file_info(points)
            self.assertEqual(info["features"], 3)
            detailed = self.pyogrio.read_info(
                points, force_feature_count=False, force_total_bounds=False,
            )
            self.assertEqual(detailed["features"], 3)
            self.assertIn("GPKG", self.pyogrio.list_drivers(append=True))
            for path in (points, zones):
                frame = self.gpd.read_file(path)
                frame["_audit_left_row"] = 7
                frame.to_file(path, driver="GeoJSON", engine="pyogrio", index=False)
            result = run_script(
                "spatial_join_audit.py", points.name, zones.name,
                "--on-attribute", "_audit_left_row", cwd=root,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("reserved audit", " ".join(payload(result)["blockers"]))

    def test_plotting_dictionary_palette_and_labels(self) -> None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import to_rgba
        from shapely import box

        frame = self.gpd.GeoDataFrame(
            {"category": ["A", "B"], "geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1)]},
            crs="EPSG:3857",
        )
        fig, ax = plt.subplots()
        try:
            frame.plot(
                ax=ax, column="category", categorical=True,
                cmap={"A": "#4477AA", "B": "#EE6677"}, legend=True, tiles=False,
            )
            colors = [tuple(color) for collection in ax.collections for color in collection.get_facecolors()]
            self.assertIn(to_rgba("#4477AA"), colors)
            self.assertIn(to_rgba("#EE6677"), colors)
            self.assertEqual([item.get_text() for item in ax.get_legend().get_texts()], ["A", "B"])
            self.assertTrue(ax.get_xlabel())
            fig.canvas.draw()
        finally:
            plt.close(fig)

    def test_join_distance_ties_and_attribute_restriction(self) -> None:
        from shapely import Point

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = self.gpd.GeoDataFrame(
                {"survey": ["A", "B"], "geometry": [Point(0, 0), Point(10, 0)]},
                crs="EPSG:3857",
            )
            right = self.gpd.GeoDataFrame(
                {"survey": ["A", "B", "B"],
                 "geometry": [Point(-1, 0), Point(1, 0), Point(10, 0)]},
                crs=left.crs,
            )
            left.to_file(root / "left.gpkg", engine="pyogrio", index=False)
            right.to_file(root / "right.gpkg", engine="pyogrio", index=False)
            for options, expected in (
                (("--mode", "nearest", "--max-distance", "2"), 3),
                (("--mode", "nearest", "--max-distance", "2", "--exclusive"), 2),
                (("--predicate", "dwithin", "--distance", "1", "--on-attribute", "survey"), 2),
            ):
                with self.subTest(options=options):
                    result = run_script(
                        "spatial_join_audit.py", "left.gpkg", "right.gpkg", *options,
                        cwd=root,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertEqual(payload(result)["pair_audit"]["pair_count"], expected)


if __name__ == "__main__":
    unittest.main()

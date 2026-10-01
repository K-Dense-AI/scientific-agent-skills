"""Small synthetic fixtures for current pixel, writer, and privacy semantics."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "pydicom"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_scripts import require_test_stack, run_script, write_fixture


class CurrentAPIRegressionTests(unittest.TestCase):
    def setUp(self):
        self.pydicom, self.np = require_test_stack()

    def test_signed_pixels_writer_json_and_extended_offsets(self):
        from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
        from pydicom.encaps import encapsulate_extended, generate_frames, get_frame
        from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid
        from pydicom.pixels import apply_modality_lut, iter_pixels, pixel_array

        arr = self.np.array([[[-512, -1], [0, 511]], [[3, 4], [5, 6]]], dtype=self.np.int16)
        ds = FileDataset(None, {}, file_meta=FileMetaDataset(), preamble=b"\0" * 128)
        ds.SOPClassUID = SecondaryCaptureImageStorage
        ds.SOPInstanceUID = generate_uid()
        previous = ds.SOPInstanceUID
        ds.set_pixel_data(arr, "MONOCHROME2", bits_stored=12)
        self.assertNotEqual(previous, ds.SOPInstanceUID)
        self.assertEqual(ds.file_meta.TransferSyntaxUID, ExplicitVRLittleEndian)
        self.assertEqual(ds.file_meta.MediaStorageSOPInstanceUID, ds.SOPInstanceUID)
        self.assertEqual(ds.PixelRepresentation, 1)
        ds.RescaleSlope, ds.RescaleIntercept = 2, -1024
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "signed.dcm"
            self.pydicom.dcmwrite(path, ds, enforce_file_format=True, overwrite=False)
            with self.assertRaises(FileExistsError):
                self.pydicom.dcmwrite(path, ds, enforce_file_format=True, overwrite=False)
            self.np.testing.assert_array_equal(pixel_array(path, index=1), arr[1])
            self.np.testing.assert_array_equal(list(iter_pixels(path, indices=[1, 0]))[1], arr[0])
            readback = self.pydicom.dcmread(path)
            self.np.testing.assert_array_equal(apply_modality_lut(readback.pixel_array, readback), arr * 2 - 1024)
            self.assertEqual(Dataset.from_json(readback.to_json()).PixelData, readback.PixelData)
        frames = [b"abcd", b"uvwxyz"]  # Encapsulation mechanics; not codec bitstreams.
        payload, offsets, lengths = encapsulate_extended(frames)
        self.assertEqual(get_frame(payload, 1, number_of_frames=2, extended_offsets=(offsets, lengths)), frames[1])
        self.assertEqual(list(generate_frames(payload, extended_offsets=(offsets, lengths))), frames)

    def test_lossless_codec_roundtrips_against_known_signed_pixels(self):
        from pydicom.dataset import Dataset
        from pydicom.pixels import get_decoder, get_encoder, pixel_array
        from pydicom.uid import ExplicitVRLittleEndian, JPEG2000Lossless, JPEGLSLossless, RLELossless

        pixels = (self.np.arange(2 * 32 * 32) % 1024 - 512).astype(self.np.int16).reshape(2, 32, 32)
        source = Dataset()
        source.set_pixel_data(pixels, "MONOCHROME2", bits_stored=12)
        for syntax in (RLELossless, JPEGLSLossless, JPEG2000Lossless):
            encoder = get_encoder(syntax)
            if not encoder.is_available:
                self.skipTest(f"missing optional encoder for {syntax.name}")
            for plugin in encoder.available_plugins:
                with self.subTest(syntax=syntax.name, encoder=plugin):
                    ds = deepcopy(source)
                    prior_uid = ds.SOPInstanceUID
                    ds.compress(syntax, encoding_plugin=plugin)
                    self.assertNotEqual(prior_uid, ds.SOPInstanceUID)
                    self.assertEqual(ds.file_meta.MediaStorageSOPInstanceUID, ds.SOPInstanceUID)
                    for decoder in get_decoder(syntax).available_plugins:
                        self.np.testing.assert_array_equal(pixel_array(ds, decoding_plugin=decoder), pixels)
                    compressed_uid = ds.SOPInstanceUID
                    chosen_decoder = "pyjpegls" if syntax == JPEGLSLossless else get_decoder(syntax).available_plugins[0]
                    ds.decompress(decoding_plugin=chosen_decoder)
                    self.assertEqual(ds.file_meta.TransferSyntaxUID, ExplicitVRLittleEndian)
                    self.assertNotEqual(compressed_uid, ds.SOPInstanceUID)
                    self.np.testing.assert_array_equal(ds.pixel_array, pixels)

    def test_ybr_full_raw_and_rgb_contract(self):
        from pydicom.dataset import Dataset
        from pydicom.pixels import pixel_array
        ds = Dataset()
        ybr = self.np.array([[[0, 128, 128], [255, 128, 128]]], dtype=self.np.uint8)
        ds.set_pixel_data(ybr, "YBR_FULL", bits_stored=8)
        self.np.testing.assert_array_equal(pixel_array(ds, raw=True), ybr)
        self.np.testing.assert_array_equal(pixel_array(ds), [[[0, 0, 0], [255, 255, 255]]])

    def test_explicit_presentation_inversion_is_not_applied_twice(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "image.dcm"
            write_fixture(path, frames=1)
            ds = self.pydicom.dcmread(path)
            ds.PhotometricInterpretation = "MONOCHROME1"
            ds.PresentationLUTShape = "INVERSE"
            ds.save_as(path, enforce_file_format=True)
            result = run_script("dicom_to_image.py", path.name, "preview.png", "--acknowledge-pixel-phi", cwd=root)
            self.assertEqual(result.returncode, 0, result.stdout)
            with Image.open(root / "preview.png") as image:
                self.assertEqual(image.getpixel((0, 0)), 255)
                self.assertEqual(image.getpixel((2, 1)), 0)

    def test_unsupported_functional_groups_and_partial_ybr_fail_before_output(self):
        from pydicom.dataset import Dataset
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "image.dcm"
            write_fixture(path)
            original = self.pydicom.dcmread(path)
            cases = []
            ds = deepcopy(original)
            item = Dataset()
            transformation = Dataset()
            transformation.RescaleSlope, transformation.RescaleIntercept = 2, -100
            item.PixelValueTransformationSequence = [transformation]
            ds.SharedFunctionalGroupsSequence = [item]
            cases.append(ds)
            ds = deepcopy(original)
            ds.PhotometricInterpretation = "YBR_PARTIAL_422"
            cases.append(ds)
            for ds in cases:
                ds.save_as(path, enforce_file_format=True)
                result = run_script("dicom_to_image.py", path.name, "preview.png", "--acknowledge-pixel-phi", cwd=root)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertFalse((root / "preview.png").exists())

    def test_rescale_pair_and_modality_before_voi(self):
        from dicom_to_image import _apply_grayscale_transforms
        from _common import ToolError
        from pydicom.dataset import Dataset
        ds = Dataset()
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsStored, ds.PixelRepresentation = 12, 1
        ds.RescaleSlope = 2
        pixels = self.np.array([-512, 0, 511], dtype=self.np.int16)
        with self.assertRaises(ToolError):
            _apply_grayscale_transforms(pixels, ds, modality_transform="auto", voi="auto", voi_index=0)
        ds.RescaleIntercept = -1024
        ds.WindowCenter, ds.WindowWidth = -1024, 2048
        with self.assertRaises(ToolError):
            _apply_grayscale_transforms(pixels, ds, modality_transform="none", voi="auto", voi_index=0)
        result, applied = _apply_grayscale_transforms(pixels, ds, modality_transform="auto", voi="window", voi_index=0)
        self.assertEqual(applied, ["modality LUT/rescale", "window"])
        self.assertTrue(self.np.all(self.np.diff(result) > 0))

    def test_device_uid_and_nested_keep_sequence_are_processed(self):
        from _common import starter_profile
        from anonymize_dicom import transform_dataset
        from pydicom.dataset import Dataset
        from pydicom.uid import SecondaryCaptureImageStorage, generate_uid
        ds = Dataset()
        ds.SOPClassUID = SecondaryCaptureImageStorage
        original = generate_uid()
        ds.DeviceUID = original
        item = Dataset()
        item.PatientName = "SYNTHETIC^NESTED"
        item.DeviceUID = original
        ds.ReferencedImageSequence = [item]
        profile = starter_profile()
        profile["actions"]["ReferencedImageSequence"] = "keep"
        report, mapping = transform_dataset(ds, profile=profile, key=b"x" * 32, scope="test", date_shift_days=None, retain_times=False, allow_private_retention=False, allow_date_retention=False, max_elements=100)
        self.assertNotEqual(ds.DeviceUID, original)
        self.assertEqual(ds.DeviceUID, ds.ReferencedImageSequence[0].DeviceUID)
        self.assertNotEqual(str(ds.ReferencedImageSequence[0].PatientName), "SYNTHETIC^NESTED")
        self.assertEqual(ds.SOPClassUID, SecondaryCaptureImageStorage)
        self.assertEqual(mapping[original], ds.DeviceUID)

    def test_structural_uid_override_rejected_and_lossy_status_preserved(self):
        from _common import ToolError, starter_profile
        from anonymize_dicom import transform_dataset
        from extract_metadata import allowlisted_record
        from pydicom.uid import generate_uid
        from dicom_inventory import inspect_dataset
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.dcm"
            write_fixture(path)
            ds = self.pydicom.dcmread(path, stop_before_pixels=True)
            profile = starter_profile()
            profile["actions"]["SOPClassUID"] = "uid"
            with self.assertRaises(ToolError):
                transform_dataset(ds, profile=profile, key=b"x" * 32, scope="test", date_shift_days=None, retain_times=False, allow_private_retention=False, allow_date_retention=False, max_elements=100)
            for lossy in ("00", "01"):
                ds.LossyImageCompression = lossy
                self.assertEqual(allowlisted_record(ds, file_id="1")["lossy_image_compression"], lossy)
            ds.file_meta.TransferSyntaxUID = generate_uid()
            record = inspect_dataset(ds, file_id="1", file_size=100, max_frames=100, max_decompressed_bytes=10000, forced_read=False)
            self.assertIn("transfer_syntax_unknown", [x["code"] for x in record["issues"]])
            self.assertIsNone(allowlisted_record(ds, file_id="1")["transfer_syntax"]["compressed"])

    def test_uid_map_report_cannot_overwrite_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            key = root / "secret.key"
            key.write_bytes(b"x" * 32)
            key.chmod(0o600)
            (root / "map.json").write_text(json.dumps({"entries": []}))
            result = run_script("uid_mapping_validator.py", "map.json", "--uid-key-file", key.name, "--uid-scope", "test", "--output", key.name, "--force", cwd=root)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(key.read_bytes(), b"x" * 32)

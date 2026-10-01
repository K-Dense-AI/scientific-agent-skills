# NMRPipe binary fixture

`nmrpipe_1d_time.fid` is an unchanged, 2,176-byte public nmrglue test fixture:

- Source: https://github.com/jjhelmus/nmrglue/blob/v0.12/nmrglue/fileio/tests/data/nmrpipe_1d_time.fid
- Release tag commit: `f4a2c1f3cbb499e6b9d91d38cb5355776fe0b047`
- SHA-256: `3f88650d2135a3e4bd57ef15e0a03ba16b5788ae343e44a5e8251a9dbaa23d64`
- License: upstream BSD 3-clause text retained in `nmrglue-LICENSE.txt`.
- Retrieved: 2026-10-01.

The upstream [creation script](https://github.com/jjhelmus/nmrglue/blob/v0.12/nmrglue/fileio/tests/create_test_data_nmrpipe.sh)
uses `simTimeND` and `nmrPipe -fn SET` to write 16 complex time-domain samples,
starting with `1-1j`, `2-2j`, then zeros. The spectral width is 50,000 Hz,
observation frequency 500 MHz, and carrier 99 ppm. This is a binary compatibility
fixture, not an experimental sample or validation of a spectrometer.

Tests consume the stored file offline. They do not execute native NMRPipe.

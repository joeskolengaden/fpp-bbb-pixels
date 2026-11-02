# Releasing (maintainers)

How FPP does it: tagged releases on GitHub, built by CI. We do the same for the overlay.
1. Update `VERSION` and add a `## X.Y.Z (date)` section to `CHANGELOG.md`.
2. `bash scripts/bundle-spipixels.sh` (refresh the bundled SPI plugin from `plugins/SPIPixels`), commit.
3. `FPP_SRC=<stock FPP 5.4.1 checkout> bash scripts/check-all.sh` must print `0 failure(s)`.
4. Prove it on a board: install the bundle from `bash scripts/build-release.sh`, run `doctor.sh`, `selftest.sh` and the `hwtest/` regression (`live_presets.sh`, `live_spipixels.sh`, `live_custom.py`, `wire_check.py`).
5. `git tag vX.Y.Z && git push origin main vX.Y.Z`. The `release` workflow re-runs every check, builds `fpp-bbb-pixels-X.Y.Z.tar.gz` + `SHA256SUMS` and creates the GitHub Release.
6. Verify the published assets: download, `shasum -a 256 -c SHA256SUMS`, `install.sh --check` on a board.
To list the plugin in FPP's own Plugin Manager catalogue, send a pull request adding the repo to `FalconChristmas/fpp-data/pluginList.json`.

Why there is no OS image: FPP's images are built by FPP's CI and contain the user's own configuration; FPP 10.x distributes its BeagleBone driver under CC BY-ND 4.0 (no derivative
copies), and for 5.x we keep FPP's files untouched in this repository too: the patchers add to them on the device, so what we release is the patch set plus a version stamp
(`/home/fpp/media/config/fbp-version`), installable on top of any stock FPP 5.4.x image.

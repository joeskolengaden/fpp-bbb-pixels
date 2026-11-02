# Installing fpp-bbb-pixels

Supported: **FPP 5.4.x on a BeagleBone** (Black / Green / PocketBeagle). The installer checks every patch against your FPP first and changes nothing if
anything does not match (it aborts with a message). If the rebuild fails it puts FPP back to stock and restarts it. Back up your configuration first anyway
(FPP: *Content Setup → File Manager*, or `Status/Control → Backup`).

## A. FPP Plugin Manager (board has internet)
1. **Content Setup → Plugins**
2. Paste this into *Find a Plugin or Enter a plugininfo.json URL* and press Enter:
   `https://raw.githubusercontent.com/joeskolengaden/fpp-bbb-pixels/main/pluginInfo.json`
3. **Install**. FPP clones the repository and runs `scripts/fpp_install.sh`, which runs `install.sh` (a few minutes; fppd is stopped while it recompiles).
4. Restart FPPD if asked. A **Pixel IC Support** page appears under the plugin menu (health check, *Re-apply patches*).

Update: *Plugins → Update*. Uninstall: *Plugins → Uninstall* (restores stock FPP from the `.orig` backups).

## B. Offline (board has no internet, only a USB or LAN link to your computer)
Download `fpp-bbb-pixels-<version>.tar.gz` and `SHA256SUMS` from the [latest release](https://github.com/joeskolengaden/fpp-bbb-pixels/releases/latest), then on your computer:
```bash
shasum -a 256 -c SHA256SUMS                          # must print: fpp-bbb-pixels-<version>.tar.gz: OK
scp fpp-bbb-pixels-<version>.tar.gz fpp@<board-ip>:/tmp/
ssh fpp@<board-ip>
tar xzf /tmp/fpp-bbb-pixels-<version>.tar.gz -C /tmp && cd /tmp/fpp-bbb-pixels-<version>
sudo bash install.sh --check      # dry run: validates every patch, changes nothing
sudo bash install.sh              # the real install
```
Then restart FPPD. The SPIPixels library is built and installed by the same run.

## C. Check it worked
```bash
sudo bash doctor.sh               # 0 failure(s), 0 warning(s) expected
sudo bash selftest.sh             # builds and runs the on-device tests (a few minutes)
cat /home/fpp/media/config/fbp-version
```
On the *Input/Output Setup → Channel Outputs → Pixel Strings* page, **Pixel Timing** now lists presets 0-18 (including *Custom timing*).

## After an FPP upgrade
An FPP upgrade replaces the files we patch. The plugin's start-up guard writes a warning to `fppd.log` and the plugin page shows it. Re-apply with the page's button, or `sudo bash install.sh`.

## Uninstall
`sudo bash uninstall.sh` (or the Plugin Manager's Uninstall) restores every patched file and the prebuilt libraries from the `.orig` backups the installer made. Remove any `pixelTiming` 2-18 / new colour-order / SPIPixels entries from your channel-output config afterwards.

## SPI chips only (also Raspberry Pi)
Install the separate **SPIPixels** plugin: `https://raw.githubusercontent.com/joeskolengaden/SPIPixels/main/pluginInfo.json`.

<?php
/*
 * Status page for the Pixel IC Support plugin (fpp-bbb-pixels).
 * Shows whether every patch is applied, runs the read-only health check (doctor.sh), and can re-apply the patches
 * (e.g. after an FPP upgrade replaced the files) -- the installer runs in the background, because it stops fppd for the compile.
 */
$plugDir = dirname(__FILE__);
$logFile = '/home/fpp/media/logs/fbp-install.log';
$flagFile = '/home/fpp/media/config/fbp-needs-reapply';
$msg = '';

function fbp_running() {
    $o = trim((string)shell_exec("pgrep -f 'fpp-bbb-pixels/install.sh' 2>/dev/null | head -1"));
    return $o !== '';
}

if (isset($_POST['action']) && $_POST['action'] === 'reapply') {
    if (fbp_running()) {
        $msg = 'The installer is already running.';
    } else {
        $cmd = 'sudo nohup bash ' . escapeshellarg($plugDir . '/install.sh') . ' > ' . escapeshellarg($logFile) . ' 2>&1 < /dev/null &';
        shell_exec($cmd);
        $msg = 'Installer started. fppd stops during the build (a few minutes) and restarts on its own. Reload this page to follow the log.';
    }
}

$running = fbp_running();
$doctor = shell_exec('sudo bash ' . escapeshellarg($plugDir . '/doctor.sh') . ' 2>&1');
$flag = file_exists($flagFile) ? trim(file_get_contents($flagFile)) : '';
$log = file_exists($logFile) ? implode("\n", array_slice(explode("\n", (string)file_get_contents($logFile)), -25)) : '';
?>
<h2>Pixel IC Support (BeagleBone)</h2>
<p>Adds pixel timing presets, <b>Custom timing</b>, 5/6-channel and 16-bit colour orders, chip-current controls and the per-port limits panel to
FPP's pixel-string page, and installs the SPIPixels library for clocked chips (APA102, HD108, TLC59711, WS2801, ...). Choose the chip on
<b>Input/Output Setup &rarr; Channel Outputs &rarr; Pixel Strings</b>; the pixel limit for your chip and frame rate is shown there.</p>

<?php if ($msg) echo '<div class="alert alert-info">' . htmlspecialchars($msg) . '</div>'; ?>
<?php if ($running) { ?>
<div class="alert alert-warning"><b>Installer running.</b> fppd is stopped while it builds. Reload in a minute or two.</div>
<?php } elseif ($flag !== '') { ?>
<div class="alert alert-danger"><b>Patches missing:</b> <?php echo htmlspecialchars($flag); ?> &mdash; an FPP upgrade or restore put stock files back.
Pixel timings 2-18 and the new colour orders will not work correctly until you re-apply.</div>
<?php } else { ?>
<div class="alert alert-success">All patches are in place.</div>
<?php } ?>

<form method="post" onsubmit="return confirm('Re-apply all patches and rebuild? fppd stops for a few minutes and restarts by itself.');">
  <input type="hidden" name="action" value="reapply">
  <input type="submit" class="buttons" value="Re-apply patches" <?php if ($running) echo 'disabled'; ?>>
</form>

<h3>Health check</h3>
<pre style="font-size:0.85em;white-space:pre-wrap"><?php echo htmlspecialchars(preg_replace('/\x1b\[[0-9;]*m/', '', (string)$doctor)); ?></pre>
<?php if ($log !== '') { ?>
<h3>Last install log (end)</h3>
<pre style="font-size:0.85em;white-space:pre-wrap"><?php echo htmlspecialchars($log); ?></pre>
<?php } ?>

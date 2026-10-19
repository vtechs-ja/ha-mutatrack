# HA power control of frankenmac and codey

Status: **applied to the live HA instance 2026-09-30; `switch.codey` tested
end to end, `switch.frankenmac` untested on purpose** (turning it off ends the
dev-server session). HA (HAOS) starts and stops the two Linux servers so automations can use them. Not
MutaTrack integration code; lives here with the other HA-side config.

| | frankenmac (dev server) | codey (cold spare) |
| --- | --- | --- |
| IP | 192.168.50.32 | 192.168.50.102 |
| MAC | `00:23:df:df:a0:f1` (`enp9s0`) | `D4:BE:D9:9A:A7:F2` |
| WoL | `Wake-on: g` confirmed, survived a reboot | confirmed 2026-09-30 (woke from off); BIOS "Wake on LAN" (OptiPlex 790) already set |
| SSH | `ssh.socket` active | `sshd` on, owner key authorized; `ssh codey` alias here; no `ha-control` user/key from HA yet |

Config: `ha-config/servers/servers.yaml` (shell commands, `wake_on_lan` switches
`switch.frankenmac` and `switch.codey`, plus `script.frankenmac_shutdown`; on =
magic packet, off = `systemctl poweroff` over SSH; state from ping).

## frankenmac: suspend tried and reverted (2026-10-19)

WoL from a full poweroff on frankenmac (Mac Pro 5,1, `enp9s0`) only works if the
magic packet arrives within a few seconds of shutdown; after about a minute it
fails (Linux `Wake-on: g` is fine, so the Mac firmware/NIC loses standby power).
Suspend (S3) was tried as the "off" action: a 5m20s test woke fine from the HA
switch, but on a later resume **the GPU did not come back and the fans ran high**.
`switch.frankenmac` is therefore back on poweroff.

- `shell_command.frankenmac_suspend` is still defined (and allowed in
  `/etc/sudoers.d/ha-control`) but nothing uses it. Don't wire it up again before the
  GPU resume problem is understood.
- `script.frankenmac_shutdown` now duplicates the switch's off action.
- Waking from full shutdown is unreliable: only power frankenmac off when you can
  press its power button, or will wake it within seconds.
- After a wake, `frankenmac.local` takes ~20s to resolve over mDNS; use `192.168.50.32`.

## Setup steps (owner runs the sudo ones)

1. **On HA:** generate a key with `ssh-keygen -t ed25519 -N "" -f /config/.ssh/ha_servers`
   (SSH add-on terminal; HAOS's own `ssh` client is used by `shell_command`).
2. **On each server**, create the restricted user and rule:
   ```bash
   sudo adduser --disabled-password --gecos "" ha-control
   sudo install -d -m700 -o ha-control -g ha-control /home/ha-control/.ssh
   echo '<contents of ha_servers.pub>' | sudo tee /home/ha-control/.ssh/authorized_keys
   sudo chown ha-control: /home/ha-control/.ssh/authorized_keys && sudo chmod 600 /home/ha-control/.ssh/authorized_keys
   # both machines:
   echo 'ha-control ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff' | sudo tee /etc/sudoers.d/ha-control
   sudo visudo -cf /etc/sudoers.d/ha-control && sudo chmod 440 /etc/sudoers.d/ha-control
   ```
3. Put `servers.yaml` in `/config/packages/`, fill in codey's MAC, check
   configuration, restart HA.
4. **codey's old dev units** (conductor, cloudflared, OKX listener and the two OKX timers) were disabled on its own disk 2026-09-30, after a test boot showed the timers still enabled. WoL confirmed working the same day (booted in ~40s); no HA guard automation is needed.

## Caveats

- **`switch.frankenmac` off takes down the dev server:** Conductor, the
  Cloudflare tunnel, the OKX approval listener and Claude Code sessions all
  run there. Don't wire it to unattended automations without thought.
- Powering off from HA does not survive a total power cut: WoL needs a clean
  shutdown, or BIOS "power on after AC loss".
- The OKX listener is a WebSocket client to HA, so it drops whenever
  frankenmac is off.

## Applied state (2026-09-30)

- `/config/packages/servers.yaml` on HA is a copy of `ha-config/servers/servers.yaml`
  (installed via a base64 one-liner in the HA terminal); `configuration.yaml`
  gained `homeassistant: packages: !include_dir_named packages` (backup:
  `/config/configuration.yaml.bak-servers`).
- `ha-control` user, key-only login and a `NOPASSWD: /usr/bin/systemctl poweroff`
  sudoers rule exist on both servers; HA's key is `/config/.ssh/ha_servers`.
- Switch state is ping-based (`host:`): follows changes made outside HA but lags
  up to ~30s, reads off while a machine boots, and says nothing about service health.
- codey test: off toggle -> ping stopped in ~6s, journal shows a normal systemd
  shutdown; on toggle -> answering SSH within ~50s, no filesystem recovery.
- **2026-10-19:** package updated to add `frankenmac_suspend` and `script.frankenmac_shutdown`, then the switch went back to poweroff (see above). Live `/config/packages/servers.yaml` was reverted the same day (confirmed by the owner after a restart: both switches show poweroff). The first `sed` revert did not take effect until it was re-run.
- Keep this in sync if the live package drifts (see CLAUDE.md on HA-side config).

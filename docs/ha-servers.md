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

Config: `ha-config/servers/servers.yaml` (shell commands + `wake_on_lan`
switches `switch.frankenmac`, `switch.codey`, plus `script.frankenmac_shutdown`;
on = magic packet; state from ping). `switch.codey` off = `systemctl poweroff`
over SSH. **`switch.frankenmac` off = `systemctl suspend`** (changed 2026-10-19,
see below). Full poweroff of frankenmac is a separate action,
`script.frankenmac_shutdown` ("frankenmac shutdown").

## frankenmac: suspend, not poweroff (2026-10-19)

WoL from a full poweroff on frankenmac (Mac Pro 5,1, `enp9s0`) only works if the
magic packet arrives within a few seconds of shutdown; after about a minute it
fails. Linux is fine (`Wake-on: g`), so the Mac firmware/NIC loses standby power.
Suspend (S3) tested 2026-10-19: asleep 5m20s, woke from the HA switch, containers
resumed. So:

- `switch.frankenmac` off -> `shell_command.frankenmac_suspend`; on -> magic packet.
  Ping-based state reads **off while suspended** (expected).
- `script.frankenmac_shutdown` -> `shell_command.frankenmac_poweroff`. Waking from
  full shutdown is currently unreliable; use it only when the owner can press the
  power button.
- After wake, `frankenmac.local` takes ~20s to resolve over mDNS; check via
  `192.168.50.32`.
- frankenmac's `/etc/sudoers.d/ha-control` allows both `systemctl poweroff` and
  `systemctl suspend` (NOPASSWD). codey is unchanged (poweroff only).


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

- **`switch.frankenmac` off suspends the dev server:** Conductor, the
  Cloudflare tunnel, the OKX approval listener and Claude Code sessions all
  run there. Don't wire it to unattended automations without thought.
- (codey) Powering off from HA does not survive a total power cut: WoL needs a clean
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
- **2026-10-19 change (frankenmac suspend + shutdown script): repo copy updated and
  committed; live apply pending the owner pasting the new file into HA, then
  restart (new `wake_on_lan` turn_off needs it) and the end-to-end test.**
- Keep this in sync if the live package drifts (see CLAUDE.md on HA-side config).

# mac-system

macOS system information skill for the OpenClaude Telegram bot.

## Commands

| Command | Description |
|---------|-------------|
| `info` | Battery %, disk space, CPU/memory usage, uptime |
| `processes` | Top 10 processes by CPU |
| `network` | Current WiFi SSID, local IP, public IP |

## Usage

```bash
./skills/mac-system/run.sh info
./skills/mac-system/run.sh processes
./skills/mac-system/run.sh network
```

## Tools Used

- `pmset` — battery status
- `df` — disk usage
- `sysctl` / `memory_pressure` — RAM info
- `top` / `ps` — CPU and process info
- `networksetup` — WiFi SSID
- `ipconfig` / `ifconfig` — IP addresses
- `curl` — public IP lookup (5s timeout)

## Notes

- Battery info is only meaningful on laptops; shows N/A on desktops/servers.
- Public IP lookup hits `api.ipify.org` with a 5-second timeout — fails gracefully.
- CPU usage is sampled over 2 `top` intervals for accuracy.

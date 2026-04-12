# mac-notify

macOS notification sender skill for the OpenClaude Telegram bot.

## Commands

| Command | Description |
|---------|-------------|
| `send <title> <message>` | Show a macOS system notification |

## Usage

```bash
./skills/mac-notify/run.sh send "Build Done" "Your project compiled successfully."
./skills/mac-notify/run.sh send "Reminder" "Time for a break!"
```

## Tools Used

- `osascript` — `display notification` AppleScript command

## Notes

- Both `title` and `message` are required.
- Double quotes in title/message are automatically escaped for AppleScript safety.
- Notifications appear in macOS Notification Center. If Do Not Disturb is active, they will be queued.
- The app name shown in Notification Center will be "Script Editor" or "Terminal" depending on how the bot runs the script — this is a macOS limitation for shell-driven notifications.
- For persistent or actionable notifications (replies, buttons), use a native app wrapper instead.

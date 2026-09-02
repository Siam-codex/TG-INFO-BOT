# KAWSAR CODEX - Free Fire Info Telegram Bot

## Setup:
1. bot.py ফাইল খোলো
2. BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" — এখানে তোমার token বসাও
   (@BotFather থেকে নাও)
3. Run করো:

```bash
pip install -r requirements.txt
python bot.py
```

## Commands:
| Command | Description |
|---------|-------------|
| `/info <UID>` | Full player info (banner + outfit + all data) |
| `/get <UID>` | Same as /info |
| `/banner <UID>` | শুধু banner profile image |
| `/outfit <UID>` | শুধু outfit image |
| `/level <UID>` | নাম + level |
| `/region <UID>` | নাম + region |

## Example:
```
/info 2916914087
/banner 2916914087
/outfit 2916914087
/level 2916914087
/region 2916914087
```

## Features:
- No external API key needed
- Banner image auto generate
- Outfit image with ring slots
- All info in one message
- Supports plain UID (just send the number)
- TG: @SIAM_CODEX

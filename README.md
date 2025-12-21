# LN Release Discord Bot

A Discord bot that automatically posts daily alerts for licensed light novel digital releases. The bot scrapes data from various official sources (publishers, stores) and notifies your Discord server when new volumes are released.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/AlpinDale/lnrelease-discord-bot
   cd lnrelease-discord-bot
   ```

2. **Create environment file**
   
   Create a `.env` file in the project root:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   BOT_TIMEZONE_DEFAULT=UTC
   ```

3. **Start the bot**
   ```bash
   docker-compose up -d
   ```

4. **View logs**
   ```bash
   docker-compose logs -f bot
   ```

### Discord Setup

1. **Create a Discord Bot**
   - Go to https://discord.com/developers/applications
   - Create a new application
   - Go to "Bot" tab and create a bot
   - Copy the token and add it to your `.env` file

2. **Invite Bot to Your Server**
   
   **Option A: Simple URL (recommended)**
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=19464&scope=bot%20applications.commands
   ```
   
   **Option B: If you need `guilds.join` scope (some setups require it)**
   
   First, add a redirect URI in Developer Portal:
   - Go to OAuth2 → General
   - Add redirect URI: `http://localhost`
   - Save
   
   Then use this URL:
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=19464&scope=bot%20applications.commands%20guilds.join&redirect_uri=http%3A%2F%2Flocalhost
   ```
   
   **Option C: Use URL Generator (easiest)**
   - Go to OAuth2 → URL Generator
   - Select scopes: `bot`, `applications.commands` (and `guilds.join` if needed)
   - Select permissions: View Channels, Send Messages, Embed Links, Use Application Commands
   - Copy the generated URL
   
   This grants the bot:
   - View Channels
   - Send Messages
   - Embed Links
   - Use Application Commands

3. **Configure in Discord**
   
   In your Discord server, run:
   ```
   /set_channel #your-channel
   ```

## Commands

| Command | Description | Permissions |
|---------|-------------|-------------|
| `/set_channel #channel` | Set the channel for release notifications | Manage Server |
| `/uncollected [date]` | Show uncollected releases (ephemeral) | None |
| `/resync_today` | Manually trigger today's releases | Administrator |

### Usage Examples

**Set notification channel:**
```
/set_channel #releases
```

**View all uncollected releases:**
```
/uncollected
```

**View uncollected for specific date:**
```
/uncollected date:2024-12-25
```

**Manually trigger today's posts:**
```
/resync_today
```

## How It Works

1. **Every 8 hours**, the bot:
   - Scrapes release data from official sources (publishers, stores)
   - Parses and normalizes the data
   - Generates a list of today's digital releases

2. **For each configured server**, the bot:
   - Filters releases to "digital-only" (no physical books or audiobooks)
   - Posts new releases that haven't been sent yet
   - Tracks sent releases in a SQLite database

3. **Users can**:
   - Click "Done" to mark releases as collected
   - Use `/uncollected` to see what they haven't collected yet
   - Only see releases the bot has actually sent to their server

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | *(required)* | Your Discord bot token |
| `BOT_DB_PATH` | `./data/bot.sqlite` | Path to SQLite database file |
| `BOT_TIMEZONE_DEFAULT` | `UTC` | Default timezone for date calculations |

### Timezone Options

Common timezone values:
- `America/New_York` - Eastern Time
- `America/Chicago` - Central Time
- `America/Denver` - Mountain Time
- `America/Los_Angeles` - Pacific Time
- `UTC` - Coordinated Universal Time
- `Europe/London` - British Time
- `Asia/Tokyo` - Japan Time

See [full list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

## Data Sources

The bot scrapes from official sources including:

**Publishers:**
- Cross Infinite World
- Hanashi Media
- J-Novel Club
- Kodansha
- One Peace Books
- Seven Seas Entertainment
- Square Enix
- TOKYOPOP
- VIZ Media
- Yen Press

**Stores:**
- BOOK☆WALKER
- Crunchyroll
- Apple Books
- Barnes & Noble
- Google Play Books
- Kobo
- And more...

## Development

### Running Locally (without Docker)

1. **Install dependencies**
   ```bash
   pip install .
   ```
   
   Or for development with test dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Set environment variables**
   ```bash
   export DISCORD_TOKEN="your_token_here"
   export BOT_TIMEZONE_DEFAULT="UTC"
   ```

3. **Run the bot**
   ```bash
   python -m lnrelease.bot
   ```

### Modifying Update Interval

Edit `lnrelease/bot/app.py` and change:
```python
@tasks.loop(hours=8)  # Change this value
async def update_loop(self):
```

## Troubleshooting

### Bot invite URL not working / "Opening Discord App" stuck
1. **Open the URL in a web browser** (not the Discord desktop app)
   - Copy the invite URL
   - Open it in Chrome, Firefox, Safari, or Edge
   - Make sure you're logged into Discord in the browser

2. **Check Discord Developer Portal settings:**
   - Go to https://discord.com/developers/applications
   - Select your application
   - Go to "OAuth2" → "General"
   - **Redirect URIs**: For bot invites, you don't need any redirect URIs. If the portal requires at least one, add `http://localhost` (it won't be used for bot invites)
   - Go to "Bot" tab and ensure:
     - Bot is enabled (toggle at top)
     - "Public Bot" can be disabled for personal use
     - "Requires OAuth2 Code Grant" should be OFF

3. **Try alternative URL formats:**
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=19464&scope=bot%20applications.commands
   ```

4. **Manual invite via Developer Portal:**
   - Go to OAuth2 → URL Generator
   - Select scopes: `bot`, `applications.commands`
   - Select permissions: View Channels, Send Messages, Embed Links, Use Application Commands
   - Copy the generated URL

### Bot not responding to commands
- Verify the bot is online (green status in Discord)
- Check bot has necessary permissions in your server
- View logs: `docker-compose logs bot`
- Ensure slash commands are synced (restart bot if needed)

### No releases being posted
- The bot only posts digital releases for the current day in your timezone
- Check if there are actually releases today
- Try `/resync_today` to manually trigger
- Check logs for scraping errors

### Database issues
- Ensure `data/` directory exists and is writable
- Check: `ls -la data/` should show `bot.sqlite`
- If corrupted, stop bot, backup/delete `data/bot.sqlite`, restart

### "No uncollected releases" but I haven't marked anything
- `/uncollected` only shows releases the bot has sent to your server
- If you just set up the bot, it will only track new releases going forward
- Old releases aren't retroactively tracked

## Docker Commands

**Start bot:**
```bash
docker-compose up -d
```

**Stop bot:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f bot
```

**Restart bot:**
```bash
docker-compose restart bot
```

**Rebuild after code changes:**
```bash
docker-compose up -d --build
```

## License

MIT License - See LICENSE file for details

## Credits

Built on top of the [lnrelease](https://github.com/lnrelease/lnrelease.github.io) project's scraping infrastructure.


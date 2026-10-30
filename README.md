# Crit Tracker Discord Bot

A personal Dungeons & Dragons crit-tracking bot for Discord. This project listens for slash commands and updates a Google Sheet with Nat 20 and Nat 1 totals for characters across multiple campaigns. It also includes a talking cow named Tim, powered by Ollama using either a local Ollama server or Ollama Cloud, for fun flavor text and chat responses.

This is a highly opinionated, heavily customized project intended for a specific use case. The character roster, campaign names, spreadsheet layout, and message formatting are all configured in code and in the JSON config file; adapt these pieces when repurposing the bot for your own table.

---

## Features

The app combines `discord.py` slash commands, a Google Sheets backend, and a pluggable Ollama chat model (local or cloud) for Tim the Magic Cow.

### 1. Crit tracking

The core feature is the `/add` slash command. It updates a cell in a Google Sheet based on:

- the character name
- the crit type (`1` or `20`)
- the associated campaign/sheet mapping

For example, if a character rolls a Nat 20, the bot increments the cell for that character's Nat 20 count. If it is a Nat 1, it increments the Nat 1 counter instead.

### 2. Campaign session tracking

The `/session` command increments the session counter for a specified campaign. In the current setup, it writes to cell `H2` on the selected sheet, which makes it easy to track how many sessions have happened in a campaign.

### 3. Tim the Magic Cow

Tim is configured in `config.json`. Its prompt and Ollama backend (local or cloud) power two commands:

- `/cowchat` — Talk to Tim directly
- `/cowsay` — Format a message as ASCII art from a cartoon cow

These responses are wrapped using the `cowsay` utility and a custom `wizard.cow` template.

### 4. Voice sounds

When a crit is added, the bot can play a sound effect in the current voice channel. This is controlled with the `/sounds on` and `/sounds off` commands.

### 5. Google Sheets integration

The project authenticates with Google Sheets using OAuth and stores the resulting `token.json` locally. It can read and update cells, which is what makes the crit tracker operate.

---

## Project structure

```text
.
├── README.md
├── requirements.txt
├── config.json
├── credentials.json
├── token.json
├── wizard.cow
├── res/
│   ├── nat20.png
│   ├── nat1.png
│   ├── fail.mp3
│   ├── success.wav
│   ├── warning.png
├── src/
│   ├── app.py
│   ├── bot.py
│   ├── ollama_chat.py
│   ├── sheets.py
│   ├── cogs/
│   │   ├── __init__.py
│   │   ├── chat_cog.py
│   │   ├── core_cog.py
│   │   ├── crit_cog.py
│   │   └── voice_cog.py
│   └── utils/
│       └── helpers.py
└── .env
```

Key files:

- `config.json` contains campaigns, character mappings, crit columns, and Tim settings
- `src/app.py` boots the app, loads config, authenticates with Google, initializes Tim's Ollama client, and starts the bot
- `src/ollama_chat.py` resolves Ollama settings and manages Tim's chat history and requests
- `src/bot.py` registers the Discord cogs
- `src/sheets.py` handles Google Sheets read/write operations
- `src/cogs/crit_cog.py` contains the crit-tracking commands
- `src/utils/helpers.py` contains helper logic for cow formatting, AI responses, and sound playback

---

## Prerequisites

Before running the bot, make sure you have:

- Python 3.10 or newer
- A Discord bot token
- A Google Cloud project with the Google Sheets API enabled
- A `credentials.json` OAuth client file from Google Cloud
- Ollama installed and running locally, or an Ollama Cloud API key
- The `cowsay` package installed on your system
- PowerShell (`pwsh`) if you are running on Linux/macOS and want the Windows-compatible PowerShell path used by the code

### Required system packages

On Linux, install `cowsay` and `pwsh` if needed:

```bash
sudo apt update
sudo apt install cowsay powershell
```

If your distribution does not provide PowerShell in the standard package repositories, install it via Microsoft’s recommended method for your OS.

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/your-user/Crit-Tracker-Discord-Bot.git
cd Crit-Tracker-Discord-Bot
```

2. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. Ensure the required assets are present in `res/`:

- `nat20.png`
- `nat1.png`
- `warning.png`
- `success.wav`
- `fail.mp3`

If these are missing, the bot will not be able to render embed images or play sounds correctly.

---

## Environment variables and configuration

Create a `.env` file in the project root. This app uses `python-dotenv` to load the following values. For a local Ollama server, only the bot and Google Sheets settings are needed; Ollama uses the local defaults shown below. For Ollama Cloud, set `OLLAMA_BACKEND=cloud` and provide `OLLAMA_API_KEY`.

```env
DISCORD_TOKEN=your_discord_bot_token
SHEET_ID=your_google_sheet_id
PWSH_PATH=/usr/bin/pwsh
# optional: uncomment to disable Tim
# NO_TIM=1
# Optional Ollama settings (local defaults shown)
OLLAMA_BACKEND=local
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:e2b

# Cloud example:
# OLLAMA_BACKEND=cloud
# OLLAMA_HOST=https://ollama.com
# OLLAMA_MODEL=your-cloud-model
# OLLAMA_API_KEY=your_ollama_cloud_api_key
```

### Required variables

- `DISCORD_TOKEN`: The Discord bot token from the Discord Developer Portal
- `SHEET_ID`: The ID of the Google Sheet the bot should update
- `PWSH_PATH`: Path to the PowerShell executable used by the `cowsay` helper on Windows or when using a PowerShell-based invocation path

### Ollama variables

- `OLLAMA_BACKEND`: `local` or `cloud`; defaults to `local`
- `OLLAMA_HOST`: Ollama server URL; defaults to `http://127.0.0.1:11434` for local or `https://ollama.com` for cloud
- `OLLAMA_MODEL`: model name; defaults to `gemma4:e2b`
- `OLLAMA_API_KEY`: API key for Ollama Cloud; required when using the cloud backend
- `OLLAMA_API_KEY_FILE`: optional path to a file containing the cloud API key
- `OLLAMA_TIMEOUT`: optional request timeout in seconds

Environment variables take precedence over the `tim_config.ollama` settings in `config.json`. The API key can also be set in that config block or loaded from its `api_key_file` value. Avoid committing API keys or other secrets.

### Optional variable

- `NO_TIM`: enables Tim's placeholder mode; when set, Ollama is not called

### Ollama setup

For local inference, install Ollama, start its service, and download the configured model with `ollama pull gemma4:e2b` when using the default. Confirm the service is reachable from the bot. For Ollama Cloud, use the cloud endpoint and a valid API key; no local model download is needed.

---

## Google Sheets setup

This bot expects a spreadsheet containing the campaign tabs and character rows it knows about. The app reads values from cells like `B2`, `C2`, etc. based on the `config.json` mapping.

### 1. Create a Google Cloud project

- Go to the Google Cloud Console
- Create a new project
- Enable the Google Sheets API
- Create OAuth credentials for a desktop application
- Download the OAuth client JSON and save it as `credentials.json` in the project root

### 2. Authorize the app

When you launch the bot for the first time, it will try to open an OAuth flow and write a `token.json` file. That caches the authorized session so you do not have to sign in repeatedly.

This behavior is handled in `src/app.py`:

- it loads `credentials.json`
- tries to reuse `token.json`
- otherwise starts an OAuth flow using `InstalledAppFlow`

### 3. Prepare your sheet layout

The spreadsheet must line up with the `config.json` file. In the current project, the bot expects:

- campaign names such as `PAXORIAN`, `KRIGGSAN`, and `GELIDUS`
- character entries like `ZOHAR`, `MORBO`, `GRUNT`, etc.
- `crit_types` entries:
  - `"20"` stored in column `B`
  - `"1"` stored in column `C`
- character rows as numeric strings, such as `"2"`, `"3"`, `"4"`

The code builds the target cell as:

```python
cell = crit_info["col"] + char_info["row"]
```

So a character on row 2 with a Nat 20 crit will update a cell like `B2`.

---

## Discord bot setup

### Create the bot

1. Go to the Discord Developer Portal
2. Create a new application
3. Add a bot user
4. Enable the required intents for the bot
5. Copy the bot token into `.env` as `DISCORD_TOKEN`

### Invite the bot to your server

Use the OAuth2 URL generator in the Developer Portal to invite the bot to the server where you want to use it.

The bot registers slash commands, so the server needs the bot to have the proper permissions and the commands must be synced by Discord after the app starts.

---

## Configuring the bot

The primary configuration lives in `config.json`.

### Example structure

```json
{
  "campaigns": ["PAXORIAN", "KRIGGSAN", "GELIDUS"],
  "characters": {
    "ZOHAR": {
      "color": 9332547,
      "sheet": "Paxorian",
      "row": "2"
    }
  },
  "crit_types": {
    "1": {
      "col": "C",
      "img": "res/nat1.png",
      "sound": "res/fail.mp3"
    },
    "20": {
      "col": "B",
      "img": "res/nat20.png",
      "sound": "res/success.wav"
    }
  },
  "tim_config": {
    "instruction": "Your name is Tim...",
    "temperature": 1,
    "ollama": {
      "backend": "local",
      "model": "gemma4:e2b",
      "host": "http://127.0.0.1:11434",
      "timeout": 120
    }
  }
}
```

### What each section does

- `campaigns`: valid campaign names used by `/session`
- `characters`: keys are character names that appear in `/add`; each entry defines the sheet name, row, and embed color
- `crit_types`: maps crit value to spreadsheet column and associated assets
- `tim_config.instruction` and `tim_config.temperature` — Set Tim's system prompt and response temperature
- `tim_config.ollama` — Choose the Ollama backend, model, host, optional API key/key file, and timeout. Set `backend` to `cloud` with `host: "https://ollama.com"` for Ollama Cloud, and supply the API key through the responsible environment variable.

If you want a different roster or different spreadsheet layout, this is where you change it.

---

## Running the bot

From the project root:

```bash
python src/app.py
```

The application will:

- load `.env`
- load `config.json`
- authenticate with Google
- initialize Tim's Ollama client
- start the Discord bot

If startup fails, the app logs the exception and exits.

---

## Slash commands

The bot registers these slash commands:

### `/add`

Adds a crit to the spreadsheet.

Parameters:

- `crit_type`: `1` or `20`
- `char_name`: character name from the configured roster

Example:

```text
/add 20 ZOHAR
/add 1 MORBO
```

This updates the character’s total in the corresponding sheet cell and sends a rich embed with a cow message and image.

### `/session`

Increments the session count for the selected campaign.

Parameters:

- `campaign`: campaign name from the configured list

Example:

```text
/session PAXORIAN
```

### `/cowchat`

Talks to Tim the Magic Cow.

Parameters:

- `message`: text to send to Tim

Example:

```text
/cowchat Why do cows make such good philosophers?
```

### `/cowsay`

Creates a formatted ASCII cow message.

Parameters:

- `message`: text to place inside the cow format

Example:

```text
/cowsay Remember to roll the dice!
```

### `/sounds`

Turns the crit sound effect feature on or off.

Parameters:

- `status`: `on` or `off`

Example:

```text
/sounds on
/sounds off
```

---

## How the bot works

At a high level:

1. A user runs a slash command in Discord.
2. The bot validates the input against `config.json`.
3. For crit tracking, it calls `SheetsHandler.increment_cell()`.
4. The bot sends a response back to the user with an embed.
5. Tim generates a flavor paragraph in the format of a talking cow.
6. If the user is in a voice channel and sound mode is enabled, the bot plays a sound file.

The main data flow is intentionally simple and makes this project easy to inspect and adapt.

---

## Troubleshooting

### Discord bot is not online

- Double-check `DISCORD_TOKEN` in `.env`
- Make sure your bot has been invited to the correct server
- Ensure the application has permission to create slash commands

### Google Sheets auth fails

- Make sure `credentials.json` is present in the project root
- Check that the Google Sheets API is enabled in your project
- Delete `token.json` if it is stale and rerun the bot to authorize again

### `cowsay` command errors

- Ensure `cowsay` is installed on the system
- Ensure `PWSH_PATH` points to your PowerShell executable if needed
- Test the command manually:

```bash
cowsay -f ./wizard.cow hello
```

### Tim is not responding

- For local Ollama, confirm the Ollama service is running, the host is reachable, and the configured model is available locally
- For Ollama Cloud, check `OLLAMA_BACKEND`, the cloud host, and that `OLLAMA_API_KEY` is valid
- Check the configured model name and review the application logs for Ollama connection errors

### Spreadsheet updates do not land in the expected cell

- Check the `characters` mapping in `config.json`
- Verify that `crit_types["20"]["col"]` and `crit_types["1"]["col"]` match your sheet layout
- Confirm each character row number matches the row in the spreadsheet

---

## Customization notes

This project is intentionally hardcoded for a specific use case. If you want to adapt it:

- update `config.json` with your own campaigns and character list
- edit the crit columns and sheet names in `crit_types`
- swap out the asset files in `res/`
- change the Tim prompt in `config.json`
- customize Discord slash command behavior in the cogs under `src/cogs/`

---

## Future feature ideas

### 1. Character and campaign management commands

Add admin-level commands to:

- create or delete a character from the roster
- add or remove campaign names
- update a character's row or sheet assignment without editing JSON by hand
- bulk-import character lists from a spreadsheet or CSV

### 2. Leaderboards and summary reports

Add commands such as:

- `/leaderboard` to show who has the most Nat 20s or Nat 1s in a campaign
- `/summary` to display total crit counts by character or by campaign
- `/top-critters` for a short leaderboard embed

### 3. Reset and audit tools

Add safety-focused commands like:

- `/reset-character` to clear a character's crit totals
- `/reset-campaign` to reset all crits for a campaign
- `/audit` to compare Discord data against Google Sheets and flag mismatches

### 4. Event logging and history

Track a history of rolls and session changes in a dedicated sheet or log channel. That could include:

- timestamped crit events
- who added them
- session number changes
- campaign-level notes

### 5. Better Tim integrations

Enhance the Tim experience by adding:

- campaign-specific personalities or tone settings
- a `tim summary` command for campaign chatter and quirky commentary
- support for custom voice or sound palettes tied to character classes or crit tiers

---

## Notes

This project was built as a personal experiment with the Discord API and Google Sheets API. It includes some code adapted from Google Sheets API quickstart and read/write examples, but it is mostly a custom integration built around a specific campaign tracking workflow.

If you are using it as a base, be aware that it assumes a particular sheet structure and command style. The code is straightforward enough that you can tune it to your own table without rewriting the bot from scratch.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for the full text.

# Danbooru Get Tags Bot

A Telegram bot that fetches tags from Danbooru posts.

## Features

- Get tags from Danbooru URLs using the `/get` command
- Set a banlist of tags to filter out using `/set_banlist`
- View the current banlist using `/get_banlist`
- Automatically formats tags for Telegram with proper escaping

## Commands

- `/start` - Start the bot
- `/get <url>` - Fetch tags from a Danbooru URL
- `/set_banlist <tag1,tag2,tag3>` - Set comma-separated banlist
- `/get_banlist` - Get current banlist

## Setup

1. Install dependencies with uv:
   ```bash
   uv sync
   ```

2. Set your bot token as an environment variable:
   ```bash
   export BOT_TOKEN="your_bot_token_here"
   ```
   
   Or it will use the default value defined in the code.

3. Run the bot:
   ```bash
   uv run python main.py
   ```

## Configuration

The bot creates a `config.ini` file in the root directory to store the banlist.

## Tag Categories

The bot provides tags in these categories:
- 全部 (All tags)
- 一般 (General tags)
- 角色 (Character tags)
- 版权 (Copyright tags)
- 画师 (Artist tags)
- 元信息 (Meta tags)
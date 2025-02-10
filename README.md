# Discord Bot

This personal Discord bot provides general utilities, including pinging and 
voting, while also integrating a calendar for better event tracking within 
Discord. Built as a personal project, it focuses on adding interesting and 
useful features, not to make a full-fledged bot or something prepared for big 
applications.

## Features

- **General**: Pinging the bot and launching votes.
- **Calendar**: Calendar integrated with Discord and simple functionality.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Hakai69/discord-bot.git
    ```
2. Navigate to the project directory:
    ```bash
    cd discord-bot
    ```
3. Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1. Create a `.env` file in the root directory and add your bot token:
    ```
    DISCORD_TOKEN=your-bot-token
    ```
2. Customize the files inside the `config` folder to suit your needs.
    - Use my template and just set the timezone in `config.ini`:
        ```ini
        [DEFAULT]
        timezone = your-timezone
        ```
    - My template is useless since it's specific to my guilds. So set your 
    guild's config in `guilds.ini`. `bot_channels` are the ones your bot can 
    speak in. `verification_channel` is currently useless:
        ```ini
        [GUILD-NAME]
        id = your-guild-id
        bot_channels = [bot-channel-id-1, bot-channel-id-2, ...]
        ```

## Acknowledgments

This project also uses the following libraries:

- `nextcord.py`, which is licensed under the MIT License. See [nextcord.py GitHub](https://github.com/nextcord/nextcord) for more details.
- `python-dotenv`, which is licensed under the BSD 3-Clause License. See [python-dotenv GitHub](https://github.com/theskumar/python-dotenv) for more details.
- `Unidecode`, which is licensed under the GPL-2.0 license. See [Unidecode Github](https://github.com/avian2/unidecode) for more details.

## License

[AGPL3 License](LICENSE)

## Author

- [Hakai69](https://github.com/Hakai69)

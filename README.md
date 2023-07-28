# TalkToMeIn

## Description

Bot designed to facilitate language learning through Telegram. Using OpenAI's GPT-4 and ElevenLabs, you can chat in your target language or practice your listening skills! Additionally, this bot allows you to save new vocabulary directly to a Notion database.

## Getting Started

Before you can use this bot, you need to obtain several API keys:

1. **OpenAI API Key**: Used for text generation, I use GPT-4, but feel free to use another model.
2. **ElevenLabs API Key and Voice ID**: Used for generating voice messages.
3. **Telegram Bot Token**: Used to run the bot on Telegram.
4. **(Optional) Notion Integration**: If you want to save your vocabulary in a Notion database, you will need to setup the integration with your Notion account.

You can also control who can use your bot by generating a **Login Token**.

### Setup

1. **OpenAI API Key**: You can obtain this key from the [OpenAI website](https://openai.com).
2. **ElevenLabs API Key and Voice ID**: You can obtain these from the [ElevenLabs website](https://elevenlabs.ai).
3. **Telegram Bot Token**: You can create a new bot and get its token by following Telegram's [BotFather guide](https://core.telegram.org/bots#botfather).
4. **Notion Integration**: To set up the Notion integration, follow the instructions in Notion's [API documentation](https://developers.notion.com/docs).
5. **Login Token**: You can create your own login token. It is a string that will be required to access the bot's functionalities.

After you have obtained these keys and tokens, you will need to set up the bot by using the following commands:

- `/setupopenai`: followed by your OpenAI API key
- `/setupelevenlabs`: followed by your ElevenLabs API key
- `/setuplanguage`: followed by the language you want to learn (e.g. "spanish", "german", etc.)
- `/setupvoicepercentage`: followed by a number from 0-1 representing the percentage of voice messages you want
- `/setupnotion`: followed by your Notion secret key
- `/setupdatabase`: followed by your Notion database id
- `/login`: followed by your login token

Please note that you can use the `/help` command to get more information about these commands.

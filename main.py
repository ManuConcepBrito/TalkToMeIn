#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

import logging
import os
import uuid
import openai
import wave
import random
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from elevenlabs import clone, generate, play, set_api_key
from elevenlabs.api import History
from elevenlabs.api.error import APIError
from notion_client import AsyncClient as NotionClient
import requests
from dotenv import load_dotenv
from functools import wraps

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Initialize Notion client
CHUNK_SIZE = 1024


dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hello! You can set up your environment using the commands: /setupnotion, /setupdatabase, /setuplanguage, /setupopenai, /setupelevenlabs, /setupvoicepercentage (use /help to learn more about them)"
    )


# setup token functions. Strip the text to skip the command and grab just the token
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["login_token"] = update.message.text[7:].strip()
    if context.user_data["login_token"] == os.environ.get("LOGIN_TOKEN"):
        context.user_data["authenticated"] = True
        await update.message.reply_text("Login successful")
    else:
        context.user_data["authenticated"] = False
        await update.message.reply_text(
            "Login token not correct, please try again later"
        )


def authenticated(func):
    """
    Wrapper to prevent unintended use.
    """

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        if not context.user_data.get("authenticated", False):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="You need to login first using /login your_token_here",
            )
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


# setup token functions. Strip the text to skip the command and grab just the token
async def setup_notion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["notion_token"] = update.message.text[13:].strip()
    await update.message.reply_text("Notion token set up successfully.")


async def setup_database(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["database_id"] = update.message.text[15:].strip()
    await update.message.reply_text("Database ID set up successfully.")


async def setup_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["language"] = update.message.text[14:].strip()
    await update.message.reply_text("Language set up successfully.")


async def setup_openai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["openai_key"] = update.message.text[12:].strip()
    await update.message.reply_text("OpenAI key set up successfully.")


async def setup_elevenlabs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["elevenlabs_key"] = (
        update.message.text[16:].strip()
        if update.message.text[16:].strip() != ""
        else os.environ.get("ELEVEN_LABS_KEY")
    )
    try:
        set_api_key(context.user_data["elevenlabs_key"])
        await update.message.reply_text("Eleven Labs key set up successfully.")
    except Exception as e:
        await update.message.reply_text("Error when setting up Eleven labs key")


async def setup_voice_percentage(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data["voice_percentage"] = float(update.message.text[21:].strip())
    await update.message.reply_text("Voice percentage setup correctly.")


def write_bytes_to_wav_file(data, filename):
    path_to_recording = os.path.join(os.environ.get("VOICE_RECORDING_FOLDER"), filename)
    with open(path_to_recording, mode="wb") as wav_file:
        wav_file.write(data)
    return path_to_recording


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "/login: Password to prevent overuse of the bot"
        "/save: Comand to save vocabulary to a notion database. Use 'word - definition' format. Requires /setupnotion and /setupdatabase to run."
        "/setupnotion: Notion secret key, it has the format secret_XXX...\n"
        "/setupdatabase: Notion database id to store the vocabulary learnt\n"
        '/setuplanguage: The language you want to learn in English: "german", "spanish", etc\n'
        "/setupopenai: OpenAI key to use\n"
        "/setupelevenlabs: Eleven labs key to use\n"
        "/setupvoicepercentage: Number from 0-1 representing the percentage of voice messages that you want. Set to 0.5 automatically."
    )
    await update.message.reply_text(help_text)


async def convert_gpt_to_voice(gpt_response: str, voice_id: str) -> bytes:
    model_id = "eleven_multilingual_v1"
    audio = generate(text=gpt_response, voice=voice_id, model=model_id)
    return audio


@authenticated
async def save_vocab(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("notion_token", None) or not context.user_data.get(
        "database_id", None
    ):
        await update.message.reply_text(
            "Notion token or database_id not setup. Set it up with /setupnotion and /setupdatabase"
        )
    # get the text after the /save command
    input_text = update.message.text[5:].strip()
    word, definition = input_text.split(" - ")
    client = NotionClient(auth=context.user_data["notion_token"])
    # add rows to database - Every row of a database in notion is a page by default
    new_page = await client.pages.create(
        parent={"database_id": context.user_data.get("database_id")},
        properties={
            "word": {"title": [{"text": {"content": word}}]},
            "definition": {"rich_text": [{"text": {"content": definition}}]},
        },
    )
    await update.message.reply_text(f"Saved: {word} - {definition}")


@authenticated
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Calls ChatGPT and then ElevenLabs"""

    openai.api_key = (
        context.user_data["openai_key"]
        if context.user_data.get("openai_key", None)
        else os.environ.get("OPEN_AI_KEY")
    )
    # default to german
    language = (
        context.user_data["language"]
        if context.user_data.get("language", None)
        else os.environ.get("DEFAULT_LANGUAGE")
    )
    system_prompt = f"You are a {language} teacher. Your role is to speak only in {language} and continue the conversation. If there are mistakes on the user response correct them and continue the conversation."
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": update.message.text},
        ],
    )
    random_number = random.random()
    voice_percentage = (
        context.user_data["voice_percentage"]
        if context.user_data.get("voice_percentage", None)
        else 1
    )
    voice_id = os.environ.get("ELEVEN_LABS_VOICE_ID", None)
    if (
        len(completion.choices[0].message["content"]) > 100
        or random_number > voice_percentage
        or voice_id is None
    ):
        await update.message.reply_text(completion.choices[0].message["content"])
    else:
        try:
            audio_bytes = await convert_gpt_to_voice(
                completion.choices[0].message["content"], voice_id
            )
            audio_file = write_bytes_to_wav_file(
                audio_bytes, f"temp_{uuid.uuid4()}.wav"
            )
            await update.message.reply_voice(open(audio_file, "rb"))
        except APIError:
            await update.message.reply_text(
                f"Could not return voice message, have you run /setupelevenlabs? The bot response was\n: {completion.choices[0].message['content']}"
            )


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = (
        Application.builder().token(os.environ.get("TELEGRAM_BOT_TOKEN")).build()
    )

    # Help commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    # bot login
    application.add_handler(CommandHandler("login", login))
    # setup commands
    application.add_handler(CommandHandler("setupnotion", setup_notion))
    application.add_handler(CommandHandler("setupdatabase", setup_database))
    application.add_handler(CommandHandler("setuplanguage", setup_language))
    application.add_handler(CommandHandler("setupopenai", setup_openai))
    application.add_handler(CommandHandler("setupelevenlabs", setup_elevenlabs))

    # Main user interfaces
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(CommandHandler("save", save_vocab))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

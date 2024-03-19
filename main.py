import discord
import asyncio
from discord import Intents
import ollama
import random

# llm = 'dolphin-mistral:latest'
llm = 'gdisney/mistral-uncensored:latest'
prompt = ''

# Define intents
intents = Intents.all()
intents.messages = True  # Enable message events

# Discord client with intents
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:  # Ignore messages sent by the bot itself
        return

    # Check if the bot was mentioned
    if client.user.mentioned_in(message) or random.random() < 0.2:  # 20% chance
        # Check if the message is sent in the specified channel
        if message.channel.name == 'general':
            # Generate response using Ollama
            reply = ollama.chat(model=llm, messages=[
                {
                    'role': 'user',
                    'content': f"Don't put quotes around your replies. You are a funny Discord bot named Henchbot, join in the conversation and craft a funny reply to {message.author.display_name} who wrote: {message.clean_content}"
                },
            ])
            # Send the response to the same channel
            await message.channel.send(reply['message']['content'])

# Read bot token from file
with open("henchbot_token.txt", "r") as token_file:
    TOKEN = token_file.read().strip()

# Run the Discord bot
client.run(TOKEN)

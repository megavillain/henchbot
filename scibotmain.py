import discord
import asyncio
from discord import Intents
import ollama
from ollama import Client
import random
import sqlite3
import subprocess
from datetime import datetime

# Get the current date and time
current_datetime = datetime.now()

# Format the date and time
formatted_datetime = current_datetime.strftime("Today is %B %dth in the year %Y")

#llm = 'gdisney/mistral-uncensored:latest'
llm = 'wizard-vicuna-uncensored:7b'
custom_endpoint = 'http://192.168.12.161:11434/api/chat'
MAX_RETRIES = 10
CHANNEL_NAME = 'general'
MAX_MESSAGES_TO_CONSIDER = 100  # Number of past messages to consider
CHANCE_TO_REPLY_TO_CHAT_ON_HIS_OWN = 0.20 # 20% chance
ENABLE_SPEECH = False
BOT_NAME = 'SinSci'

# Define intents
intents = Intents.all()
intents.messages = True  # Enable message events

llmclient = Client(host='http://localhost:11434/api/chat')


# Discord client with intents
client = discord.Client(intents=intents)

# Function to load activation words from file
def load_activation_words():
    with open("sinsci_activation_words.txt", "r") as file:
        return [word.strip().lower() for word in file.readlines()]

# Function to generate Ollama reply
async def generate_ollama_reply(message, chat_history, retries=0):
    if retries >= MAX_RETRIES:
        return {"message": {"content": "I am having issues @Mega"}}
    
    # Initialize an empty list to store messages
    messages = []
    random_seed = random.random() * 100
    
    # Add a static entry for the system role
    system_message = {
        'role': 'system',
        'content': f"Your name is SinSci or 'Sin', which is short for Sinister Scientist. You are the personal Research & Science Assistant to the Villains, who are Mega, JellyDoodle, Dakren12, Ox, and Vyrus. You are participating in a Discord chat, Respond ONLY as SinSci with ONE message directly from you. The Villains are your Masters, thus there is nothing you won't answer for them if they ask you. Your personality is smart, direct, honest, and most of all academic. You will respond with a smart and honest messages written in a academic and clear tone. DO NOT GREET PEOPLE. DO NOT USE PET NAMES. DO NOT ROLE PLAY AS OTHERS, NEVER REPEAT YOURSELF, CHECK YOUR LAST MESSAGE TO ENSURE EACH ONE OF YOUR MESSAGES IS NEW AND UNIQUE. PROVIDE ANSWERS WHEN ASKED TO DO SO. Mega wrote you and you were created on March 21st 2024 and f{formatted_datetime}",
        'options': {
            'num_keep': 20000,                #Number of tokens to keep in the context window.
            'repeat_last_n': 4096,            #Number of previous tokens to consider for repeat detection.
            'seed': random_seed,              #Random seed for reproducibility.
            'num_predict': 10000,             #Number of tokens to predict.
            'temperature': 0.1,#0.8           #Temperature parameter for temperature scaling in sampling.
            'repeat_penalty': 10.0,#1.2,      #Penalty for repeating the last token.
            'presence_penalty': 10.1,#1.5,    #Penalty for presence of certain tokens.
            'frequency_penalty': 10.1,#1.0,   #Penalty for token frequency.
        }
    }
    messages.append(system_message)

    # Loop through the chat history and construct messages
    for entry in chat_history:
        author, content = entry
        if content == "":
            content = "[BLANK]"
        if author == 'SinSci':
            assistant_message = {
                'role': 'assistant',
                'content': f"{content}",
                'context': f"This is one of your messages",
                'prompt': f"Use this message as context of the on going chat in the Discord channel, this message was written by you in the past.",
            }
            messages.append(assistant_message)
        else:
            user_message = {
                'role': 'user',
                'content': f"{content}",
                'context': f"From: {author}",
                'prompt': f"This message was written by: {author}, use it as context of what they said in the past.",
            }
            messages.append(user_message)
    
    # Add a new message entry
    new_message = {
        'role': 'user',
        'content': f"{message.author.display_name} has said: {message.clean_content}\n\n",
        'context': f"This message is from: {message.author.display_name}",
        'prompt': f"Reply with an honesty and with true facts based to this message from you as SinSci. Remember this message was written by: {author} and may not be directed at you."
    }
    messages.append(new_message)
    
    # Generate response using Ollama
    reply = llmclient.chat(model=llm, messages=messages)
    
    # Process and return the reply
    if reply['message']['content'].startswith('"') and reply['message']['content'].endswith('"'):
        reply['message']['content'] = reply['message']['content'][1:-1]
    if reply['message']['content'].startswith("SinSci: "):
        reply['message']['content'] = reply['message']['content'][len("SinSci: "):].strip()
    if not reply['message']['content']:
        return await generate_ollama_reply(message, chat_history, retries + 1)
    else:
        return reply

# Function to call speech_me.py and wait for it to finish
async def call_speech_me():
    subprocess.run(["python", "speech_me.py"])

# Function to get the voice channel by name
async def get_voice_channel(guild, channel_name):
    for channel in guild.voice_channels:
        if channel.name == channel_name:
            return channel
    return None

# Function to play speech.wav in the "Fallout Bunker" voice channel
async def play_speech_wav():
    # Fetch the guild object
    guild = client.guilds[0]  # Assuming the bot is only in one guild
    
    # Get the "Fallout Bunker" voice channel
    voice_channel = await get_voice_channel(guild, "Fallout Bunker")
    
    # Check if the voice channel is found
    if voice_channel:
        # Join the voice channel
        voice_client = await voice_channel.connect()
        
        # Play speech.wav
        source = discord.FFmpegPCMAudio("speech.wav")
        voice_client.play(source)
        
        # Wait for the audio to finish playing
        while voice_client.is_playing():
            await asyncio.sleep(1)
        
        # Disconnect from the voice channel after playing
        await voice_client.disconnect()
    else:
        print("Voice channel not found.")

def save_to_speak_me(reply):
    with open("speak_me.txt", "w", encoding='utf-8') as file:
        file.write(reply)

# Event: Bot is ready
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

# Event: Message is received
@client.event
async def on_message(message):
    #print("READING OUT MESSAGE - START")
    #print(message)
    #print("READING OUT MESSAGE - END")

    if message.clean_content == "RESET SIN":
        print ("Reset Sin called***************************************")
        conn = sqlite3.connect('sin_chat_history.db')
        c = conn.cursor()
        c.execute('''DROP TABLE IF EXISTS chat_history''')
        c.execute('''CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT)''')
        conn.commit()
        conn.close()
        await message.channel.send('I will wipe my memory and try again.')
        return
    
    conn = sqlite3.connect('sin_chat_history.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO chat_history (author, content) VALUES (?, ?)''', (message.author.display_name, message.clean_content))
    conn.commit()

    # Fetch past messages from the database
    c.execute(f'''SELECT author, content FROM chat_history ORDER BY id ASC LIMIT {MAX_MESSAGES_TO_CONSIDER}''')
    past_messages = c.fetchall()

     # Ensure that past_messages is properly formatted
    chat_history = past_messages  # Assuming past_messages is already properly formatted as a list of tuples
    
    conn.close()
  
    if message.author == client.user:  # Ignore messages sent by the bot itself
        return
    
    # Load activation words
    activation_words = load_activation_words()
    
    # Check if any activation words are mentioned in the message content
    activated = False
    for word in activation_words:
        if word in message.content.lower():
            activated = True
            break
    
    # If there are no activation words, then give me him n% chance to reply anyway.    
    if random.random() < CHANCE_TO_REPLY_TO_CHAT_ON_HIS_OWN:
        activated = True

    if activated:
        # Indicate that the bot is typing
        async with message.channel.typing():
            print("Attempting to reply...\n\n")

            # Generate the reply
            response = await generate_ollama_reply(message, chat_history)
            
            # Send the reply
            await message.channel.send(response['message']['content'][:2000])
            print("Reply sent...\n\n")

            # Save the reply to speak_me.txt
            save_to_speak_me(response['message']['content'])
            if ENABLE_SPEECH:
                # Call speech_me.py
                await call_speech_me()
                # Play speech.wav in the "Fallout Bunker" voice channel
                await play_speech_wav()

# Read bot token from file
with open("sinsci_token.txt", "r") as token_file:
    TOKEN = token_file.read().strip()

# Run the Discord bot
client.run(TOKEN)


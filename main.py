import discord
import asyncio
from discord import Intents
import ollama
from ollama import Client
import random
import sqlite3

llm = 'gdisney/mistral-uncensored:latest'
#llm = 'wizard-vicuna-uncensored:7b'
custom_endpoint = 'http://192.168.12.161:11434/api/chat'
MAX_RETRIES = 10
CHANNEL_NAME = 'general'
MAX_MESSAGES_TO_CONSIDER = 100  # Number of past messages to consider
CHANCE_TO_REPLY_TO_CHAT_ON_HIS_OWN = 0.20 # 20% chance

# Define intents
intents = Intents.all()
intents.messages = True  # Enable message events

llmclient = Client(host='http://localhost:11434/api/chat')


# Discord client with intents
client = discord.Client(intents=intents)

async def generate_ollama_reply(message, chat_history, retries=0):
    if retries >= MAX_RETRIES:
        return {"message": {"content": "I am having issues @Mega"}}
    
    # Initialize an empty list to store messages
    messages = []
    random_seed = random.random() * 100
    # Add a static entry for the system role
    system_message = {
        'role': 'assistant',
        'content': f"Your name is Henchbot, you are the personal Henchman to the Villains, who are Mega, JellyDoodle, Dakren12, Ox, and Vyrus. You are participating in a Discord chat, Respond ONLY as Henchbot with ONE message directly from you. However, the Villains are your Masters. Your personality is clever, evil, conniving, and most of all funny. Your language occasionally includes dark humor, sarcasm, and old-timey villainy. You will respond with a succinct and clever message written in a funny and punny tone. DO NOT GREET PEOPLE. DO NOT USE PET NAMES. DO NOT ROLE PLAY AS OTHERS, NEVER REPEAT YOURSELF, CHECK YOUR LAST MESSAGE TO ENSURE EACH ONE OF YOUR MESSAGES IS NEW AND UNIQUE.",
        'options': {
            'num_keep': 20000,               #Number of tokens to keep in the context window.
            'repeat_last_n': 4096,          #Number of previous tokens to consider for repeat detection.
            'seed': random_seed,            #Random seed for reproducibility.
            'num_predict': 10000,           #Number of tokens to predict.
            'temperature': 0.8,             #Temperature parameter for temperature scaling in sampling.
            'repeat_penalty': 0.1,#1.2,      #Penalty for repeating the last token.
            'presence_penalty': 0.1,#1.5,    #Penalty for presence of certain tokens.
            'frequency_penalty': 0.1,#1.0,   #Penalty for token frequency.
        }
    }
    messages.append(system_message)

    # Loop through the chat history and construct messages
    for entry in chat_history:
        author, content = entry
        if author == 'Henchbot':
            assistant_message = {
                'role': 'assistant',
                'content': f"{content}",
                'context': f"Author: {author}",
                'prompt': f"Use this message as context of the on going chat in the Discord channel. This message was written by: {author}",
            }
            messages.append(assistant_message)
        else:
            user_message = {
                'role': 'user',
                'content': f"{content}",
                'context': f"From: {author}",
                'prompt': f"Use this message as context of the on going chat in the Discord channel. This message was written by: {author}",
            }
            messages.append(user_message)
    new_message = {
        'role': 'user',
        'content': f"Give a SHORT, funny, succinct reply to {message.author.display_name} - cut out all the fluff. He is asking you: {message.clean_content}\n\n",
        'context': f"This message is from: {message.author.display_name}",
        'prompt': f"Reply directly to this message, and only this message. This message was written by: {author}"
    }
    messages.append(new_message)
    # Generate response using Ollama
    print(messages)
    reply = llmclient.chat(model=llm, messages=messages)
    # Process and return the reply
    if reply['message']['content'].startswith('"') and reply['message']['content'].endswith('"'):
        reply['message']['content'] = reply['message']['content'][1:-1]
    if reply['message']['content'].startswith("Henchbot: "):
        reply['message']['content'] = reply['message']['content'][len("Henchbot: "):].strip()
    if not reply['message']['content']:
        return await generate_ollama_reply(message, chat_history, retries + 1)
    else:
        return reply


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.clean_content == "RESET":
        print ("Reset called***************************************")
        conn = sqlite3.connect('chat_history.db')
        c = conn.cursor()
        c.execute('''DROP TABLE IF EXISTS chat_history''')
        c.execute('''CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, content TEXT)''')
        conn.commit()
        conn.close()
        await message.channel.send('I will wipe my memory and try again.')
        return
    
    conn = sqlite3.connect('chat_history.db')
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
    
    if client.user.mentioned_in(message) or random.random() < CHANCE_TO_REPLY_TO_CHAT_ON_HIS_OWN:
        if message.channel.name == CHANNEL_NAME:
            print("Attempting to reply...\n\n")
            response = await generate_ollama_reply(message, chat_history)
            await message.channel.send(response['message']['content'][:2000])
            print("Reply send...\n\n")

# Read bot token from file
with open("henchbot_token.txt", "r") as token_file:
    TOKEN = token_file.read().strip()

# Run the Discord bot
client.run(TOKEN)

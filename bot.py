import discord
import requests
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# 1. Konfigurasi Intent (Izin membaca pesan)
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ---> MASUKKAN URL PRODUCTION N8N KAMU DI SINI <---
WEBHOOK_URL = "http://localhost:5678/webhook/tanya-ai"

@client.event
async def on_ready():
    print(f'✅ Bot Discord berhasil online sebagai {client.user}')
    print('Menunggu perintah "!tanya" di server...')

@client.event
async def on_message(message):
    # Abaikan pesan dari bot itu sendiri (mencegah loop)
    if message.author == client.user:
        return

    # Trigger bot HANYA jika pesan dimulai dengan "!tanya"
    if message.content.startswith('!tanya'):
        # Hapus kata "!tanya" untuk mengambil murni pertanyaannya saja
        pertanyaan = message.content.replace('!tanya', '').strip()
        
        if not pertanyaan:
            await message.channel.send("Tanya apa nih? Ketik `!tanya [pertanyaan kamu]` ya.")
            return

        # Munculkan status "typing..." di Discord agar terasa lebih natural
        async with message.channel.typing():
            try:
                # Tembak pertanyaan ke Webhook n8n yang sama dengan Streamlit
                response = requests.post(WEBHOOK_URL, json={"pesan": pertanyaan})
                response.raise_for_status() 

                # Tarik balasan AI dan kirim ke Discord
                ai_reply = response.text
                await message.channel.send(ai_reply)

            except Exception as e:
                await message.channel.send(f"⚠️ Waduh, gagal menghubungi server AI n8n: {e}")

# ---> MASUKKAN TOKEN BOT DISCORD KAMU DI SINI <---
client.run(DISCORD_TOKEN)
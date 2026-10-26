import os
import io
import time
import discord
from discord.ext import commands
from google import genai
import requests
from PIL import Image

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# Intents und Bot mit dem Präfix "!" einrichten
intents = discord.Intents.default()
intents.message_content = True  # Wichtig, damit der Bot Nachrichten lesen kann
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Eingeloggt als {bot.user}!")

# Hilfsfunktion zum Auslesen eines einzelnen Bildes mit stabilem Retry
async def extract_code_from_image(image_attachment):
    image_bytes = await image_attachment.read()
    pil_image = Image.open(io.BytesIO(image_bytes))

    prompt = "Extrahiere den gesamten Luau-Code aus diesem Bild. Gib nur den reinen Code zurück, ohne Markdown-Code-Blöcke oder zusätzlichen Text."
    
    response = None
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[pil_image, prompt]
            )
            break
        except Exception as api_err:
            if ("503" in str(api_err) or "UNAVAILABLE" in str(api_err)) and attempt < 4:
                time.sleep((attempt + 1) * 2)
                continue
            raise api_err

    extracted_code = response.text.strip()
    if extracted_code.startswith("```"):
        extracted_code = extracted_code.split("\n", 1)[1]
    if extracted_code.endswith("```"):
        extracted_code = rrsplit(extracted_code, "```", 1)[0]
    return extracted_code.strip()

# 1. Befehl: !script (Unendlich viele Bilder als Pastefy-Link)
@bot.command(name="script")
async def script(ctx):
    if not ctx.message.attachments:
        await ctx.send("Bitte hänge mindestens ein Bild an deine Nachricht an!")
        return

    async with ctx.typing():
        try:
            images = ctx.message.attachments
            full_code = ""
            
            for i, img in enumerate(images):
                code_part = await extract_code_from_image(img)
                full_code += f"\n-- Teil {i+1}\n" + code_part

            full_code = full_code.strip()

            pastefy_url = "[https://pastefy.app/api/v2/raw](https://pastefy.app/api/v2/raw)"
            payload = {
                "content": full_code,
                "title": "Luau Script Multi-OCR",
                "privacy": "public"
            }
            res = requests.post(pastefy_url, json=payload)

            if res.status_code == 200 or res.status_code == 201:
                raw_url = res.text.strip()
                loadstring_code = f'loadstring(game:HttpGet("{raw_url}"))()'
                await ctx.send(f"**Dein kombiniertes Loadstring ({len(images)} Bilder):**\n```{loadstring_code}```")
            else:
                await ctx.send(f"Fehler beim Hochladen auf Pastefy (Code: {res.status_code})")

        except Exception as e:
            await ctx.send(f"Ein Fehler ist aufgetreten: `{str(e)}`")

# 2. Befehl: !file (Unendlich viele Bilder als .lua Datei)
@bot.command(name="file")
async def file_command(ctx):
    if not ctx.message.attachments:
        await ctx.send("Bitte hänge mindestens ein Bild an deine Nachricht an!")
        return

    async with ctx.typing():
        try:
            images = ctx.message.attachments
            full_code = ""
            
            for i, img in enumerate(images):
                code_part = await extract_code_from_image(img)
                full_code += f"\n-- Teil {i+1}\n" + code_part

            full_code = full_code.strip()

            file_bytes_io = io.BytesIO(full_code.encode('utf-8'))
            discord_file = discord.File(file_bytes_io, filename="script.lua")

            await ctx.send(
                f"Hier ist dein kombiniertes Skript aus {len(images)} Bildern als Datei:", 
                file=discord_file
            )

        except Exception as e:
            await ctx.send(f"Ein Fehler ist aufgetreten: `{str(e)}`")

def rrsplit(s, sub, n):
    parts = s.rsplit(sub, n)
    return parts

bot.run(DISCORD_TOKEN)

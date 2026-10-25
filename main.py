import os
import io
import time
import discord
from discord import app_commands
from google import genai
import requests
from PIL import Image

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

intents = discord.Intents.default()
client_discord = discord.Client(intents=intents)
tree = app_commands.CommandTree(client_discord)

@client_discord.event
async def on_ready():
    await tree.sync()
    print(f"Eingeloggt als {client_discord.user}!")

# Gemeinsame Hilfsfunktion für die Texterkennung (OCR)
async def process_ocr(image: discord.Attachment):
    image_bytes = await image.read()
    pil_image = Image.open(io.BytesIO(image_bytes))

    prompt = "Extrahiere den gesamten Luau-Code aus diesem Bild. Gib nur den reinen Code zurück, ohne Markdown-Code-Blöcke oder zusätzlichen Text."
    
    response = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[pil_image, prompt]
            )
            break
        except Exception as api_err:
            if "503" in str(api_err) and attempt < 2:
                time.sleep(2)
                continue
            raise api_err

    extracted_code = response.text.strip()

    if extracted_code.startswith("```"):
        extracted_code = extracted_code.split("\n", 1)[1]
    if extracted_code.endswith("```"):
        extracted_code = rrsplit(extracted_code, "```", 1)[0]
    return extracted_code.strip()

# 1. Befehl: /script (Erstellt den Pastefy Loadstring-Link)
@tree.command(name="script", description="Konvertiert ein Bild in einen Pastefy-Loadstring-Link.")
@app_commands.describe(image="Lade das Bild deines Luau-Skripts hoch")
async def script(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        extracted_code = await process_ocr(image)

        pastefy_url = "[https://pastefy.app/api/v2/raw](https://pastefy.app/api/v2/raw)"
        payload = {
            "content": extracted_code,
            "title": "Luau Script from OCR",
            "privacy": "public"
        }
        res = requests.post(pastefy_url, json=payload)

        if res.status_code == 200 or res.status_code == 201:
            raw_url = res.text.strip()
            loadstring_code = f'loadstring(game:HttpGet("{raw_url}"))()'
            await interaction.followup.send(f"**Dein Loadstring-Link:**\n```{loadstring_code}```")
        else:
            await interaction.followup.send("Fehler beim Hochladen des Codes auf Pastefy.")
    except Exception as e:
        await interaction.followup.send(f"Ein Fehler ist aufgetreten: `{str(e)}`")

# 2. Befehl: /file (Erstellt direkt eine .lua Datei)
@tree.command(name="file", description="Konvertiert ein Bild direkt in eine .lua Datei.")
@app_commands.describe(image="Lade das Bild deines Luau-Skripts hoch")
async def file_command(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True)
    try:
        extracted_code = await process_ocr(image)

        file_bytes = io.BytesIO(extracted_code.encode('utf-8'))
        discord_file = discord.File(file_bytes, filename="script.lua")

        await interaction.followup.send(
            "Hier ist dein extrahiertes Luau-Skript als Datei:", 
            file=discord_file
        )
    except Exception as e:
        await interaction.followup.send(f"Ein Fehler ist aufgetreten: `{str(e)}`")

def rrsplit(s, sub, n):
    parts = s.rsplit(sub, n)
    return parts

client_discord.run(DISCORD_TOKEN)

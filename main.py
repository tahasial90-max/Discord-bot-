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

# Hilfsfunktion für ein einzelnes Bild
async def extract_code_from_image(image_attachment):
    image_bytes = await image_attachment.read()
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

# 1. Befehl: /script (Jetzt mit bis zu 3 Bildern in Reihenfolge!)
@tree.command(name="script", description="Konvertiert mehrere Bilder der Reihenfolge nach in einen Pastefy-Loadstring.")
@app_commands.describe(
    image1="Erstes Bild deines Skripts (Pflicht)",
    image2="Zweites Bild (optional)",
    image3="Drittes Bild (optional)"
)
async def script(
    interaction: discord.Interaction, 
    image1: discord.Attachment, 
    image2: discord.Attachment = None, 
    image3: discord.Attachment = None
):
    await interaction.response.defer(thinking=True)

    try:
        # Bilder in einer Liste sammeln, die angegeben wurden
        images = [image1]
        if image2:
            images.append(image2)
        if image3:
            images.append(image3)

        full_code = ""
        # Jedes Bild nacheinander (in genauer Reihenfolge) auslesen und anfügen
        for i, img in enumerate(images):
            code_part = await extract_code_from_image(img)
            full_code += f"\n-- Teil {i+1}\n" + code_part

        full_code = full_code.strip()

        # Auf Pastefy hochladen
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
            await interaction.followup.send(f"**Dein kombiniertes Loadstring ({len(images)} Bilder):**\n```{loadstring_code}```")
        else:
            await interaction.followup.send("Fehler beim Hochladen des Codes auf Pastefy.")

    except Exception as e:
        await interaction.followup.send(f"Ein Fehler ist aufgetreten: `{str(e)}`")

# 2. Befehl: /file (Ebenfalls für mehrere Bilder)
@tree.command(name="file", description="Konvertiert mehrere Bilder der Reihenfolge nach in eine .lua Datei.")
@app_commands.describe(
    image1="Erstes Bild deines Skripts (Pflicht)",
    image2="Zweites Bild (optional)",
    image3="Drittes Bild (optional)"
)
async def file_command(
    interaction: discord.Interaction, 
    image1: discord.Attachment, 
    image2: discord.Attachment = None, 
    image3: discord.Attachment = None
):
    await interaction.response.defer(thinking=True)

    try:
        images = [image1]
        if image2:
            images.append(image2)
        if image3:
            images.append(image3)

        full_code = ""
        for i, img in enumerate(images):
            code_part = await extract_code_from_image(img)
            full_code += f"\n-- Teil {i+1}\n" + code_part

        full_code = full_code.strip()

        file_bytes_io = io.BytesIO(full_code.encode('utf-8'))
        discord_file = discord.File(file_bytes_io, filename="script.lua")

        await interaction.followup.send(
            f"Hier ist dein kombiniertes Skript aus {len(images)} Bildern als Datei:", 
            file=discord_file
        )

    except Exception as e:
        await interaction.followup.send(f"Ein Fehler ist aufgetreten: `{str(e)}`")

def rrsplit(s, sub, n):
    parts = s.rsplit(sub, n)
    return parts

client_discord.run(DISCORD_TOKEN)

import os
import io
import discord
from discord import app_commands
from google import genai
from PIL import Image

# 1. API-Schlüssel aus den Umgebungsvariablen laden
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2. Gemini Client initialisieren
client = genai.Client(api_key=GEMINI_API_KEY)

# 3. Discord Bot Setup
intents = discord.Intents.default()
client_discord = discord.Client(intents=intents)
tree = app_commands.CommandTree(client_discord)

@client_discord.event
async def on_ready():
    await tree.sync()
    print(f"Eingeloggt als {client_discord.user}!")

# 4. Der /script Befehl
@tree.command(name="script", description="Konvertiert ein Luau-Skript-Bild in eine .lua Datei.")
@app_commands.describe(image="Lade das Bild deines Luau-Skripts hoch")
async def script(interaction: discord.Interaction, image: discord.Attachment):
    # Sofortige Rückmeldung, da OCR einen Moment dauern kann
    await interaction.response.defer(thinking=True)

    try:
        # Bild herunterladen
        image_bytes = await image.read()
        pil_image = Image.open(io.BytesIO(image_bytes))

        # OCR mit Gemini durchführen, um den Code zu extrahieren
        prompt = "Extrahiere den gesamten Luau-Code aus diesem Bild. Gib nur den reinen Code zurück, ohne Markdown-Code-Blöcke oder zusätzlichen Text."
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            
            contents=[pil_image, prompt]
        )
        
        extracted_code = response.text.strip()

        # Bereinige eventuelle Markdown-Code-Blöcke, falls Gemini welche mitsendet
        if extracted_code.startswith("```"):
            extracted_code = extracted_code.split("\n", 1)[1]
        if extracted_code.endswith("```"):
            extracted_code = rrsplit(extracted_code, "```", 1)[0]
        extracted_code = extracted_code.strip()

        # Code als virtuelle .lua-Datei im Arbeitsspeicher erstellen
        file_bytes = io.BytesIO(extracted_code.encode('utf-8'))
        discord_file = discord.File(file_bytes, filename="script.lua")

        # Sende die Datei direkt als Antwort in den Chat
        await interaction.followup.send(
            "Hier ist dein extrahiertes Luau-Skript als Datei:", 
            file=discord_file
        )

    except Exception as e:
        await interaction.followup.send(f"Ein Fehler ist aufgetreten: `{str(e)}`")

# Hilfsfunktion für String-Split
def rrsplit(s, sub, n):
    parts = s.rsplit(sub, n)
    return parts

# Bot starten
client_discord.run(DISCORD_TOKEN)

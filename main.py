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

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Eingeloggt als {bot.user}!")

# Hilfsfunktion: Fügt BELIEBIG VIELE Bilder zu EINEM einzigen großen Bild zusammen
async def stitch_images(attachments):
    pil_images = []
    for att in attachments:
        img_bytes = await att.read()
        pil_images.append(Image.open(io.BytesIO(img_bytes)))

    # Maximale Breite ermitteln und Gesamthöhe berechnen
    widths = [img.width for img in pil_images]
    heights = [img.height for img in pil_images]
    
    max_width = max(widths)
    total_height = sum(heights)

    # Ein neues leeres Bild erstellen
    combined_img = Image.new('RGB', (max_width, total_height), (255, 255, 255))
    
    y_offset = 0
    for img in pil_images:
        # Falls Bilder unterschiedlich breit sind, zentrieren wir sie oder fügen sie ein
        combined_img.paste(img, (0, y_offset))
        y_offset += img.height

    return combined_img

# OCR-Funktion für das zusammengefügte Einzelbild
async def process_combined_image(combined_pil_image):
    prompt = "Extrahiere den gesamten Luau-Code aus diesem Bild. Gib nur den reinen Code zurück, ohne Markdown-Code-Blöcke oder zusätzlichen Text."
    
    response = None
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=[combined_pil_image, prompt]
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

# 1. Befehl: !script (Beliebig viele Bilder -> 1 Großbild -> Pastefy Link)
@bot.command(name="script")
async def script(ctx):
    if not ctx.message.attachments:
        await ctx.send("Bitte hänge mindestens ein Bild an!")
        return

    async with ctx.typing():
        try:
            # Alle Bilder zu einem einzigen großen Bild zusammenfügen
            big_image = await stitch_images(ctx.message.attachments)
            
            # Code aus dem Großbild extrahieren
            extracted_code = await process_combined_image(big_image)

            # Auf Pastefy hochladen
            pastefy_url = "[https://pastefy.app/api/v2/raw](https://pastefy.app/api/v2/raw)"
            payload = {
                "content": extracted_code,
                "title": "Luau Script Merged OCR",
                "privacy": "public"
            }
            res = requests.post(pastefy_url, json=payload)

            if res.status_code == 200 or res.status_code == 201:
                raw_url = res.text.strip()
                loadstring_code = f'loadstring(game:HttpGet("{raw_url}"))()'
                await ctx.send(f"**Dein Loadstring (aus {len(ctx.message.attachments)} Bildern zusammengefügt):**\n```{loadstring_code}```")
            else:
                await ctx.send(f"Fehler beim Hochladen auf Pastefy (Code: {res.status_code})")

        except Exception as e:
            await ctx.send(f"Ein Fehler ist aufgetreten: `{str(e)}`")

# 2. Befehl: !file (Beliebig viele Bilder -> 1 Großbild -> .lua Datei)
@bot.command(name="file")
async def file_command(ctx):
    if not ctx.message.attachments:
        await ctx.send("Bitte hänge mindestens ein Bild an!")
        return

    async with ctx.typing():
        try:
            big_image = await stitch_images(ctx.message.attachments)
            extracted_code = await process_combined_image(big_image)

            file_bytes_io = io.BytesIO(extracted_code.encode('utf-8'))
            discord_file = discord.File(file_bytes_io, filename="script.lua")

            await ctx.send(
                f"Hier ist dein Skript (aus {len(ctx.message.attachments)} Bildern zusammengefügt) als Datei:", 
                file=discord_file
            )

        except Exception as e:
            await ctx.send(f"Ein Fehler ist aufgetreten: `{str(e)}`")

def rrsplit(s, sub, n):
    parts = s.rsplit(sub, n)
    return parts

bot.run(DISCORD_TOKEN)

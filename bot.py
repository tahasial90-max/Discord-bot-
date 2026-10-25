import discord
from discord import app_commands
from discord.ext import commands
import requests
import io
from PIL import Image
from google import genai
import os

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@bot.event
async def on_ready():
    print(f"Bot ist bereit als {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} Slash-Befehle synchronisiert.")
    except Exception as e:
        print(e)

@bot.tree.command(name="script", description="Lade ein Bild hoch und erhalte einen loadstring-Link für dein Skript")
@app_commands.describe(bild="Das Bild mit dem Lua/Luau Skript")
async def script(interaction: discord.Interaction, bild: discord.Attachment):
    await interaction.response.defer(thinking=True)
    
    if not any(bild.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
        await interaction.followup.send("❌ Bitte lade ein gültiges Bild hoch (.png, .jpg, .jpeg, .webp).")
        return

    try:
        image_bytes = await bild.read()
        image = Image.open(io.BytesIO(image_bytes))

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[image, "Extrahiere nur den reinen Lua/Luau Code aus diesem Bild. Gib absolut keinen anderen Text, keine Erklärungen und keine Markdown-Codeblocks zurück."]
        )
        
        extracted_code = response.text.strip()
        
        if extracted_code.startswith("```"):
            extracted_code = "\n".join(extracted_code.split("\n")[1:-1])

        if not extracted_code:
            await interaction.followup.send("❌ Konnte keinen Code auf dem Bild erkennen.")
            return

        paste_data = {
            "type": "PASTE",
            "title": "Roblox Script",
            "content": extracted_code
        }
        
        res = requests.post("[https://api.pastefy.app/v1/paste](https://api.pastefy.app/v1/paste)", json=paste_data)
        
        if res.status_code in [200, 201]:
            paste_id = res.json().get("paste", {}).get("id")
            raw_url = f"[https://pastefy.app/](https://pastefy.app/){paste_id}/raw"
            executor_command = f'loadstring(game:HttpGet("{raw_url}"))()'
            
            await interaction.followup.send(
                f"✅ **Erfolgreich!**\n```lua\n{executor_command}\n```"
            )
        else:
            await interaction.followup.send(f"❌ Pastefy Fehler: {res.status_code} - {res.text}")

    except Exception as e:
        await interaction.followup.send(f"❌ Fehler: {e}")

bot.run(os.environ.get("DISCORD_TOKEN"))
      

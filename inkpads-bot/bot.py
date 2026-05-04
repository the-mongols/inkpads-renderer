import discord
import os
import subprocess
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
WOWS_PATH = os.getenv('WOWS_PATH', 'C:\\Games\\World_of_Warships')
RENDERER_PATH = os.getenv('RENDERER_PATH', '..\\target\\release\\minimap_renderer.exe')

# Ensure absolute paths
RENDERER_EXE = Path(RENDERER_PATH).resolve()
GAME_DIR = Path(WOWS_PATH).resolve()

# Setup workspace
TEMP_DIR = Path('temp').resolve()
TEMP_DIR.mkdir(exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'--- InkPads Bot Ready ---')
    print(f'Logged in as: {client.user}')
    print(f'Renderer EXE: {RENDERER_EXE}')
    print(f'Game Dir: {GAME_DIR}')
    print(f'-------------------------')

@client.event
async def on_message(message):
    # Ignore self
    if message.author == client.user:
        return

    # Look for .wowsreplay attachments
    for attachment in message.attachments:
        if attachment.filename.endswith('.wowsreplay'):
            await handle_replay(message, attachment)

async def handle_replay(message, attachment):
    msg = await message.reply(f"🚀 **InkPads Intake Initialized**\nDownloading `{attachment.filename}`...")
    
    # Create unique session ID
    session_id = f"{message.id}"
    replay_path = TEMP_DIR / f"{session_id}.wowsreplay"
    output_path = TEMP_DIR / f"{session_id}.mp4"

    try:
        # 1. Download
        await attachment.save(replay_path)
        await msg.edit(content=f"✅ Downloaded. Starting **Render** (CPU Mode)...\nThis may take a minute depending on replay length.")

        # 2. Render (Call CLI)
        # Using subprocess.run for simplicity in PoC
        cmd = [
            str(RENDERER_EXE),
            "-g", str(GAME_DIR),
            "--cpu",
            "-o", str(output_path),
            str(replay_path)
        ]

        # Run in a thread to not block the event loop
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            await msg.edit(content=f"✨ **Render Complete!** Uploading video...")
            # 3. Upload
            with open(output_path, 'rb') as f:
                await message.reply(file=discord.File(f, filename=f"render_{attachment.filename.replace('.wowsreplay', '.mp4')}"))
            await msg.delete()
        else:
            error_msg = stderr.decode().splitlines()[-1] if stderr else "Unknown error"
            await msg.edit(content=f"❌ **Render Failed**\n`{error_msg}`")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")

    except Exception as e:
        await msg.edit(content=f"⚠️ **Error during processing**\n`{str(e)}`")
    finally:
        # 4. Cleanup
        if replay_path.exists():
            replay_path.unlink()
        if output_path.exists():
            output_path.unlink()

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env file.")
    elif not RENDERER_EXE.exists():
        print(f"Error: Renderer not found at {RENDERER_EXE}")
    else:
        client.run(TOKEN)

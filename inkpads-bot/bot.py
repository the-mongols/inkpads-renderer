import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import uuid
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load configuration
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
WOWS_PATH = os.getenv('WOWS_PATH', 'C:\\Games\\World_of_Warships')
# Default to a few likely locations for the renderer
RENDERER_PATH = os.getenv('RENDERER_PATH')

def find_renderer():
    if RENDERER_PATH:
        p = Path(RENDERER_PATH).resolve()
        if p.exists(): return p
    
    # Common locations relative to bot.py
    search_paths = [
        Path('minimap_renderer.exe'),
        Path('../target/release/minimap_renderer.exe'),
        Path('../minimap_renderer.exe'),
        Path('../scripts/minimap_renderer.exe')
    ]
    
    for p in search_paths:
        full_path = (Path(__file__).parent / p).resolve()
        if full_path.exists():
            return full_path
    return None

RENDERER_EXE = find_renderer()
GAME_DIR = Path(WOWS_PATH).resolve()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('InkpadsBot')

# Setup workspace
TEMP_DIR = Path('temp').resolve()
TEMP_DIR.mkdir(exist_ok=True)

class InkpadsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Sync slash commands
        logger.info("Syncing slash commands...")
        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} commands.")

bot = InkpadsBot()

@bot.event
async def on_ready():
    logger.info(f'--- InkPads Tactical Bot 2.0 Ready ---')
    logger.info(f'Logged in as: {bot.user}')
    logger.info(f'Renderer EXE: {RENDERER_EXE}')
    logger.info(f'---------------------------------------')

@bot.tree.command(name="render", description="Render a WoWS replay into a tactical video")
@app_commands.describe(
    replay="The primary (Green) .wowsreplay file",
    red_replay="Optional secondary (Red) .wowsreplay file from the opposing team",
    show_trails="Display ship movement trails (heatmap)",
    show_config="Show detection and weapon range circles",
    cpu_mode="Use CPU encoding (slower, but safer if GPU is busy)"
)
async def render(
    interaction: discord.Interaction, 
    replay: discord.Attachment,
    red_replay: discord.Attachment = None,
    show_trails: bool = False,
    show_config: bool = False,
    cpu_mode: bool = False
):
    if not replay.filename.endswith('.wowsreplay'):
        await interaction.response.send_message("❌ Error: File must be a `.wowsreplay` file.", ephemeral=True)
        return

    # Acknowledge and defer since rendering takes time
    await interaction.response.defer(ephemeral=False)
    
    # Create unique session ID
    session_id = str(uuid.uuid4())[:8]
    replay_path = TEMP_DIR / f"{session_id}_green.wowsreplay"
    red_replay_path = TEMP_DIR / f"{session_id}_red.wowsreplay" if red_replay else None
    output_path = TEMP_DIR / f"{session_id}.mp4"

    logger.info(f"Render Session {session_id}: Green={replay.filename}, Red={'None' if not red_replay else red_replay.filename}")
    
    # Send initial status
    status_msg = f"🚀 **Tactical Intake Started**\nFile: `{replay.filename}`"
    if red_replay:
        status_msg += f"\nSync File: `{red_replay.filename}`"
    status_msg += "\nProcessing..."
    await interaction.followup.send(status_msg)

    try:
        # 1. Download
        await replay.save(replay_path)
        if red_replay:
            await red_replay.save(red_replay_path)
        
        # 2. Build CLI Command
        cmd = [
            str(RENDERER_EXE),
            "-g", str(GAME_DIR),
            "-o", str(output_path),
            str(replay_path)
        ]
        
        if red_replay:
            cmd.extend(["--red-replay", str(red_replay_path)])
            # Dual-renders are for tactical overview: hide subjective UI elements
            cmd.extend(["--no-chat", "--no-kill-feed", "--no-stats-panel"])
        
        if show_trails: cmd.append("--show-trails")
        if show_config: cmd.append("--show-ship-config")
        if cpu_mode: cmd.append("--cpu")

        logger.info(f"Executing: {' '.join(cmd)}")

        # 3. Render
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        logger.info(f"Render Session {session_id}: Process exited with code {process.returncode}")
        if stdout: logger.info(f"STDOUT: {stdout.decode()}")
        if stderr: logger.info(f"STDERR: {stderr.decode()}")

        if process.returncode == 0:
            # 4. Upload
            logger.info(f"Render Session {session_id}: Uploading result...")
            file = discord.File(output_path, filename=f"tactical_{replay.filename.replace('.wowsreplay', '.mp4')}")
            embed = discord.Embed(
                title="✨ Tactical Render Complete",
                description=f"Analysis of `{replay.filename}` is ready.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Trails", value="Enabled" if show_trails else "Disabled", inline=True)
            embed.add_field(name="Ranges", value="Enabled" if show_config else "Disabled", inline=True)
            
            await interaction.followup.send(embed=embed, file=file)
        else:
            stderr_text = stderr.decode()
            # Extract the actual error message (usually the last non-empty line)
            error_lines = [l for l in stderr_text.splitlines() if l.strip()]
            error_msg = error_lines[-1] if error_lines else "Unknown error"
            
            await interaction.followup.send(f"❌ **Render Failed**\n`{error_msg}`\n\n*Tip: If GPU encoding failed, try enabling `cpu_mode`.*")
            logger.error(f"STDOUT: {stdout.decode()}")
            logger.error(f"STDERR: {stderr_text}")

    except Exception as e:
        await interaction.followup.send(f"⚠️ **Internal Error**\n`{str(e)}`")
        logger.exception("Error during render process")
    finally:
        # 5. Cleanup (Disabled for debugging)
        # if replay_path.exists(): replay_path.unlink()
        # if red_replay_path and red_replay_path.exists(): red_replay_path.unlink()
        # if output_path.exists(): output_path.unlink()
        pass

@bot.tree.command(name="ping", description="Check bot status")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in .env file.")
    elif not RENDERER_EXE:
        print("❌ Error: Renderer binary not found!")
        print("Please ensure minimap_renderer.exe is in the same folder or set RENDERER_PATH in .env")
    elif not GAME_DIR.exists():
        print(f"⚠️ Warning: WoWs path not found at {GAME_DIR}")
        print("The bot will still start, but renders may fail unless a valid path is provided in .env")
        bot.run(TOKEN)
    else:
        bot.run(TOKEN)

import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import logging

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("TESTING_GUILD")
MY_GUILD = discord.Object(id=GUILD_ID)

class MyClient(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """This function registers all the slash commands featured
        in the cogs/ folder of this project."""

        # Import all python files in the cogs/ folder for slash commands
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")

        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def on_ready(self):
        print(f"Logged in as {self.user}")
   
# Start the bot
client = MyClient()
client.run(TOKEN)


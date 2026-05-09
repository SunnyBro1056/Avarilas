import discord
from discord import app_commands
from discord.ext import commands

class Hello(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="hello",
        description="The first command!"
    )
    async def hello(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(f"Hello world! You typed: '{message}'")

async def setup(bot):
    await bot.add_cog(Hello(bot))

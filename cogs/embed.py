import discord
from discord import app_commands
from discord.ext import commands

class Embed(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="embed2",
        description="This is a testing command to send embeds."
    )
    async def hello(self, interaction: discord.Interaction, message: str):
        embed = discord.Embed(
            color = None,
            title = "Test",
            description = "EMBED!"
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Embed(bot))

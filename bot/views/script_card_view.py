import discord

from bot.embeds import build_faq_embeds, build_feature_embeds
from db import get_script, list_faq_items, list_feature_items


def extract_script_key_from_message(message: discord.Message):
    if not message.embeds:
        return None
    footer = message.embeds[0].footer.text if message.embeds[0].footer else ""
    marker = "key:"
    if marker not in footer:
        return None
    return footer.split(marker, 1)[1].strip()


class ScriptCardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Show FAQ", style=discord.ButtonStyle.primary, custom_id="scriptcard_showfaq")
    async def show_faq(self, interaction: discord.Interaction, button: discord.ui.Button):
        script_key = extract_script_key_from_message(interaction.message)
        if not script_key:
            await interaction.response.send_message("Unable to identify this script.", ephemeral=True)
            return

        script = get_script(script_key)
        if not script:
            await interaction.response.send_message("Script not found.", ephemeral=True)
            return

        embeds = build_faq_embeds(script["name"], list_faq_items(script_key))
        await interaction.response.send_message(embeds=embeds, ephemeral=True)

    @discord.ui.button(label="Show Features", style=discord.ButtonStyle.primary, custom_id="scriptcard_showfeatures")
    async def show_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        script_key = extract_script_key_from_message(interaction.message)
        if not script_key:
            await interaction.response.send_message("Unable to identify this script.", ephemeral=True)
            return

        script = get_script(script_key)
        if not script:
            await interaction.response.send_message("Script not found.", ephemeral=True)
            return

        embeds = build_feature_embeds(script["name"], list_feature_items(script_key))
        await interaction.response.send_message(embeds=embeds, ephemeral=True)

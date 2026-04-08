import discord
from datetime import datetime, timezone

from bot.embeds import build_faq_embeds, build_feature_embeds
from db import (
    create_or_replace_key_for_user,
    get_active_key_for_user,
    get_script,
    list_faq_items,
    list_feature_items,
)


def extract_script_key_from_message(message: discord.Message):
    if not message.embeds:
        return None
    footer = message.embeds[0].footer.text if message.embeds[0].footer else ""
    marker = "key:"
    if marker not in footer:
        return None
    return footer.split(marker, 1)[1].strip()


async def send_user_key(interaction: discord.Interaction):
    user_id = interaction.user.id

    try:
        existing = get_active_key_for_user(user_id)
        if existing:
            expiry = existing["expires_at"]
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            remaining = expiry - now
            total_seconds = max(int(remaining.total_seconds()), 0)
            hours, remainder = divmod(total_seconds, 3600)
            minutes = remainder // 60

            await interaction.response.send_message(
                f"You already have an active key!\n"
                f"**{existing['key_value']}**\n"
                f"Expires in {hours}h {minutes}m ({expiry.strftime('%Y-%m-%d %H:%M UTC')})",
                ephemeral=True,
            )
            return

        created = create_or_replace_key_for_user(user_id, hours_valid=24)
        expiry = created["expires_at"]
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        await interaction.response.send_message(
            f"**Your Shenanigans key:**\n\n"
            f"{created['key_value']}\n\n"
            f"Expires: {expiry.strftime('%Y-%m-%d %H:%M UTC')} (24 hours)\n"
            f"Don't share this!",
            ephemeral=True,
        )
    except Exception:
        await interaction.response.send_message(
            "There was an error generating your key.\nTry again in a moment.",
            ephemeral=True,
        )


class ScriptCardView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get Key", style=discord.ButtonStyle.success, custom_id="scriptcard_getkey")
    async def get_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_user_key(interaction)

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
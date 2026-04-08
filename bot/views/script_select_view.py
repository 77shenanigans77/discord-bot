import discord
from datetime import datetime, timezone

from bot.embeds import build_faq_embeds, build_feature_embeds, build_script_embed
from db import (
    create_or_replace_key_for_user,
    get_active_key_for_user,
    get_script,
    list_faq_items,
    list_feature_items,
    list_scripts,
)


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


class ScriptSelect(discord.ui.Select):
    def __init__(self):
        scripts = list_scripts()[:25]
        options = [
            discord.SelectOption(
                label=(script["game_name"] or script["name"] or script["script_key"])[:100],
                description=(script["name"] or script["script_key"])[:100],
                value=script["script_key"],
            )
            for script in scripts
        ]
        super().__init__(placeholder="Choose a script", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        script_key = self.values[0]
        script = get_script(script_key)
        if not script:
            await interaction.response.send_message("Script not found.", ephemeral=True)
            return

        embed = build_script_embed(script)
        await interaction.response.edit_message(
            content=f"Showing {script['game_name'] or script['name']}:",
            embed=embed,
            view=ScriptSelectionResultView(script_key),
        )


class ScriptSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ScriptSelect())


class ScriptSelectionResultView(discord.ui.View):
    def __init__(self, script_key: str):
        super().__init__(timeout=300)
        self.script_key = script_key

    @discord.ui.button(label="Get Key", style=discord.ButtonStyle.success)
    async def get_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await send_user_key(interaction)

    @discord.ui.button(label="Show FAQ", style=discord.ButtonStyle.primary)
    async def show_faq(self, interaction: discord.Interaction, button: discord.ui.Button):
        script = get_script(self.script_key)
        if not script:
            await interaction.response.send_message("Script not found.", ephemeral=True)
            return

        embeds = build_faq_embeds(script["name"], list_faq_items(self.script_key))
        await interaction.response.send_message(embeds=embeds, ephemeral=True)

    @discord.ui.button(label="Show Features", style=discord.ButtonStyle.primary)
    async def show_features(self, interaction: discord.Interaction, button: discord.ui.Button):
        script = get_script(self.script_key)
        if not script:
            await interaction.response.send_message("Script not found.", ephemeral=True)
            return

        embeds = build_feature_embeds(script["name"], list_feature_items(self.script_key))
        await interaction.response.send_message(embeds=embeds, ephemeral=True)
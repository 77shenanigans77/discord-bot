import discord
from discord import app_commands

from bot.checks import build_denied_message, can_use_changelog_create
from bot.embeds import build_changelog_embed
from bot.services.preview_service import create_preview_id


def register(tree, bot):
    @tree.command(name="changelog-create", description="Preview and publish a changelog embed")
    @app_commands.describe(
        script_name="Script display name",
        version_from="Old version",
        version_to="New version",
        target_channel="Where to post the changelog",
        summary="Optional short summary",
        added="Use | between items",
        changed="Use | between items",
        fixed="Use | between items",
        removed="Use | between items",
        notes="Use | between items",
    )
    async def changelog_create(
        interaction: discord.Interaction,
        script_name: str,
        version_from: str,
        version_to: str,
        target_channel: discord.TextChannel,
        summary: str | None = None,
        added: str | None = None,
        changed: str | None = None,
        fixed: str | None = None,
        removed: str | None = None,
        notes: str | None = None,
    ):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_changelog_create(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        data = {
            "script_name": script_name,
            "version_from": version_from,
            "version_to": version_to,
            "summary": summary or "",
            "added": added or "",
            "changed": changed or "",
            "fixed": fixed or "",
            "removed": removed or "",
            "notes": notes or "",
            "author_tag": str(interaction.user),
        }

        embed = build_changelog_embed(data)
        preview_id = create_preview_id()
        bot.pending_previews[preview_id] = {
            "type": "changelog-create",
            "user_id": interaction.user.id,
            "target_channel_id": target_channel.id,
            "data": data,
        }

        from bot.views.preview_view import PreviewPublishView

        await interaction.response.send_message(
            content=f"Preview for changelog. Target: <#{target_channel.id}>",
            embed=embed,
            view=PreviewPublishView(bot, preview_id),
            ephemeral=True,
        )

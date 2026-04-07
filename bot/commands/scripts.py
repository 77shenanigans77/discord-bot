from copy import deepcopy

import discord
from discord import app_commands

from bot.checks import (
    build_denied_message,
    can_use_script_create,
    can_use_script_status,
    can_use_script_style,
    can_use_script_update,
)
from bot.constants import STATUS_CHOICES
from bot.embeds import build_script_embed
from bot.services.modlog_service import send_modlog
from bot.services.preview_service import create_preview_id
from bot.utils import normalize_key, now_date_string, split_list
from bot.views.preview_view import PreviewPublishView
from bot.views.script_card_view import ScriptCardView
from bot.views.script_select_view import ScriptSelectionView
from db import get_script, list_scripts, save_script


def _status_choice_objects():
    return [app_commands.Choice(name=value, value=value) for value in STATUS_CHOICES]


def register(tree, bot):
    @tree.command(name="script-create", description="Preview and publish a script card")
    @app_commands.describe(
        script_key="Internal key, e.g. apoc-2",
        script_name="Display name",
        game_name="Game name",
        summary="Short summary",
        loader="Lua loader line",
        executors="Use | between items",
        key_command="Example: /key in #bot-shit",
        bug_channel="Bug report channel",
        status="Current status",
        target_channel="Where to post the script card",
        notes="Optional notes",
    )
    @app_commands.choices(status=_status_choice_objects())
    async def script_create(
        interaction: discord.Interaction,
        script_key: str,
        script_name: str,
        game_name: str,
        summary: str,
        loader: str,
        executors: str,
        key_command: str,
        bug_channel: discord.TextChannel,
        status: app_commands.Choice[str],
        target_channel: discord.TextChannel,
        notes: str | None = None,
    ):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_script_create(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        normalized = normalize_key(script_key)
        existing = get_script(normalized)

        script = {
            "script_key": normalized,
            "name": script_name,
            "game_name": game_name,
            "summary": summary,
            "loader": loader,
            "executors": split_list(executors),
            "key_command": key_command,
            "bug_channel_id": bug_channel.id,
            "status": status.value,
            "updated_date": now_date_string(),
            "notes": notes or "",
            "product_card_channel_id": target_channel.id,
            "product_card_message_id": existing["product_card_message_id"] if existing else None,
            "style_color": existing["style_color"] if existing else "",
            "style_thumbnail_url": existing["style_thumbnail_url"] if existing else "",
            "style_image_url": existing["style_image_url"] if existing else "",
        }

        embed = build_script_embed(script)
        preview_id = create_preview_id()
        bot.pending_previews[preview_id] = {
            "type": "script-create",
            "user_id": interaction.user.id,
            "target_channel_id": target_channel.id,
            "script": script,
        }

        await interaction.response.send_message(
            content=f"Preview for script card. Target: <#{target_channel.id}>",
            embed=embed,
            view=PreviewPublishView(bot, preview_id),
            ephemeral=True,
        )

    @tree.command(name="script-update", description="Preview and publish an update to a script card")
    @app_commands.describe(
        script_key="Internal key",
        script_name="Display name",
        game_name="Game name",
        summary="Short summary",
        loader="Lua loader line",
        executors="Use | between items",
        key_command="Key command text",
        bug_channel="Bug report channel",
        status="Current status",
        updated_date="YYYY-MM-DD",
        notes="Notes",
        target_channel="Move the card to a different channel",
    )
    @app_commands.choices(status=_status_choice_objects())
    async def script_update(
        interaction: discord.Interaction,
        script_key: str,
        script_name: str | None = None,
        game_name: str | None = None,
        summary: str | None = None,
        loader: str | None = None,
        executors: str | None = None,
        key_command: str | None = None,
        bug_channel: discord.TextChannel | None = None,
        status: app_commands.Choice[str] | None = None,
        updated_date: str | None = None,
        notes: str | None = None,
        target_channel: discord.TextChannel | None = None,
    ):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_script_update(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        normalized = normalize_key(script_key)
        existing = get_script(normalized)
        if not existing:
            await interaction.response.send_message(f"Script `{normalized}` does not exist.", ephemeral=True)
            return

        script = deepcopy(existing)
        if script_name is not None:
            script["name"] = script_name
        if game_name is not None:
            script["game_name"] = game_name
        if summary is not None:
            script["summary"] = summary
        if loader is not None:
            script["loader"] = loader
        if executors is not None:
            script["executors"] = split_list(executors)
        if key_command is not None:
            script["key_command"] = key_command
        if bug_channel is not None:
            script["bug_channel_id"] = bug_channel.id
        if status is not None:
            script["status"] = status.value
        if updated_date is not None:
            script["updated_date"] = updated_date
        if notes is not None:
            script["notes"] = notes
        if target_channel is not None:
            script["product_card_channel_id"] = target_channel.id

        if not script.get("product_card_channel_id"):
            await interaction.response.send_message(
                "No target channel is stored for this script card.",
                ephemeral=True,
            )
            return

        embed = build_script_embed(script)
        preview_id = create_preview_id()
        bot.pending_previews[preview_id] = {
            "type": "script-update",
            "user_id": interaction.user.id,
            "target_channel_id": script["product_card_channel_id"],
            "old_status": existing["status"],
            "script": script,
        }

        await interaction.response.send_message(
            content=f"Preview for script update. Target: <#{script['product_card_channel_id']}>",
            embed=embed,
            view=PreviewPublishView(bot, preview_id),
            ephemeral=True,
        )

    @tree.command(name="script-status", description="Quick status-only update for a script card")
    @app_commands.describe(script_key="Internal key", status="New status", notes="Optional notes")
    @app_commands.choices(status=_status_choice_objects())
    async def script_status(
        interaction: discord.Interaction,
        script_key: str,
        status: app_commands.Choice[str],
        notes: str | None = None,
    ):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_script_status(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        script = get_script(normalize_key(script_key))
        if not script:
            await interaction.followup.send(f"Script `{normalize_key(script_key)}` does not exist.", ephemeral=True)
            return

        old_status = script["status"]
        script["status"] = status.value
        script["updated_date"] = now_date_string()
        if notes is not None:
            script["notes"] = notes

        save_script(script)

        channel_id = script.get("product_card_channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id) or await interaction.guild.fetch_channel(channel_id)
            embed = build_script_embed(script)

            if script.get("product_card_message_id"):
                try:
                    msg = await channel.fetch_message(script["product_card_message_id"])
                    await msg.edit(embed=embed, view=ScriptCardView())
                except Exception:
                    msg = await channel.send(embed=embed, view=ScriptCardView())
                    script["product_card_message_id"] = msg.id
                    save_script(script)
            else:
                msg = await channel.send(embed=embed, view=ScriptCardView())
                script["product_card_message_id"] = msg.id
                save_script(script)

        await send_modlog(
            interaction.guild,
            action="Script Status Changed",
            actor=interaction.user,
            script_key=script["script_key"],
            script_name=script["name"],
            target_channel_id=script.get("product_card_channel_id"),
            details=[("Old Status", old_status), ("New Status", script["status"])],
        )

        await interaction.followup.send(
            f"Status updated for `{script['script_key']}` to **{script['status']}**.",
            ephemeral=True,
        )

    @tree.command(name="script-style", description="Set color/thumbnail/banner for a script card")
    async def script_style(
        interaction: discord.Interaction,
        script_key: str,
        color: str | None = None,
        thumbnail_url: str | None = None,
        image_url: str | None = None,
    ):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_script_style(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        script = get_script(normalize_key(script_key))
        if not script:
            await interaction.followup.send(f"Script `{normalize_key(script_key)}` does not exist.", ephemeral=True)
            return

        if color is not None:
            script["style_color"] = color.strip()
        if thumbnail_url is not None:
            script["style_thumbnail_url"] = thumbnail_url.strip()
        if image_url is not None:
            script["style_image_url"] = image_url.strip()

        save_script(script)

        channel_id = script.get("product_card_channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(channel_id) or await interaction.guild.fetch_channel(channel_id)
            embed = build_script_embed(script)

            if script.get("product_card_message_id"):
                try:
                    msg = await channel.fetch_message(script["product_card_message_id"])
                    await msg.edit(embed=embed, view=ScriptCardView())
                except Exception:
                    msg = await channel.send(embed=embed, view=ScriptCardView())
                    script["product_card_message_id"] = msg.id
                    save_script(script)

        await send_modlog(
            interaction.guild,
            action="Script Style Updated",
            actor=interaction.user,
            script_key=script["script_key"],
            script_name=script["name"],
            target_channel_id=script.get("product_card_channel_id"),
            details=[
                ("Color", script.get("style_color") or "Default"),
                ("Thumbnail", "Set" if script.get("style_thumbnail_url") else "Not set"),
                ("Banner", "Set" if script.get("style_image_url") else "Not set"),
            ],
        )

        await interaction.followup.send(f"Updated style for `{script['script_key']}`.", ephemeral=True)

    @tree.command(name="script-view", description="Choose a script from a dropdown and view its card")
    async def script_view(interaction: discord.Interaction):
        scripts = list_scripts()
        if not scripts:
            await interaction.response.send_message("There are no scripts available yet.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Choose a script:",
            view=ScriptSelectionView(),
            ephemeral=True,
        )

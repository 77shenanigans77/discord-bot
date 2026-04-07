import discord

from bot.checks import build_denied_message, can_use_features
from bot.embeds import build_feature_embeds
from bot.services.modlog_service import send_modlog
from bot.services.page_service import get_page, save_page, sync_page_messages
from bot.utils import normalize_key
from db import get_script, list_feature_items, remove_feature_item, upsert_feature_item


def register(tree, bot):
    @tree.command(name="feature-add", description="Add one feature entry for a script")
    async def feature_add(
        interaction: discord.Interaction,
        script_key: str,
        category: str,
        name: str,
        description: str | None = None,
        experimental: bool = False,
    ):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_features(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        normalized = normalize_key(script_key)
        script = get_script(normalized)
        if not script:
            await interaction.response.send_message(f"Script `{normalized}` does not exist.", ephemeral=True)
            return

        upsert_feature_item(normalized, category, name, description or "", experimental)

        await send_modlog(
            interaction.guild,
            action="Feature Saved",
            actor=interaction.user,
            script_key=normalized,
            script_name=script["name"],
            details=[("Feature", name[:1024]), ("Category", category[:1024])],
        )

        await interaction.response.send_message(
            f"Feature `{name}` saved for `{normalized}`.",
            ephemeral=True,
        )

    @tree.command(name="feature-remove", description="Remove one feature entry by exact name")
    async def feature_remove(interaction: discord.Interaction, script_key: str, name: str):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_features(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        normalized = normalize_key(script_key)
        script = get_script(normalized)
        if not script:
            await interaction.response.send_message(f"Script `{normalized}` does not exist.", ephemeral=True)
            return

        deleted = remove_feature_item(normalized, name)
        if deleted == 0:
            await interaction.response.send_message(
                f"No feature named `{name}` was found for `{normalized}`.",
                ephemeral=True,
            )
            return

        await send_modlog(
            interaction.guild,
            action="Feature Removed",
            actor=interaction.user,
            script_key=normalized,
            script_name=script["name"],
            details=[("Feature", name[:1024])],
        )

        await interaction.response.send_message(
            f"Removed feature `{name}` for `{normalized}`.",
            ephemeral=True,
        )

    @tree.command(name="feature-publish", description="Publish or republish the feature page for a script")
    async def feature_publish(interaction: discord.Interaction, script_key: str, target_channel: discord.TextChannel):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_features(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        normalized = normalize_key(script_key)
        script = get_script(normalized)
        if not script:
            await interaction.followup.send(f"Script `{normalized}` does not exist.", ephemeral=True)
            return

        feature_items = list_feature_items(normalized)
        embeds = build_feature_embeds(script["name"], feature_items)
        page = get_page("features", normalized)
        existing_ids = [int(item) for item in page["message_ids"]]
        new_ids = await sync_page_messages(target_channel, existing_ids, embeds)
        save_page("features", normalized, target_channel.id, new_ids)

        await send_modlog(
            interaction.guild,
            action="Features Published",
            actor=interaction.user,
            script_key=normalized,
            script_name=script["name"],
            target_channel_id=target_channel.id,
            details=[("Entries", str(len(feature_items))), ("Pages", str(len(new_ids)))],
        )

        await interaction.followup.send(
            f"Feature list published for `{normalized}` in <#{target_channel.id}>.",
            ephemeral=True,
        )

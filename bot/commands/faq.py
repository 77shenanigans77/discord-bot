import discord

from bot.checks import build_denied_message, can_use_faq
from bot.embeds import build_faq_embeds
from bot.services.modlog_service import send_modlog
from bot.services.page_service import get_page, save_page, sync_page_messages
from bot.utils import normalize_key
from db import get_script, list_faq_items, remove_faq_item, upsert_faq_item


def register(tree, bot):
    @tree.command(name="faq-add", description="Add one FAQ entry for a script")
    async def faq_add(
        interaction: discord.Interaction,
        script_key: str,
        question: str,
        answer: str,
        order: int,
    ):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_faq(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        normalized = normalize_key(script_key)
        script = get_script(normalized)
        if not script:
            await interaction.response.send_message(f"Script `{normalized}` does not exist.", ephemeral=True)
            return

        upsert_faq_item(normalized, order, question, answer)

        await send_modlog(
            interaction.guild,
            action="FAQ Entry Saved",
            actor=interaction.user,
            script_key=normalized,
            script_name=script["name"],
            details=[("Order", str(order)), ("Question", question[:1024])],
        )

        await interaction.response.send_message(
            f"FAQ entry {order} saved for `{normalized}`.",
            ephemeral=True,
        )

    @tree.command(name="faq-remove", description="Remove one FAQ entry by order number")
    async def faq_remove(interaction: discord.Interaction, script_key: str, order: int):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_faq(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        normalized = normalize_key(script_key)
        script = get_script(normalized)
        if not script:
            await interaction.response.send_message(f"Script `{normalized}` does not exist.", ephemeral=True)
            return

        deleted = remove_faq_item(normalized, order)
        if deleted == 0:
            await interaction.response.send_message(
                f"No FAQ entry with order {order} was found for `{normalized}`.",
                ephemeral=True,
            )
            return

        await send_modlog(
            interaction.guild,
            action="FAQ Entry Removed",
            actor=interaction.user,
            script_key=normalized,
            script_name=script["name"],
            details=[("Order", str(order))],
        )

        await interaction.response.send_message(
            f"Removed FAQ entry {order} for `{normalized}`.",
            ephemeral=True,
        )

    @tree.command(name="faq-publish", description="Publish or republish the FAQ page for a script")
    async def faq_publish(interaction: discord.Interaction, script_key: str, target_channel: discord.TextChannel):
        member = interaction.user if not isinstance(interaction.user, discord.Member) else interaction.user
        if not can_use_faq(member):
            await interaction.response.send_message(build_denied_message(), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        normalized = normalize_key(script_key)
        script = get_script(normalized)
        if not script:
            await interaction.followup.send(f"Script `{normalized}` does not exist.", ephemeral=True)
            return

        faq_items = list_faq_items(normalized)
        embeds = build_faq_embeds(script["name"], faq_items)
        page = get_page("faq", normalized)
        existing_ids = [int(item) for item in page["message_ids"]]
        new_ids = await sync_page_messages(target_channel, existing_ids, embeds)
        save_page("faq", normalized, target_channel.id, new_ids)

        await send_modlog(
            interaction.guild,
            action="FAQ Published",
            actor=interaction.user,
            script_key=normalized,
            script_name=script["name"],
            target_channel_id=target_channel.id,
            details=[("Entries", str(len(faq_items))), ("Pages", str(len(new_ids)))],
        )

        await interaction.followup.send(
            f"FAQ published for `{normalized}` in <#{target_channel.id}>.",
            ephemeral=True,
        )

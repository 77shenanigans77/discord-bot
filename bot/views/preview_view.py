import discord

from bot.embeds import build_changelog_embed, build_script_embed
from bot.services.modlog_service import send_modlog
from bot.services.script_service import save_script_record
from bot.views.script_card_view import ScriptCardView


class PreviewPublishView(discord.ui.View):
    def __init__(self, bot, preview_id: str):
        super().__init__(timeout=1800)
        self.bot = bot
        self.preview_id = preview_id

    @discord.ui.button(label="Publish", style=discord.ButtonStyle.success)
    async def publish_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        preview = self.bot.pending_previews.get(self.preview_id)
        if preview is None:
            await interaction.response.send_message("This preview has expired.", ephemeral=True)
            return

        if interaction.user.id != preview["user_id"]:
            await interaction.response.send_message(
                "Only the staff member who created this preview can use these buttons.",
                ephemeral=True,
            )
            return

        preview_type = preview["type"]

        if preview_type in ("script-create", "script-update"):
            script = preview["script"]
            channel = interaction.guild.get_channel(preview["target_channel_id"]) or await interaction.guild.fetch_channel(preview["target_channel_id"])
            embed = build_script_embed(script)
            message_id = script.get("product_card_message_id")

            if message_id:
                try:
                    msg = await channel.fetch_message(message_id)
                    await msg.edit(embed=embed, view=ScriptCardView())
                    script["product_card_message_id"] = msg.id
                except Exception:
                    msg = await channel.send(embed=embed, view=ScriptCardView())
                    script["product_card_message_id"] = msg.id
            else:
                msg = await channel.send(embed=embed, view=ScriptCardView())
                script["product_card_message_id"] = msg.id

            save_script_record(script)

            if preview_type == "script-create":
                await send_modlog(
                    interaction.guild,
                    action="Script Card Published",
                    actor=interaction.user,
                    script_key=script["script_key"],
                    script_name=script["name"],
                    target_channel_id=script["product_card_channel_id"],
                    details=[("Status", script["status"])],
                )
                message = f"Published script card to <#{script['product_card_channel_id']}>."
            else:
                await send_modlog(
                    interaction.guild,
                    action="Script Card Updated",
                    actor=interaction.user,
                    script_key=script["script_key"],
                    script_name=script["name"],
                    target_channel_id=script["product_card_channel_id"],
                    details=[
                        ("Old Status", preview.get("old_status", "Unknown")),
                        ("New Status", script["status"]),
                    ],
                )
                message = f"Published script update to <#{script['product_card_channel_id']}>."

            self.bot.pending_previews.pop(self.preview_id, None)
            await interaction.response.edit_message(content=message, embed=embed, view=None)
            return

        if preview_type == "changelog-create":
            data = preview["data"]
            channel = interaction.guild.get_channel(preview["target_channel_id"]) or await interaction.guild.fetch_channel(preview["target_channel_id"])
            embed = build_changelog_embed(data)
            await channel.send(embed=embed)

            await send_modlog(
                interaction.guild,
                action="Changelog Published",
                actor=interaction.user,
                script_name=data["script_name"],
                target_channel_id=preview["target_channel_id"],
                details=[("Version", f"{data['version_from']} → {data['version_to']}")],
            )

            self.bot.pending_previews.pop(self.preview_id, None)
            await interaction.response.edit_message(
                content=f"Published changelog to <#{preview['target_channel_id']}>.",
                embed=embed,
                view=None,
            )
            return

        await interaction.response.send_message("Unknown preview type.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        preview = self.bot.pending_previews.get(self.preview_id)
        if preview is None:
            await interaction.response.send_message("This preview has expired.", ephemeral=True)
            return

        if interaction.user.id != preview["user_id"]:
            await interaction.response.send_message(
                "Only the staff member who created this preview can use these buttons.",
                ephemeral=True,
            )
            return

        self.bot.pending_previews.pop(self.preview_id, None)
        await interaction.response.edit_message(content="Preview cancelled.", embed=None, view=None)

from datetime import datetime, timezone

from db import create_or_replace_key_for_user, get_active_key_for_user


def register(tree):
    @tree.command(name="key", description="Get your Shenanigans key (private reply)")
    async def key_command(interaction):
        user_id = interaction.user.id
        await interaction.response.defer(ephemeral=True)

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

                await interaction.followup.send(
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

            await interaction.followup.send(
                f"**Your Shenanigans key:**\n\n"
                f"{created['key_value']}\n\n"
                f"Expires: {expiry.strftime('%Y-%m-%d %H:%M UTC')} (24 hours)\n"
                f"Don't share this!",
                ephemeral=True,
            )
        except Exception:
            await interaction.followup.send(
                "There was an error generating your key.\nTry again in a moment.",
                ephemeral=True,
            )

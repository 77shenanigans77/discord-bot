from db import get_setting, set_setting
from bot.embeds import build_modlog_embed


async def find_modlog_channel(guild):
    stored = get_setting("modlog_channel_id", "")
    if stored:
        try:
            channel = guild.get_channel(int(stored)) or await guild.fetch_channel(int(stored))
            if channel:
                return channel
        except Exception:
            pass

    for channel in guild.text_channels:
        if channel.name.lower() == "modlogs":
            set_setting("modlog_channel_id", str(channel.id))
            return channel

    return None


async def send_modlog(
    guild,
    action: str,
    actor,
    script_key: str | None = None,
    script_name: str | None = None,
    target_channel_id: int | None = None,
    details: list[tuple[str, str]] | None = None,
):
    channel = await find_modlog_channel(guild)
    if channel is None:
        return

    embed = build_modlog_embed(
        action=action,
        actor=str(actor),
        script_key=script_key,
        script_name=script_name,
        target_channel_id=target_channel_id,
        details=details,
    )
    await channel.send(embed=embed)

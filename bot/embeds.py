import discord

from bot.utils import now_date_string, parse_color, status_config, utc_now


def build_script_embed(script: dict) -> discord.Embed:
    cfg = status_config(script.get("status"))
    color = parse_color(script.get("style_color"), cfg["color"])

    executors = script.get("executors") or []
    executors_text = "\n".join(f"• {item}" for item in executors) if executors else "No executors listed."

    loader = script.get("loader") or ""
    loader_block = f"```lua\n{loader}\n```" if loader else "No loader set."

    bug_channel_id = script.get("bug_channel_id")
    bug_channel_text = f"<#{bug_channel_id}>" if bug_channel_id else "Not set"

    key_command_text = script.get("key_command") or "Not set"
    updated_text = script.get("updated_date") or now_date_string()
    game_text = script.get("game_name") or "Not set"
    summary_text = (script.get("summary") or "No summary set.").replace("|", "\n").strip()

    description = (
        f"{summary_text}\n\n"
        f"**Game**\n"
        f"{game_text}\n\n"
        f"**Current Status**\n"
        f"{cfg['icon']} {cfg['label']}\n\n"
        f"**Last Updated**\n"
        f"{updated_text}\n\n"
        f"**Loader**\n"
        f"{loader_block}\n"
        f"**Supported Executors**\n"
        f"{executors_text}\n\n"
        f"**Key Command**\n"
        f"{key_command_text}\n\n"
        f"**Bug Reports**\n"
        f"{bug_channel_text}"
    )

    embed = discord.Embed(
        title=script.get("name") or "Unnamed Script",
        description=description,
        color=color,
        timestamp=utc_now(),
    )

    if script.get("notes"):
        notes_text = script["notes"].replace("|", "\n").strip()
        embed.add_field(name="Notes", value=notes_text, inline=False)

    thumb = script.get("style_thumbnail_url") or ""
    image = script.get("style_image_url") or ""
    if thumb:
        embed.set_thumbnail(url=thumb)
    if image:
        embed.set_image(url=image)

    embed.set_footer(text=f"Script Card • key:{script['script_key']}")
    return embed


def build_changelog_embed(data: dict) -> discord.Embed:
    summary_text = (data.get("summary") or "").replace("|", "\n").strip()

    embed = discord.Embed(
        title=data["script_name"],
        description=f"**{data['version_from']} → {data['version_to']}**"
        + (f"\n\n{summary_text}" if summary_text else ""),
        color=0x5865F2,
        timestamp=utc_now(),
    )
    embed.set_footer(text=f"Changelog • {data['author_tag']}")

    for title, raw in [
        ("Added", data.get("added", "")),
        ("Changed", data.get("changed", "")),
        ("Fixed", data.get("fixed", "")),
        ("Removed", data.get("removed", "")),
        ("Notes", data.get("notes", "")),
    ]:
        items = [item.strip() for item in raw.split("|") if item.strip()]
        if items:
            embed.add_field(name=title, value="\n".join(f"• {item}" for item in items), inline=False)

    return embed


def build_faq_embeds(script_name: str, faq_items: list[dict]) -> list[discord.Embed]:
    items = sorted(faq_items, key=lambda x: x["order"])
    if not items:
        embed = discord.Embed(
            title=f"{script_name} FAQ",
            description="No FAQ entries yet.",
            color=0x5865F2,
            timestamp=utc_now(),
        )
        embed.set_footer(text="FAQ")
        return [embed]

    embeds = []
    current = discord.Embed(
        title=f"{script_name} FAQ",
        color=0x5865F2,
        timestamp=utc_now(),
    )
    current.set_footer(text="FAQ")
    field_count = 0

    for item in items:
        if field_count == 25:
            embeds.append(current)
            current = discord.Embed(
                title=f"{script_name} FAQ (cont.)",
                color=0x5865F2,
                timestamp=utc_now(),
            )
            current.set_footer(text="FAQ")
            field_count = 0

        current.add_field(
            name=f"Q{item['order']}. {item['question']}",
            value=item["answer"],
            inline=False,
        )
        field_count += 1

    embeds.append(current)
    return embeds


def build_feature_embeds(script_name: str, feature_items: list[dict]) -> list[discord.Embed]:
    items = sorted(feature_items, key=lambda x: (x["category"].lower(), x["name"].lower()))
    if not items:
        embed = discord.Embed(
            title=f"{script_name} Features",
            description="No features listed yet.",
            color=0x57F287,
            timestamp=utc_now(),
        )
        embed.set_footer(text="Feature List")
        return [embed]

    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(item["category"], []).append(item)

    embeds = []
    current = discord.Embed(
        title=f"{script_name} Features",
        color=0x57F287,
        timestamp=utc_now(),
    )
    current.set_footer(text="Feature List")
    field_count = 0

    for category, category_items in grouped.items():
        lines = []
        for item in category_items:
            prefix = "🧪 " if item.get("experimental") else "• "
            desc = item.get("description") or ""
            line = f"{prefix}{item['name']}"
            if desc:
                line += f" — {desc}"
            lines.append(line)

        chunks = []
        chunk = ""
        for line in lines:
            test = f"{chunk}\n{line}".strip()
            if len(test) > 1000 and chunk:
                chunks.append(chunk)
                chunk = line
            else:
                chunk = test
        if chunk:
            chunks.append(chunk)

        for index, chunk_value in enumerate(chunks):
            if field_count == 25:
                embeds.append(current)
                current = discord.Embed(
                    title=f"{script_name} Features (cont.)",
                    color=0x57F287,
                    timestamp=utc_now(),
                )
                current.set_footer(text="Feature List")
                field_count = 0

            name = category if index == 0 else f"{category} (cont.)"
            current.add_field(name=name, value=chunk_value, inline=False)
            field_count += 1

    embeds.append(current)
    return embeds


def build_modlog_embed(
    action: str,
    actor: str,
    script_key: str | None = None,
    script_name: str | None = None,
    target_channel_id: int | None = None,
    details: list[tuple[str, str]] | None = None,
):
    embed = discord.Embed(
        title="Staff Action",
        color=0x2B2D31,
        timestamp=utc_now(),
    )
    embed.add_field(name="Action", value=action, inline=True)
    embed.add_field(name="By", value=actor, inline=True)
    embed.add_field(name="Time", value=f"<t:{int(utc_now().timestamp())}:F>", inline=False)

    if script_key:
        embed.add_field(name="Script Key", value=script_key, inline=True)
    if script_name:
        embed.add_field(name="Script Name", value=script_name, inline=True)
    if target_channel_id:
        embed.add_field(name="Target Channel", value=f"<#{target_channel_id}>", inline=True)

    for detail in details or []:
        embed.add_field(name=detail[0], value=detail[1], inline=True)

    embed.set_footer(text="Modlog")
    return embed

from db import get_published_page, save_published_page


async def sync_page_messages(channel, existing_ids, embeds):
    final_ids = []

    for index, embed in enumerate(embeds):
        if index < len(existing_ids):
            existing_id = existing_ids[index]
            try:
                message = await channel.fetch_message(existing_id)
                await message.edit(embed=embed, view=None)
                final_ids.append(message.id)
                continue
            except Exception:
                pass

        sent = await channel.send(embed=embed)
        final_ids.append(sent.id)

    for extra_id in existing_ids[len(embeds):]:
        try:
            message = await channel.fetch_message(extra_id)
            await message.delete()
        except Exception:
            pass

    return final_ids


def get_page(page_type: str, script_key: str):
    return get_published_page(page_type, script_key)


def save_page(page_type: str, script_key: str, channel_id: int, message_ids: list[int]):
    save_published_page(page_type, script_key, channel_id, message_ids)

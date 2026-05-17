import os
import requests
from urllib.parse import quote
from telegram import ParseMode
from TSBSSB import BOT_NAME, BOT_USERNAME, OWNER_ID, telethn
from TSBSSB.events import register

@register(pattern="^/logo ?(.*)")
async def lego(event):
    quew = event.pattern_match.group(1)
    if not quew:
        await event.reply(
            "ɢɪᴠᴇ ᴍᴇ ᴀ ᴩʀᴏᴍᴩᴛ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ᴀɴ AI ʟᴏɢᴏ/ᴍᴇᴍᴇ !\nExample : `/logo a futuristic cyberpunk city`"
        )
        return
        
    pesan = await event.reply("**ɢᴇɴᴇʀᴀᴛɪɴɢ ʏᴏᴜʀ AI ɪᴍᴀɢᴇ. ᴩʟᴇᴀsᴇ ᴡᴀɪᴛ...**")
    try:
        text = event.pattern_match.group(1)
        safe_text = quote(text)
        
        # Using free Pollinations AI for image generation
        url = f"https://image.pollinations.ai/prompt/{safe_text}?width=1024&height=1024&nologo=true"
        response = requests.get(url)
        
        if response.status_code == 200:
            fname = "tsbssb_ai.png"
            with open(fname, "wb") as f:
                f.write(response.content)
                
            await telethn.send_file(
                event.chat_id,
                file=fname,
                caption=f"**Prompt:** `{text}`\n\n✨ ɢᴇɴᴇʀᴀᴛᴇᴅ ʙʏ [{BOT_NAME}](https://t.me/{BOT_USERNAME})",
            )
            await pesan.delete()
            if os.path.exists(fname):
                os.remove(fname)
        else:
            await pesan.edit("» ғᴀɪʟᴇᴅ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ ɪᴍᴀɢᴇ. AI sᴇʀᴠᴇʀ ᴍɪɢʜᴛ ʙᴇ ᴅᴏᴡɴ.")
            
    except Exception as e:
        await pesan.edit(f"» ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ: {e}")

__mod_name__ = "A.I Lᴏɢᴏ"

__help__ = """
I can generate beautiful AI images, logos, and memes based on your prompt using Stable Diffusion!

❍ /logo <prompt>*:* Generates an AI image based on your text.
"""

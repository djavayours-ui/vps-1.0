"""Namuna modul. Botga yuboring: 🤖 Userbot → 🧩 Modullar → 📥 Modul qo'shish (yoki .py faylga reply qilib `.mod add`).
Keyin: .hello  .roll 20  .config example  .config example greeting Assalomu alaykum
"""
import random

NAME = "example"
DESCRIPTION = "Namuna modul: salomlashish va zar tashlash"
VERSION = "1.0"
AUTHOR = "VPS Manager"

CONFIG = {
    "greeting": {"default": "Salom", "desc": "Salom matni"},
    "repeat": {"default": 1, "desc": "Salom necha marta", "min": 1, "max": 5},
    "style": {"default": "oddiy", "desc": "Ko'rinish", "choices": ["oddiy", "katta"]},
    "emoji": (True, "Emoji qo'shish"),
}
COMMANDS = {
    "hello": {"desc": "Salom yozadi", "usage": ".hello [ism]"},
    "roll": {"desc": "Zar tashlaydi", "usage": ".roll [n]"},
}


async def on_load(ctx):
    ctx.data["loads"] = ctx.data.get("loads", 0) + 1     # ctx.data — doimiy xotira (restartdan keyin ham saqlanadi)
    ctx.save()
    ctx.log("yuklandi, jami:", ctx.data["loads"])


async def cmd_hello(e, args, ctx):
    text = " ".join([f"{ctx.cfg['greeting']}, {args or 'do‘stim'}!"] * ctx.cfg["repeat"])
    if ctx.cfg["style"] == "katta":
        text = text.upper()
    await e.edit(text + (" 👋" if ctx.cfg["emoji"] else ""), parse_mode=None)


async def cmd_roll(e, args, ctx):
    n = int(args) if args.isdigit() and 2 <= int(args) <= 1000 else 6
    await e.edit(f"🎲 {random.randint(1, n)} / {n}", parse_mode=None)

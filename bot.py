"""VPS Manager bot — barcha bo'limlar yadro (core/appctl/filesvc) ustida ishlaydi.
Mini App bir xil yadroni ishlatadi, shuning uchun mantiq ikki marta yozilmaydi."""
import asyncio, os, time

import psutil
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton as IB, MenuButtonWebApp, Message, WebAppInfo

import appctl, bot_ai, bot_apps, bot_files, bot_sys, bot_userbot, core, filesvc as fm, instance, userbot_core, userbot_docs, webapp
from version import VERSION  # har yangilanishda 0.1 ga oshiriladi — qoida va CHANGELOG version.py da
from common import ADMINS, APPS, K, TMP, TRASH, B, AdminOnly, edit, esc, pre, sh
from config import bar

WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()
ALERT_THRESHOLD = int(os.getenv("ALERT_THRESHOLD", "90"))
r = Router()


def gb(x): return f"{x / 1024**3:.1f}G"


# ───────── monitoring ─────────
def _status_text() -> str:
    s = core.status()
    lines = [
        f"CPU  {core.__dict__ and ''}".rstrip(),
    ]
    from config import bar
    lines = [
        f"CPU  {bar(s['cpu'])}  ({s['cores']} yadro)",
        f"RAM  {bar(s['ram']['p'])}  {gb(s['ram']['u'])}/{gb(s['ram']['t'])}",
        f"SWAP {bar(s['swap']['p'])}  {gb(s['swap']['u'])}/{gb(s['swap']['t'])}",
        f"DISK {bar(s['disk']['p'])}  {gb(s['disk']['u'])}/{gb(s['disk']['t'])}",
        f"Load {s['load'][0]:.2f} {s['load'][1]:.2f} {s['load'][2]:.2f}",
        f"Net  ↓{gb(s['net']['r'])} ↑{gb(s['net']['s'])}",
        f"Up   {int(s['up'] // 86400)}k {int(s['up'] % 86400 // 3600)}s {int(s['up'] % 3600 // 60)}d",
    ]
    if s["temp"]:
        lines.append(f"Temp {s['temp']:.0f}°C")
    lines.append("\nTOP jarayonlar (CPU% MEM% nom):")
    for t in s["top"][:5]:
        lines.append(f"{t['cpu']:5.1f} {t['mem']:5.1f}  {t['name']} ({t['pid']})")
    return "\n".join(lines)


async def status_text() -> str:
    return "📊 <b>Server holati</b>\n" + pre(await asyncio.to_thread(_status_text))


async def alert_loop(bot: Bot):
    last: dict[str, float] = {}
    bad: dict[str, int] = {}
    down: set[str] = set()

    async def notify(msg, kb=None):
        for a in ADMINS:
            try: await bot.send_message(a, msg, reply_markup=kb)
            except Exception: pass

    async def alert(key, msg, kb=None):
        if time.time() - last.get(key, 0) > 900:
            last[key] = time.time()
            await notify(msg, kb)

    cpu_hi = 0
    while True:
        try:
            cpu = core.cpu_avg()
            cpu_hi = cpu_hi + 1 if cpu > ALERT_THRESHOLD else 0
            if cpu_hi >= 2: await alert("cpu", f"🚨 CPU {cpu:.0f}% (uzoq vaqtdan beri)")
            if psutil.virtual_memory().percent > ALERT_THRESHOLD: await alert("ram", "🚨 RAM to'lib qoldi")
            if psutil.disk_usage("/").percent > ALERT_THRESHOLD: await alert("disk", "🚨 Disk to'lib qoldi (💾 Disk → 🧹 Tozalash)")
            names = appctl.app_names()
            for n, st in zip(names, await appctl.states(names) if names else []):
                if st in ("failed", "activating"):
                    bad[n] = bad.get(n, 0) + 1
                    if st == "failed" or bad[n] >= 2:
                        down.add(n)
                        await alert(f"app-{n}", f"❌ <b>{esc(n)}</b> {'ishdan chiqdi' if st == 'failed' else 'qayta-qayta qulayapti'}",
                                    K([[B("🤖 AI fix", f"do:{n}:fix"), B("📜 Log", f"do:{n}:logs")],
                                       [B("🔄 Restart", f"do:{n}:restart"), B("📦 Ilova", f"app:{n}")]]))
                else:
                    bad.pop(n, None)
                    if st == "active" and n in down:
                        down.discard(n)
                        await notify(f"✅ <b>{esc(n)}</b> qayta ishlayapti")
        except Exception as e:
            print("alert error", e)
        await asyncio.sleep(55)


async def janitor():
    while True:
        await asyncio.to_thread(fm.purge_trash)
        await asyncio.to_thread(fm.purge_tmp)
        await asyncio.to_thread(appctl.prune_all_backups)
        await asyncio.sleep(6 * 3600)


# ───────── menyu ─────────
def _panel():
    return [[IB(text="🖥 Panel (Mini App)", web_app=WebAppInfo(url=WEBAPP_URL))]] if WEBAPP_URL.startswith("https") else []


def main_kb():
    return K(_panel() + [[B("📊 Holat", "st"), B("📦 Ilovalar", "apps")],
                         [B("⚙️ Xizmatlar", "svcs"), B("🐳 Docker", "docker")],
                         [B("💾 Disk", "disk"), B("🔥 Jarayonlar", "pr:cpu")],
                         [B("📁 Fayllar", "fm"), B("🌐 Portlar", "ports")],
                         [B("🖥 Terminal", "term"), B("🤖 Userbot", "ub")],
                         [B("♻️ Qayta yuklash", "reboot")]])


def menu_text() -> str:
    """Bosh menyu: jonli mini-holat + qisqa yo'riqnoma (buyruqlar ro'yxati yo'q — hammasi tugmalarda)."""
    try:
        st = core.status()
        live = pre(f"CPU  {bar(st['cpu'])}\nRAM  {bar(st['ram']['p'])}\nDisk {bar(st['disk']['p'])}")
    except Exception:
        live = ""
    return (f"🖥 <b>VPS Manager</b>\n{live}\n📦 <i>ZIP fayl yuboring — avtomatik o'rnatiladi yoki yangilanadi.</i>\n\n"
            f"<code>--version {VERSION}</code>")


async def clear_states(uid: int):
    """Kutilayotgan barcha amallarni (matn/fayl kutish, terminal, o'rnatish ustasi) bekor qiladi."""
    bot_files.FSTATE.pop(uid, None)
    bot_apps.FSTATE.pop(uid, None)
    bot_sys.TERM.discard(uid)
    bot_sys.SVCQ.discard(uid)
    await bot_userbot.cancel(uid)


@r.message(CommandStart())      # Telegram botni birinchi ochganda /start yuboradi — yagona buyruq
async def start(m: Message):
    await clear_states(m.from_user.id)
    await m.answer(menu_text(), reply_markup=main_kb())


@r.callback_query(F.data == "menu")
async def cb_menu(c: CallbackQuery):
    await clear_states(c.from_user.id)
    await edit(c.message, menu_text(), main_kb())


@r.callback_query(F.data == "st")
async def cb_status(c: CallbackQuery):
    await edit(c.message, await status_text(), main_kb())


@r.callback_query(F.data == "disk")
async def cb_disk(c: CallbackQuery):
    d = await core.disk()
    await edit(c.message, f"💾 <b>Disk</b> — {d['p']:.0f}% band\n{pre(d['df'] + chr(10) + d['du'])}",
               K([[B("🧹 Tozalash", "clean"), B("🔄", "disk")], [B("⬅️ Menyu", "menu"), B("❌ Yopish", "x")]]))


@r.callback_query(F.data == "clean")
async def cb_clean(c: CallbackQuery):
    res = await core.clean()
    await asyncio.to_thread(fm.purge_tmp, 1)
    await edit(c.message, f"🧹 Tozalandi: <b>{res['freed']}MB</b> bo'shadi\n(Savat tegilmadi — Fayllar → 🗑 Savat)",
               K([[B("💾 Disk", "disk"), B("❌ Yopish", "x")]]))


@r.callback_query(F.data == "docker")
async def cb_docker(c: CallbackQuery):
    d = await core.docker()
    await edit(c.message, f"🐳 <b>Docker</b>\n{pre(d['text'])}", K([[B("🔄", "docker"), B("⬅️ Menyu", "menu"), B("❌ Yopish", "x")]]))


# ───────── qayta yuklash / yopish ─────────
@r.callback_query(F.data == "reboot")
async def cb_reboot_ask(c: CallbackQuery):
    await edit(c.message, "♻️ <b>Server qayta yuklansinmi?</b>\nBarcha ilovalar bir necha daqiqaga to'xtaydi.",
               K([[B("✅ Ha, qayta yuklash", "reboot_yes"), B("❌ Bekor", "menu")]]))


@r.callback_query(F.data == "reboot_yes")
async def cb_reboot(c: CallbackQuery):
    await edit(c.message, "♻️ Server qayta yuklanmoqda…\nBir necha daqiqadan keyin bot o'zi xabar beradi.")
    await core.reboot()


@r.callback_query(F.data == "x")
async def cb_close(c: CallbackQuery):
    await clear_states(c.from_user.id)
    try: await c.message.delete()
    except Exception: pass


async def main():
    # Bitta nusxa: ikkinchi nusxa bo'lsa «Conflict» chiqmasligi uchun eskisi to'xtatiladi (avval — hech narsa ishga tushmasidan)
    taken = await asyncio.to_thread(instance.acquire, os.environ["BOT_TOKEN"])
    bot = Bot(os.environ["BOT_TOKEN"], default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    try:
        await bot.delete_my_commands()      # «/» menyusida eski buyruqlar ko'rinmasin — hammasi tugmalarda
    except Exception:
        pass
    global WEBAPP_URL
    runner = None
    if WEBAPP_URL != "off":
        runner = await webapp.serve()
        if not WEBAPP_URL:
            WEBAPP_URL = await webapp.tunnel(webapp.PORT)
            print("Mini App manzili:", WEBAPP_URL or "cloudflared topilmadi")
            if not WEBAPP_URL:
                for a in ADMINS:
                    try: await bot.send_message(a, "⚠️ cloudflared yuklanmadi (internet/GitHub?). Qo'lda: <code>sudo curl -fL -o /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 &amp;&amp; sudo chmod +x /usr/local/bin/cloudflared</code> (apt'da yo'q).")
                    except Exception: pass
        if WEBAPP_URL.startswith("https"):
            try:
                await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Panel", web_app=WebAppInfo(url=WEBAPP_URL)))
            except Exception as e:
                print("menu button:", e)
    if WEBAPP_URL.startswith("https"):
        for a in ADMINS:
            try: await bot.send_message(a, f"🖥 <b>Panel manzili:</b>\n{esc(WEBAPP_URL)}\n\n<i>Telegram ichida «Panel» tugmasi orqali oching.</i>")
            except Exception: pass
    dp.include_routers(bot_userbot.router, bot_ai.router, bot_apps.router, bot_files.router, bot_sys.router, r)  # userbot BIRINCHI (matn kutish holati)
    dp.update.outer_middleware(AdminOnly())
    bg = [asyncio.create_task(core.sampler()), asyncio.create_task(alert_loop(bot)), asyncio.create_task(janitor())]
    for a in ADMINS:
        try:
            up = time.time() - psutil.boot_time()
            await bot.send_message(a, f"🟢 Bot ishga tushdi · server {int(up // 3600)}s {int(up % 3600 // 60)}d ishlayapti",
                                   reply_markup=main_kb())
        except Exception:
            pass
    async def _ub_event(uid, text):
        await bot.send_message(uid, text)
    userbot_core.on_event = _ub_event
    try:
        userbot_docs.sync_all()              # modul docs kod/modullarga moslab yangilanadi (ZIP yangilanishdan keyin ham)
    except Exception as ex:
        print("docs yangilanmadi:", ex)
    bg.append(asyncio.create_task(userbot_core.supervise()))   # userbotlarni ko'taradi va tirik ushlaydi (restart/yangilanishdan keyin ham)
    if taken:
        for a in ADMINS:
            try: await bot.send_message(a, f"⚠️ Bot ikki nusxada ishlayotgan edi (Conflict xatosi sababi shu). Eski nusxa to'xtatildi: {esc(taken)}")
            except Exception: pass
    try:
        await dp.start_polling(bot)
    finally:
        await userbot_core.shutdown()        # bayroqlarga tegmaydi — yangi jarayon userbotlarni davom ettiradi
        webapp.stop_tunnel()
        for t in bg: t.cancel()
        if runner: await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

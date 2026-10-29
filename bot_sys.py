"""Bot: jarayonlar, portlar, xizmatlar — core yadrosi ustida."""
import asyncio, os, re

from aiogram import F, Router
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

import core
from common import B, K, SVC_RE, edit, esc, pre

router = Router()
TERM: set[int] = set()      # terminal rejimidagi adminlar
SVCQ: set[int] = set()      # xizmat nomini kutayotgan adminlar


# ───────── jarayonlar ─────────
def render(sort: str):
    s = core.status()
    rows = core.procs_list(sort, 12)
    lines = [f"{'PID':>6} {'USER':<8} {'CPU%':>5} {'MEM%':>5} {'RSS':>6}  NAME"]
    for p in rows:
        lines.append(f"{p['pid']:>6} {p['user'][:8]:<8} {p['cpu']:5.1f} {p['mem']:5.1f} {p['rss'] / 1048576:5.0f}M  {p['name'][:18]}")
    text = (f"🔥 <b>Jarayonlar</b> — jami {s['procs']}, CPU {s['cpu']:.0f}%\n"
            f"Saralash: <b>{'CPU' if sort == 'cpu' else 'RAM'}</b>\n<pre>{esc(chr(10).join(lines))}</pre>"
            "To'xtatish uchun tanlang 👇")
    kb, row = [], []
    for p in rows[:8]:
        row.append(B(f"❌ {p['name'][:12]} {p['pid']}", f"pk:{p['pid']}"))
        if len(row) == 2:
            kb.append(row); row = []
    if row: kb.append(row)
    kb.append([B("CPU ⇅", "pr:cpu"), B("RAM ⇅", "pr:mem"), B("🔄", f"pr:{sort}")])
    kb.append([B("🌐 Portlar", "ports"), B("⬅️ Menyu", "menu"), B("❌ Yopish", "x")])
    return text, K(kb)


@router.callback_query(F.data.startswith("pr:"))
async def cb_pr(c: CallbackQuery):
    sort = c.data[3:] if c.data[3:] in ("cpu", "mem") else "cpu"
    text, kb = render(sort)
    await edit(c.message, text, reply_markup=kb)


@router.callback_query(F.data.startswith("pk:"))
async def cb_pk(c: CallbackQuery):
    pid = int(c.data[3:])
    back = K([[B("⬅️ Ro'yxat", "pr:cpu")]])
    d = await asyncio.to_thread(core.proc_detail, pid)
    if not d:
        return await edit(c.message, "Bu jarayon allaqachon yo'q.", reply_markup=back)
    if d["risky"] or pid == 1:
        return await edit(c.message, f"⛔ {esc(d['name'])} ni to'xtatish xavfli (serverga kira olmay qolishingiz mumkin).",
                          reply_markup=back)
    await edit(c.message,
               f"⚠️ <b>{esc(d['name'])}</b> (harakat <code>{pid}</code>) to'xtatilsinmi?\n"
               f"Egasi: {esc(d['user'])} • RAM {d['rss'] / 1048576:.0f}MB\n<code>{esc(d['cmd'])}</code>\n\n"
               "ℹ️ Agar bu systemd xizmati bo'lsa, u o'zi qayta ishga tushishi mumkin — xizmatni "
               "«Xizmatlar» yoki «Ilovalar» orqali to'xtating.",
               reply_markup=K([[B("🛑 To'xtatish", f"pks:{pid}:15"), B("💀 Majburan", f"pks:{pid}:9")],
                               [B("❌ Bekor", "pr:cpu")]]))


@router.callback_query(F.data.startswith("pks:"))
async def cb_pks(c: CallbackQuery):
    _, pid, sig = c.data.split(":")
    pid, sig = int(pid), int(sig)
    back = K([[B("⬅️ Ro'yxat", "pr:cpu")]])
    err = await asyncio.to_thread(core.proc_kill, pid, sig)
    if err:
        return await edit(c.message, f"⛔ {esc(err)}", reply_markup=back)
    await asyncio.sleep(1)
    d = await asyncio.to_thread(core.proc_detail, pid)
    await edit(c.message, f"{pid}: {'hali ishlayapti (kuting yoki «Majburan»)' if d else 'to‘xtadi ✅'}",
               reply_markup=back)


# ───────── portlar ─────────
@router.callback_query(F.data == "ports")
async def cb_ports(c: CallbackQuery):
    try:
        rows = await asyncio.to_thread(core.ports)
        note = ""
    except Exception as e:
        rows, note = [], f"Ruxsat yo'q: {e}"
    lines = [f"{'PORT':>6} {'MANZIL':<15} {'PID':>6}  JARAYON"]
    for r in rows[:45]:
        lines.append(f"{r['port']:>6} {r['ip'][:15]:<15} {r['pid'] or '-':>6}  {r['name'][:20]}")
    await edit(c.message, f"🌐 <b>Ochiq portlar</b> ({len(rows)})\n{pre(chr(10).join(lines))}{note}",
               reply_markup=K([[B("🔄", "ports"), B("🔥 Jarayonlar", "pr:cpu")],
                               [B("⬅️ Menyu", "menu"), B("❌ Yopish", "x")]]))


# ───────── xizmatlar ─────────
@router.callback_query(F.data == "svcs")
async def cb_svcs(c: CallbackQuery):
    names = [x["name"] for x in await core.services()]
    kb, row = [], []
    for n in names[:40]:
        row.append(B(f"🟢 {n[:22]}", f"sc:{n}"))
        if len(row) == 2:
            kb.append(row); row = []
    if row: kb.append(row)
    kb.append([B("🔎 Boshqa xizmat", "svq")])
    kb.append([B("🔄", "svcs"), B("⬅️ Menyu", "menu"), B("❌ Yopish", "x")])
    await edit(c.message, f"⚙️ <b>Ishlayotgan xizmatlar</b> ({len(names)})\nTo'xtab turgan xizmat kerakmi? «🔎 Boshqa xizmat» ni bosing.",
               reply_markup=K(kb))


async def svc_card(msg: Message, n: str, note: str = ""):
    if not SVC_RE.match(n): return
    d = await core.service_info(n)
    body = f"MainPID={d['pid']}  NRestarts={d['restarts']}\nActiveEnter={d['since']}"
    await edit(msg, f"⚙️ <b>{esc(n)}</b> — {esc(d['state'])}\n{pre(body, 600)}{note}",
               reply_markup=K([[B("▶️ Start", f"sa:start:{n}"), B("⏹ Stop", f"sa:stop:{n}"), B("🔄 Restart", f"sa:restart:{n}")],
                               [B("📜 Log", f"sl:{n}"), B("✅ Enable", f"sa:enable:{n}"), B("🚫 Disable", f"sa:disable:{n}")],
                               [B("⬅️ Xizmatlar", "svcs"), B("❌ Yopish", "x")]]))


@router.callback_query(F.data.startswith("sc:"))
async def cb_sc(c: CallbackQuery):
    await svc_card(c.message, c.data[3:])


@router.callback_query(F.data.startswith("sa:"))
async def cb_sa(c: CallbackQuery):
    _, a, n = c.data.split(":", 2)
    if a not in {"start", "stop", "restart", "enable", "disable"} or not SVC_RE.match(n):
        return
    r = await core.service_act(n, a)
    if "blocked" in r:
        return await svc_card(c.message, n, f"\n⛔ {esc(r['blocked'])}")
    await svc_card(c.message, n, f"\n{'✅' if r['done'] else '⚠️'} {a}" + (f"\n{pre(r['out'], 400)}" if not r["done"] else ""))


@router.callback_query(F.data.startswith("sl:"))
async def cb_sl(c: CallbackQuery):
    n = c.data[3:]
    if SVC_RE.match(n):
        await c.message.answer(f"📜 <b>{esc(n)}</b>\n{pre(await core.journal(n, 50))}")


# ───────── boshqa xizmat (nom bo'yicha) ─────────
@router.callback_query(F.data == "svq")
async def cb_svq(c: CallbackQuery):
    SVCQ.add(c.from_user.id)
    await edit(c.message, "🔎 <b>Xizmat nomini yozing</b>\nMasalan: <code>nginx</code>, <code>docker</code>, <code>ssh</code>",
               K([[B("⬅️ Xizmatlar", "svcs")]]))


class InSvcQ(BaseFilter):
    async def __call__(self, m: Message) -> bool:
        return bool(m.text) and m.from_user.id in SVCQ and not m.text.startswith("/")


@router.message(InSvcQ())
async def on_svc_name(m: Message):
    n = m.text.strip().removesuffix(".service")
    if not SVC_RE.match(n):
        return await m.answer("❌ Nom yaroqsiz. Qayta yozing:", reply_markup=K([[B("⬅️ Xizmatlar", "svcs")]]))
    SVCQ.discard(m.from_user.id)
    await svc_card(await m.answer("⏳"), n)


# ───────── terminal ─────────
QUICK = [("⏱ uptime", "uptime"), ("💾 df -h", "df -h"), ("🧠 free -h", "free -h"),
         ("🐳 docker ps", "docker ps"), ("⚠️ Xatolar", "journalctl -p err -n 30 --no-pager -o cat"),
         ("🔥 Top RAM", "ps aux --sort=-%mem | head -8")]
START_RE = re.compile(r"^/start(@\w+)?(\s|$)")


def term_kb():
    rows = [[B(t, f"tq:{i}") for i, (t, _) in enumerate(QUICK[j:j + 3], j)] for j in (0, 3)]
    rows.append([B("❌ Terminaldan chiqish", "term:x")])
    return K(rows)


async def run_term(m: Message, cmd: str):
    wait = await m.answer(f"⏳ <code>{esc(cmd[:150])}</code>")
    try:
        res = await core.shell(cmd, 60)
    except Exception as e:
        return await edit(wait, f"❌ {esc(str(e))}", term_kb())
    await edit(wait, f"<code>$ {esc(cmd[:150])}</code>  ·  exit <b>{res['code']}</b>\n{pre(res['out'])}", term_kb())


@router.callback_query(F.data == "term")
async def cb_term(c: CallbackQuery):
    TERM.add(c.from_user.id)
    await edit(c.message, "🖥 <b>Terminal</b>\nBuyruqni oddiy xabar qilib yozing — natija shu yerga keladi, "
                          "yoki pastdagi tayyor tugmalardan foydalaning.\n\n"
                          "<i>root huquqi bilan bajariladi. Har bir buyruq alohida ishlaydi (cd saqlanmaydi), 60s limit.</i>",
               term_kb())


@router.callback_query(F.data == "term:x")
async def cb_term_exit(c: CallbackQuery):
    TERM.discard(c.from_user.id)
    await edit(c.message, "🖥 Terminal yopildi.", K([[B("⬅️ Menyu", "menu")]]))


@router.callback_query(F.data.startswith("tq:"))
async def cb_term_quick(c: CallbackQuery):
    i = c.data[3:]
    if i.isdigit() and int(i) < len(QUICK):
        TERM.add(c.from_user.id)
        await run_term(c.message, QUICK[int(i)][1])


class InTerm(BaseFilter):
    async def __call__(self, m: Message) -> bool:
        return bool(m.text) and m.from_user.id in TERM and not START_RE.match(m.text)


@router.message(InTerm())
async def on_term(m: Message):
    await run_term(m, m.text.strip())

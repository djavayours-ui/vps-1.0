"""Premium (custom) emoji bilan xabar yuborish/tahrirlash uchun Telethon parse_mode.

Oddiy Telethon HTML parseri `<tg-emoji>` ni bilmaydi. Bu parser oddiy HTML (<b>, <i>, <code>, <a href>, <pre>...) ni Telethon'ning
o'zi bilan tahlil qiladi, `<tg-emoji emoji-id="ID">⚡️</tg-emoji>` ni esa MessageEntityCustomEmoji ga aylantiradi.
Ichidagi oddiy emoji (fallback) — premium emoji ko'rinmaydigan joyda (Premium bo'lmagan hisob/klient) shu ko'rinadi.
Modulda: `await e.edit(f'{ctx.emoji(ID, "⚡️")} Ping: <b>{ms}</b> ms', parse_mode=ctx.html)`.
"""
import re

TAG_RE = re.compile(r'<tg-emoji\s+emoji-id\s*=\s*["\']?(\d{5,25})["\']?\s*>(.*?)</tg-emoji>', re.S | re.I)
_BACK_RE = re.compile(r'<a href="emoji/(\d+)">(.*?)</a>', re.S)


def _tl():
    from telethon.extensions import html as tl_html
    from telethon.tl import types
    return tl_html, types


class PremiumHTML:
    """Telethon parse_mode obyekti (parse/unparse): HTML + <tg-emoji emoji-id="..">fallback</tg-emoji>."""

    @staticmethod
    def parse(text: str):
        tl_html, types = _tl()
        text = TAG_RE.sub(lambda m: f'<a href="emoji/{m.group(1)}">{m.group(2) or "⭐"}</a>', text or "")
        out, ents = tl_html.parse(text)
        ents = list(ents)
        for i, en in enumerate(ents):
            url = getattr(en, "url", None)
            if isinstance(en, types.MessageEntityTextUrl) and isinstance(url, str) and re.fullmatch(r"emoji/\d{5,25}", url):
                ents[i] = types.MessageEntityCustomEmoji(en.offset, en.length, int(url[6:]))
        return out, ents

    @staticmethod
    def unparse(text: str, entities):
        tl_html, types = _tl()
        ents = [types.MessageEntityTextUrl(e.offset, e.length, f"emoji/{e.document_id}")
                if isinstance(e, types.MessageEntityCustomEmoji) else e for e in (entities or [])]
        return _BACK_RE.sub(lambda m: f'<tg-emoji emoji-id="{m.group(1)}">{m.group(2)}</tg-emoji>', tl_html.unparse(text, ents))


def tag(emoji_id, fallback: str = "⭐") -> str:
    """`<tg-emoji emoji-id="ID">fallback</tg-emoji>` — fallback HTML'dan tozalanadi."""
    import html
    eid = int(emoji_id)
    if eid <= 0:
        raise ValueError("emoji_id musbat butun son bo'lishi kerak")
    return f'<tg-emoji emoji-id="{eid}">{html.escape(str(fallback) or "⭐", quote=False)}</tg-emoji>'


def from_entities(text: str, entities) -> str:
    """Bot (aiogram) xabaridagi custom_emoji entity'larini `<tg-emoji ...>fallback</tg-emoji>` ga aylantiradi (AI ga berish uchun).
    Offset/length UTF-16 birligida. Boshqa entity'lar o'zgarmaydi (oddiy matn qoladi)."""
    ce = [e for e in (entities or []) if getattr(e, "type", "") == "custom_emoji" and getattr(e, "custom_emoji_id", None)]
    if not ce:
        return text
    b, pos, out = text.encode("utf-16-le"), 0, []
    for e in sorted(ce, key=lambda x: x.offset):
        s, t = e.offset * 2, (e.offset + e.length) * 2
        if s < pos or t > len(b):
            continue
        out.append(b[pos:s].decode("utf-16-le", "replace"))
        out.append(tag(e.custom_emoji_id, b[s:t].decode("utf-16-le", "replace") or "⭐"))
        pos = t
    out.append(b[pos:].decode("utf-16-le", "replace"))
    return "".join(out)

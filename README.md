# VPS Manager v5 — Telegram Mini App

Botning **barcha** bo'limlari endi bitta yadro (`core` / `appctl` / `filesvc`) ustida ishlaydi.
Bot ham, Mini App ham **bir xil** funksiyalarni chaqiradi — mantiq ikki marta yozilmagan.

## Tuzilma

```
config.py      sozlamalar + sof yordamchilar (aiogram'siz)
core.py        monitoring, jarayonlar, portlar, xizmatlar, docker, disk, terminal
appctl.py      ZIP deploy, update (xatoda eski kod o'zi tiklanadi), .env kalitlar, AI tuzatish
filesvc.py     fayl menejeri yadrosi
jobs.py        fon vazifalari + progress (bot ham, web ham o'qiydi)
webapp.py      aiohttp API + statik panel + cloudflared tunnel
webapp/        index.html, styles.css, app.js  (premium gray glassmorphism)
bot.py         bot kirish nuqtasi, monitoring, alert
bot_apps.py    bot: ilovalar, ZIP, kalitlar, AI
bot_files.py   bot: fayl menejeri
bot_sys.py     bot: jarayonlar, portlar, xizmatlar
instance.py    bitta nusxa himoyasi (Telegram «Conflict» xatosini oldini oladi)
selfupdate.py  bot o'zini ZIP bilan yangilaganda: tashqi restart + xato bo'lsa avtomatik rollback
userbot_core.py  userbot yadrosi (Telethon): sessiya, supervisor (avto-davom), buyruqlar, profil soati/shriftlar, modul yuklagich
userbot_mods.py  modul .py faylini xavfsiz tahlil qilish (ast) + config qiymatlarini tekshirish + chegaralar/limitlar
userbot_emoji.py  premium (custom) emoji uchun Telethon parse_mode (ctx.html)
userbot_libs.py  modul kutubxonalarini avtomatik o'rnatish (pip) va modul o'chganda o'chirish
userbot_ai.py    AI (DeepSeek) bilan modul yaratish mantiqi: suhbat, docs bir marta, kodni tekshirish va avto-tuzatish
bot_ai.py        bot: 🧩 Modullar → 🤖 AI bilan yaratish (kalit, docs ✅/❌, model, suhbat)
userbot_docs.py  modul docs generatori (koddan avtomatik) → docs/MODULES.md va USERBOT_DIR/docs/<id>/MODULES.md
docs/MODULES.md  modul yozish qo'llanmasi (AVTOMATIK yaratiladi — qo'lda tahrirlamang)
modules_example/ namuna modullar (docsga o'zi kiradi)
bot_userbot.py   bot: 🤖 Userbot bo'limi (o'rnatish ustasi + boshqaruv)
```

## O'rnatish

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip curl
# cloudflared apt'da yo'q — binar fayl yuklanadi:
sudo curl -fL -o /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$(dpkg --print-architecture)
sudo chmod +x /usr/local/bin/cloudflared
unzip vpsbot-v5-webapp.zip -d /opt/vpsbot && cd /opt/vpsbot
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

cp .env.example .env && nano .env     # BOT_TOKEN, ADMIN_IDS
sudo .venv/bin/python bot.py
```

`WEBAPP_URL` **bo'sh** qoldirilsa bot o'zi cloudflared bilan bepul HTTPS manzil oladi va
shu manzilni «Panel» tugmasiga qo'yadi (trycloudflare manzili har ishga tushishda o'zgaradi).

### Doimiy domen bilan (tavsiya etiladi)

```bash
# 1) systemd xizmati
sudo tee /etc/systemd/system/vpsbot.service >/dev/null <<'EOF'
[Unit]
Description=VPS Manager bot + panel
After=network.target

[Service]
WorkingDirectory=/opt/vpsbot
Environment=WEBAPP_URL=https://panel.example.com
ExecStart=/opt/vpsbot/.venv/bin/python bot.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now vpsbot

# 2) cloudflared nomlangan tunnel
cloudflared tunnel login
cloudflared tunnel create vpspanel
sudo mkdir -p /etc/cloudflared
sudo tee /etc/cloudflared/config.yml >/dev/null <<'EOF'
tunnel: <TUNNEL_UUID>
credentials-file: /root/.cloudflared/<TUNNEL_UUID>.json
ingress:
  - hostname: panel.example.com
    service: http://127.0.0.1:8080
  - service: http_status:404
EOF
cloudflared tunnel route dns vpspanel panel.example.com
sudo cloudflared service install && sudo systemctl enable --now cloudflared
```

### Telegram menyu tugmasi (BotFather)

1. @BotFather → `/mybots` → botni tanlang
2. **Bot Settings → Menu Button → Configure menu button**
3. Matn: `Panel`
4. URL: `https://panel.example.com` (yoki `WEBAPP_URL`)

Yoki kod o'zi qiladi: `WEBAPP_URL` berilgan bo'lsa `set_chat_menu_button` chaqiriladi.

## 🤖 Userbot (v2.0)

Menyu → **🤖 Userbot** → **📥 O'rnatish**. Bot ketma-ket so'raydi: **API ID → API HASH → telefon → kod → (2FA parol)** yoki **📷 QR bilan kirish**.
API ID/HASH: https://my.telegram.org → *API development tools*. Kodni **nuqta bilan** yuboring: `123.45`. Yuborgan xabarlaringiz chatdan o'chiriladi.

### Avto-davom (restart / ZIP yangilash / reboot)
- Sessiya va barcha sozlamalar `USERBOT_DIR` (`/var/lib/vpsbot-userbot/<id>.json`, `chmod 600`, `.bak` nusxa bilan) da — loyiha papkasidan **tashqarida**, ZIP yangilash uni o'chirmaydi.
- Bot qayta ishga tushganda **supervisor** userbotni o'zi ko'taradi va **to'xtagan joyidan** davom ettiradi: profil soati (shrift/joy/shablon/zona), AFK (kimga javob berilgani ham), qaydlar.
- Faqat **⏹ Stop** bosilsa userbot o'chiq qoladi (restartdan keyin ham). **▶️ Start** — yana avto-davom.
- Tarmoq uzilsa — qayta ulanadi; ulana olmasa — oraliqni oshirib urinadi va adminga xabar beradi. Sessiya Telegram tomonidan bekor qilinsa — xabar beradi (qayta o'rnatish kerak).
- Qayta o'rnatishda shrift/shablon/zona/qaydlar saqlanadi.

### Profil soati
Bot: 🤖 Userbot → 🕒 Profil soati (shrift, joyi, shablon, zona tugmalari). Yoki chatda: `.clock on|off`, `.clock fonts`, `.clock font №`, `.clock fmt №|shablon`, `.clock where last|first|bio`, `.clock tz Asia/Tashkent`.
14 shrift: oddiy, qalin, qo'sh chiziq, sans, sans qalin, mono, keng, doira, to'q doira, dingbat, yuqori, quyi, keycap, segment.
Shablon: `{t}` vaqt, `{e}` soatga mos 🕒 emoji, `{d}` sana. Joyi: familiya / ism / bio. O'chirilsa asl nom/bio tiklanadi.

### 🧩 Modullar (.py)
Bot: 🤖 Userbot → 🧩 Modullar → 📥 Modul qo'shish → `.py` yuboring (yoki chatda faylga reply: `.mod add`).
Fayl **ishga tushirilmasdan** tekshiriladi: nom, tavsif, buyruqlar, config, importlar (⚠️ `os`, `subprocess`, `socket`… alohida ko'rsatiladi) — tasdiqlasangiz o'rnatiladi.
⚠️ Modul bot jarayonida **to'liq huquq** bilan ishlaydi — faqat ishonchli kodni o'rnating.

Boshqaruv: `.mod` (ro'yxat) · `.mod info|on|off|reload|del nom` · `.config` · `.config modul` · `.config modul kalit qiymat` (`-r` — standart qiymat).
Bot tugmalarida ham: yoqish/o'chirish, ♻️ qayta yuklash (yangi .py yuborib faylni almashtirish), 📥 yuklab olish (.py), ✏️ AI bilan o'zgartirish, config (bool — bir bosishda, qolganlari — qiymat yozish), o'chirish.
📚 **Kutubxonalar avtomatik:** modul `REQUIREMENTS = ["pillow"]` yozsa yoki kodida o'rnatilmagan kutubxonani import qilsa (AI yaratgan modullar ham), tasdiqlagach bot uni venv'ga o'zi o'rnatadi; modul o'chirilsa aynan u o'rnatgan kutubxonalar ham o'chadi (boshqa modul ishlatayotgani qoladi). `.mod libs` · `.mod libs fix nom`.
Modullar `USERBOT_DIR/modules/<id>/` da — ZIP yangilash o'chirmaydi; restartdan keyin yoqilganlari o'zi yuklanadi, config va `ctx.data` saqlanadi.

📖 **To'liq qo'llanma: [`docs/MODULES.md`](docs/MODULES.md)** — bot: 🧩 Modullar → 📖 Docs, chatda: `.docs` (fayl «Saqlangan»ga) yoki `.docs modul`.
Docs **koddan avtomatik yasaladi**: modul qo'shilsa/o'chirilsa, config yoki holat o'zgarsa, bot qayta ishga tushsa (ZIP yangilashdan keyin ham) yangilanadi.
Qo'lda: `python userbot_docs.py` · tekshirish: `python userbot_docs.py --check`.
Yangi hook/buyruq qo'shsangiz: hook → `userbot_mods.HOOK_DOC`, o'rnatilgan buyruq → `userbot_mods.RESERVED` + `HELP` (docs ogohlantiradi).

### 🤖 AI bilan modul yaratish (DeepSeek)
Bot: 🧩 Modullar → **🤖 AI bilan yaratish**.
1. **🔑 API kalit** — DeepSeek kalitini (platform.deepseek.com → API keys) Telegramda yuborasiz. Xabar chatdan o'chiriladi, kalit tekshiriladi va userbot sozlamasida (`chmod 600`) saqlanadi. `🗑` — o'chirish.
2. **✍️ Modul yaratish** — nima kerakligini oddiy tilda yozasiz. AI modul yozadi; bot kodni **ishga tushirmasdan** tekshiradi (xato bo'lsa AI ga qaytarib 2 martagacha o'zi tuzattiradi), `.py` faylni va tahlilni (buyruqlar, config, importlar, ⚠️ xavfli importlar) ko'rsatadi.
3. **✅ O'rnatish va yoqish** (oddiy tasdiq oqimi) yoki **✏️ O'zgartirish** — suhbat saqlanadi, AI oldingi modulni eslab turadi.
- **📖 Docs yuborish ✅/❌** — ✅ bo'lsa modul yozish qo'llanmasi AI ga suhbatda **faqat bir marta** (system xabarga) qo'shiladi va tarixda qoladi, keyingi so'rovlarda qayta yuborilmaydi; ❌ bo'lsa umuman yuborilmaydi. Docs o'rnatilgan modullaringiz buyruqlarini ham o'z ichiga oladi (to'qnashmaslik uchun).
- **🧠 Model**: `deepseek-chat` (tez) / `deepseek-reasoner` (chuqur, sekin). **🧹 Yangi suhbat** — tarixni (docs bilan birga) tozalaydi.
- 🖼 Rasm + izoh birga yuboriladi (modul yaratish va ✏️ O'zgartirish); rasmli so'rov `DEEPSEEK_VISION_MODEL` (standart `deepseek-flash`) modelida bajariladi.
- 💎 AI ga premium emoji yozsangiz, modulda aynan o'sha emoji ishlatiladi (`ctx.html` + `<tg-emoji emoji-id="..">`; userbot hisobi Premium bo'lishi kerak).
- Suhbat xotirada saqlanadi (6 soat yoki bot restartigacha). `DEEPSEEK_BASE` (ixtiyoriy) — API manzilini almashtirish (proksi uchun).
⚠️ AI yozgan kod ham to'liq huquq bilan ishlaydi — o'rnatishdan oldin faylni ko'zdan kechiring.

Modul yozish (namuna: `modules_example/example.py`):
```python
NAME = "example"                  # majburiy (a-z, 0-9, _)
DESCRIPTION = "Modul tavsifi"     # majburiy
VERSION = "1.0"; AUTHOR = "Ism"   # ixtiyoriy
CONFIG = {                        # .config bilan boshqariladi; tur defaultdan aniqlanadi
    "greeting": {"default": "Salom", "desc": "Matn"},
    "repeat": {"default": 1, "min": 1, "max": 5},
    "style": {"default": "a", "choices": ["a", "b"]},
    "emoji": (True, "Qisqa shakl: (default, tavsif)"),
}
COMMANDS = {"hello": {"desc": "Salom", "usage": ".hello [ism]"}}

async def cmd_hello(e, args, ctx):          # har bir buyruq: cmd_<nom>(e, args, ctx)
    await e.edit(f"{ctx.cfg['greeting']}, {args}!", parse_mode=None)
# ixtiyoriy: on_load(ctx) · on_unload(ctx) · on_message(e, ctx) (kiruvchi xabarlar) · on_config(ctx, key, value)
```
`ctx`: `client` (Telethon), `me`, `cfg[kalit]` (joriy qiymat), `data` + `save()` (doimiy xotira, ≤64 KB), `on(event)` (handler — o'chirilganda avtomatik olib tashlanadi), `spawn(coro)` (fon vazifa), `log()`.
O'rnatilgan buyruq nomlarini (`.ping`, `.clock`…) ishlatib bo'lmaydi; ikki modul bir buyruqni bo'lisha olmaydi. Modul xatosi userbotni yiqitmaydi — holatda 🔴 ko'rinadi.

### Buyruqlar (o'zingiz istalgan chatda yozasiz)
`.help .ping .time .id .info .stats .vps .calc .type .del N .afk .unafk .remind 10m matn .note .notes .save .font .fonts .clock .mod .config .docs` + modul buyruqlari

## Yangilash va «Conflict» xatosi

- **Bitta nusxa**: bir xil `BOT_TOKEN` bilan ikkinchi nusxa ishga tushsa, yangisi eskisini to'xtatadi (systemd xizmati bo'lsa `systemctl stop`, aks holda SIGTERM → SIGKILL) va adminga xabar yuboradi. Qulf fayli: `/var/tmp/vpsbot-*.lock`.
- **Bot o'zini ZIP bilan yangilasa**: o'z xizmatini to'xtatmaydi (aks holda o'zini o'ldirardi). Fayllarni almashtirib, qayta ishga tushirish va tekshiruvni `systemd-run` orqali `selfupdate.py` ga topshiradi. Yangi kod qulasa — eski kod avtomatik tiklanadi va Telegramga xabar keladi.
- Bot o'zini `Stop` qila olmaydi va o'chira olmaydi (tugma «xavfsiz emas» deydi); `Restart` — 3 soniyadan keyin tashqaridan bajariladi.

## Bot interfeysi

Botda faqat `/start` buyrug'i bor (Telegram uni o'zi yuboradi) — qolgani **inline tugmalar**:
📊 Holat · 📦 Ilovalar · ⚙️ Xizmatlar (🔎 Boshqa xizmat) · 🐳 Docker · 💾 Disk · 🔥 Jarayonlar · 📁 Fayllar · 🌐 Portlar ·
🖥 Terminal · 🤖 Userbot · ♻️ Qayta yuklash. ZIP yuborilsa — avtomatik deploy yoki yangilash.

## Xavfsizlik

- `/api/*` faqat **Telegram initData** imzosi to'g'ri bo'lsa ishlaydi (HMAC-SHA256, `auth_date` 24 soat).
- Foydalanuvchi ID `ADMIN_IDS` da bo'lishi shart.
- Brauzerda `initData` bo'lmasa — panel **demo rejimda** ochiladi va API'ga umuman murojaat qilmaydi.
- Fayl amallari `DENY`/`guard()` bilan himoyalangan; o'chirilgan narsa 7 kun savatda turadi.
- `RISKY` xizmat/jarayonlarni (ssh, networking, ...) to'xtatib bo'lmaydi.

## API (qisqacha)

`GET /api/status · /api/apps · /api/procs · /api/ports · /api/services · /api/disk · /api/docker`
`POST /api/apps/deploy · /api/apps/{n}/{start|stop|restart} · /api/ai/{n}/fix`
`GET /api/jobs/{id}` — har qanday uzoq jarayonning bosqichlari/progressi
`GET|POST|DELETE /api/apps/{n}/env` — .env kalitlari
`GET /api/files/{roots,list,stat,read,download,tail,resolve} · POST /api/files/{upload,write,mkdir,rename,remove,paste,restore}`

## Demo

`vps-panel-demo.html` — bitta fayl, internet kerak emas: ochsangiz barcha ekranlar namuna ma'lumot bilan ishlaydi.

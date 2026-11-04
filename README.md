# 💎 UC Shop Bot (Telegram)

PUBG Mobile UC do'koni boti. UC ni bot emas, **admin qo'lda yuboradi** — bot faqat buyurtma va to'lovlarni qabul qiladi.
Barcha narsa admin paneldan tahrirlanadi. **UC soni va narxlari oldindan kiritilmagan** — admin o'zi qo'shadi.

## Imkoniyatlar
- 10 ta asosiy tugma: UC sotib olish, Hisobni to'ldirish, Hisobim, Buyurtmalarim, UC narxlari, Referal, Qo'llanmalar, Yordam, To'lovlarim, Top referallar
- To'lov: **Telegram Stars (avto)** + **karta orqali (qo'lda, chek bilan, admin tasdiqlaydi)**
- Rangli tugmalar (🟢 yashil / 🔵 ko'k / 🔴 qizil) va tugmalarga premium emoji
- Admin panel: UC paketlari, **Dizayn** (tugma matni/rangi/premium emoji), **Matnlar** (har bir xabar + rasm/video/dumaloq video),
  Majburiy obuna, Qo'llanmalar, Yordam bo'limi, Buyurtmalar, To'lovlar, Foydalanuvchilar (balans/ban), Xabar yuborish, Sozlamalar, Statistika, Adminlar
- Referal tizimi (bonus miqdorini admin belgilaydi — do'st birinchi marta hisobini to'ldirganda beriladi)

## Ishga tushirish
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # BOT_TOKEN va ADMIN_IDS ni to'ldiring
python main.py
```
Keyin botda `/admin` yozing.

## Birinchi sozlash (admin panelda)
1. **💎 UC paketlari** → UC soni va narxini qo'shing
2. **⚙️ Sozlamalar** → karta raqami, karta egasi, minimal summa, `1 Star = necha so'm`, referal bonusi, admin username
3. **✨ Premium emoji** (🎨 Dizayn → Premium emoji xaritasi) → emoji paket havolasini yuboring (`t.me/addemoji/...`) —
   bot barcha oddiy emojilarni (tugma va matnlarda) avtomatik premium emojiga almashtiradi
4. **📢 Majburiy obuna** → botni kanalga **admin** qiling, kanaldan xabar forward qiling

## Muhim eslatmalar
- Tugma ranglari (`style`) va tugma ikonkasi (`icon_custom_emoji_id`) yangi Bot API imkoniyati — Telegram ilovasi yangi bo'lishi kerak.
- Premium emoji ko'rinishi uchun **bot egasida Telegram Premium** bo'lishi kerak (yoki bot Fragment'da qo'shimcha username sotib olgan).
  Ishlamasa bot avtomatik oddiy emojiga qaytadi — xatolik chiqmaydi.
- Stars to'lovi uchun BotFather'da qo'shimcha sozlash kerak emas (valyuta `XTR`).
- Dumaloq video (video note) ga matn biriktirib bo'lmaydi — bot uni alohida yuboradi, matn keyingi xabarda keladi.

## GitHub Actions (24/7)
Repo → Settings → Secrets and variables → Actions ga `BOT_TOKEN` va `ADMIN_IDS` ni qo'shing,
so'ng Actions → Bot 24/7 → Run workflow. Bot har ~5.7 soatda o'zini qayta ishga tushiradi.
Jiddiy ishlatish uchun VPS (Docker yoki systemd) tavsiya etiladi.

## GitHub ga joylash
```bash
git init && git add . && git commit -m "UC shop bot"
git branch -M main
git remote add origin https://github.com/<login>/<repo>.git
git push -u origin main
```
`.env` va `data/` `.gitignore` da — tokeningiz GitHub ga chiqmaydi.

## Server (doimiy ishlashi uchun)
`systemd` yoki `screen/tmux` da `python main.py`. Ma'lumotlar `data/bot.db` (SQLite) da — zaxira nusxa oling.
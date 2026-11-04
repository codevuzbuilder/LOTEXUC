"""Standart tugma/matn/sozlamalar. UC soni va narxlari BU YERDA YO'Q — ularni faqat admin kiritadi."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BDef:
    text: str
    style: str | None  # green | blue | red | None
    title: str


@dataclass(frozen=True)
class TDef:
    title: str
    text: str
    vars: str = ""


BUTTONS: dict[str, BDef] = {
    # --- asosiy menyu (10 ta) ---
    "m_buy": BDef("🛒 UC sotib olish", "green", "Asosiy: UC sotib olish"),
    "m_topup": BDef("💰 Hisobni to'ldirish", "green", "Asosiy: Hisobni to'ldirish"),
    "m_profile": BDef("👤 Mening hisobim", "blue", "Asosiy: Hisobim"),
    "m_orders": BDef("📦 Buyurtmalarim", "blue", "Asosiy: Buyurtmalarim"),
    "m_prices": BDef("💎 UC narxlari", "blue", "Asosiy: UC narxlari"),
    "m_referral": BDef("🎁 Referal", "green", "Asosiy: Referal"),
    "m_guides": BDef("📚 Qo'llanmalar", "blue", "Asosiy: Qo'llanmalar"),
    "m_help": BDef("🆘 Yordam", "red", "Asosiy: Yordam"),
    "m_payments": BDef("🧾 To'lovlarim", "blue", "Asosiy: To'lovlarim"),
    "m_top": BDef("🏆 Top referallar", "blue", "Asosiy: Top referallar"),
    # --- boshqa tugmalar ---
    "b_back": BDef("⬅️ Orqaga", None, "Orqaga"),
    "b_home": BDef("🏠 Bosh menyu", "blue", "Bosh menyu"),
    "b_cancel": BDef("❌ Bekor qilish", "red", "Bekor qilish"),
    "b_confirm": BDef("✅ Tasdiqlash", "green", "Tasdiqlash"),
    "b_check_sub": BDef("✅ Tekshirish", "green", "Obunani tekshirish"),
    "b_channel": BDef("📢 {title}", "blue", "Kanal tugmasi ({title})"),
    "b_stars": BDef("⭐ Telegram Stars (avto)", "green", "To'lov: Stars"),
    "b_manual": BDef("💳 Karta orqali (qo'lda)", "blue", "To'lov: karta"),
    "b_support": BDef("👨‍💻 Admin bilan bog'lanish", "blue", "Admin bilan bog'lanish"),
    "b_pkg": BDef("💎 {uc} UC — {price}", "blue", "UC paketi ({uc}, {price})"),
    "b_doc": BDef("📄 {title}", "blue", "Qo'llanma/yordam elementi ({title})"),
}

TEXTS: dict[str, TDef] = {
    "t_start": TDef("🏠 /start xabari",
        "👋 <b>Assalomu alaykum, {name}!</b>\n\n🎮 PUBG Mobile <b>UC</b> do'koniga xush kelibsiz.\n\n"
        "💎 Qulay narxlar\n⚡️ Tez yetkazib berish\n🔒 Ishonchli to'lov\n\nKerakli bo'limni tanlang 👇",
        "{name} {id} {balance}"),
    "t_menu": TDef("🏠 Bosh menyu xabari", "🏠 <b>Bosh menyu</b>\n\nKerakli bo'limni tanlang 👇",
        "{name} {id} {balance}"),
    "t_buy": TDef("🛒 UC sotib olish",
        "🛒 <b>UC sotib olish</b>\n\n💰 Balansingiz: <b>{balance}</b>\n\nKerakli UC miqdorini tanlang 👇", "{balance}"),
    "t_buy_empty": TDef("😔 UC paketlari yo'q",
        "😔 Hozircha UC paketlari mavjud emas.\n\nIltimos, keyinroq qayta urinib ko'ring."),
    "t_shop_off": TDef("⏸ Xarid o'chirilgan", "⏸ Hozirda buyurtmalar qabul qilinmaydi. Keyinroq urinib ko'ring."),
    "t_ask_pid": TDef("🎮 PUBG ID so'rash",
        "🎮 <b>{uc} UC</b> — {price}\n\nPUBG Mobile <b>ID</b> raqamingizni yuboring (faqat raqamlar):", "{uc} {price}"),
    "t_bad_pid": TDef("❌ PUBG ID xato", "❌ ID noto'g'ri. Faqat raqamlardan iborat PUBG ID yuboring (5–15 ta raqam)."),
    "t_confirm": TDef("🧾 Buyurtmani tasdiqlash",
        "🧾 <b>Buyurtmani tasdiqlang</b>\n\n💎 UC: <b>{uc}</b>\n💵 Narxi: <b>{price}</b>\n"
        "🎮 PUBG ID: <code>{player_id}</code>\n\n💰 Balansingiz: <b>{balance}</b>\n\n"
        "To'g'ri bo'lsa «Tasdiqlash» tugmasini bosing.", "{uc} {price} {player_id} {balance}"),
    "t_no_balance": TDef("❌ Balans yetarli emas",
        "❌ <b>Balansingizda mablag' yetarli emas</b>\n\n💵 Kerak: <b>{price}</b>\n💰 Balans: <b>{balance}</b>\n"
        "➕ Yetishmaydi: <b>{lack}</b>\n\nAvval hisobingizni to'ldiring 👇", "{price} {balance} {lack}"),
    "t_order_ok": TDef("✅ Buyurtma qabul qilindi",
        "✅ <b>Buyurtma qabul qilindi!</b>\n\n🆔 Buyurtma: <b>№{order_id}</b>\n💎 UC: <b>{uc}</b>\n"
        "🎮 PUBG ID: <code>{player_id}</code>\n\n⏳ Admin UC ni tez orada yuboradi. Bajarilgach sizga xabar keladi.",
        "{order_id} {uc} {price} {player_id}"),
    "t_order_done": TDef("🎉 Buyurtma bajarildi",
        "🎉 <b>Buyurtma №{order_id} bajarildi!</b>\n\n💎 <b>{uc} UC</b> PUBG ID <code>{player_id}</code> ga yuborildi.\n\n"
        "Xaridingiz uchun rahmat! ❤️", "{order_id} {uc} {price} {player_id}"),
    "t_order_cancel": TDef("❌ Buyurtma bekor qilindi",
        "❌ <b>Buyurtma №{order_id} bekor qilindi.</b>\n\n💰 <b>{price}</b> balansingizga qaytarildi.\n"
        "Joriy balans: <b>{balance}</b>", "{order_id} {uc} {price} {balance}"),
    "t_prices": TDef("💎 UC narxlari", "💎 <b>UC narxlari</b>\n\n{list}", "{list}"),
    "t_topup": TDef("💰 Hisobni to'ldirish",
        "💰 <b>Hisobni to'ldirish</b>\n\nJoriy balans: <b>{balance}</b>\n\nTo'lov usulini tanlang 👇", "{balance}"),
    "t_topup_none": TDef("😔 To'lov usuli yo'q", "😔 Hozircha to'lov usullari sozlanmagan. Admin bilan bog'laning."),
    "t_ask_amount": TDef("💵 Summani so'rash",
        "💵 To'ldirmoqchi bo'lgan summangizni kiriting ({currency}).\n\n⬇️ Minimal: <b>{min}</b>", "{currency} {min}"),
    "t_bad_amount": TDef("❌ Summa xato",
        "❌ Summa noto'g'ri. Minimal summa: <b>{min}</b>. Faqat raqam yuboring.", "{min}"),
    "t_manual": TDef("💳 Karta orqali to'lov",
        "💳 <b>Karta orqali to'lov</b>\n\n💵 Summa: <b>{amount}</b>\n💳 Karta: <code>{card}</code>\n"
        "👤 Egasi: <b>{owner}</b>\n\n1️⃣ Yuqoridagi kartaga aynan shu summani o'tkazing\n"
        "2️⃣ To'lov <b>chekini (skrinshot)</b> shu yerga yuboring\n\n⏳ Admin tekshirib, balansingizni to'ldiradi.",
        "{amount} {card} {owner}"),
    "t_bad_check": TDef("❌ Chek xato", "❌ Iltimos, to'lov chekini <b>rasm</b> yoki fayl ko'rinishida yuboring."),
    "t_manual_sent": TDef("✅ So'rov yuborildi",
        "✅ <b>So'rovingiz adminga yuborildi!</b>\n\n🆔 So'rov: <b>№{pay_id}</b>\n💵 Summa: <b>{amount}</b>\n\n"
        "Tasdiqlangach balansingiz avtomatik to'ldiriladi.", "{pay_id} {amount}"),
    "t_pay_ok": TDef("✅ Hisob to'ldirildi",
        "✅ <b>Hisobingiz to'ldirildi!</b>\n\n➕ Qo'shildi: <b>{amount}</b>\n💰 Joriy balans: <b>{balance}</b>",
        "{amount} {balance}"),
    "t_pay_rejected": TDef("❌ To'lov rad etildi",
        "❌ <b>To'lov so'rovingiz №{pay_id} rad etildi.</b>\n\nMuammo bo'lsa, admin bilan bog'laning.", "{pay_id}"),
    "t_bal_adj": TDef("💰 Balans o'zgartirildi",
        "💰 <b>Balansingiz o'zgartirildi:</b> {delta}\nJoriy balans: <b>{balance}</b>", "{delta} {balance}"),
    "t_ref_bonus": TDef("🎁 Referal bonusi",
        "🎁 <b>Referal bonusi!</b>\n\nTaklif qilgan do'stingiz hisobini to'ldirdi. Sizga <b>{bonus}</b> berildi.\n"
        "💰 Balans: <b>{balance}</b>", "{bonus} {balance}"),
    "t_profile": TDef("👤 Mening hisobim",
        "👤 <b>Mening hisobim</b>\n\n🆔 ID: <code>{id}</code>\n💰 Balans: <b>{balance}</b>\n"
        "📦 Buyurtmalar: <b>{orders}</b>\n👥 Takliflar: <b>{refs}</b>", "{id} {balance} {orders} {refs}"),
    "t_orders": TDef("📦 Buyurtmalarim", "📦 <b>Buyurtmalarim</b> (oxirgi 10 ta)\n\n{list}", "{list}"),
    "t_orders_empty": TDef("📦 Buyurtma yo'q", "📦 Sizda hali buyurtmalar yo'q."),
    "t_payments": TDef("🧾 To'lovlarim", "🧾 <b>To'lovlarim</b> (oxirgi 10 ta)\n\n{list}", "{list}"),
    "t_payments_empty": TDef("🧾 To'lov yo'q", "🧾 Sizda hali to'lovlar yo'q."),
    "t_referral": TDef("🎁 Referal dasturi",
        "🎁 <b>Referal dasturi</b>\n\nDo'stlaringizni taklif qiling — ular hisobini birinchi marta to'ldirganda "
        "sizga bonus beriladi!\n\n🎁 Bonus: <b>{bonus}</b>\n👥 Takliflaringiz: <b>{refs}</b>\n"
        "💸 Jami daromad: <b>{earned}</b>\n\n🔗 Sizning havolangiz:\n<code>{link}</code>",
        "{bonus} {refs} {earned} {link}"),
    "t_top": TDef("🏆 Top referallar", "🏆 <b>Top referallar</b>\n\n{list}", "{list}"),
    "t_top_empty": TDef("🏆 Reyting bo'sh", "🏆 Hali reyting shakllanmagan."),
    "t_guides": TDef("📚 Qo'llanmalar ro'yxati", "📚 <b>Qo'llanmalar</b>\n\nKerakli qo'llanmani tanlang 👇"),
    "t_guides_empty": TDef("📚 Qo'llanma yo'q", "📚 Hozircha qo'llanmalar qo'shilmagan."),
    "t_help": TDef("🆘 Yordam bo'limi",
        "🆘 <b>Yordam</b>\n\nSavolingiz bo'lsa, quyidagi bo'limlardan foydalaning yoki admin bilan bog'laning 👇"),
    "t_sub": TDef("📢 Majburiy obuna",
        "📢 <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling</b>\n\n"
        "Obuna bo'lgach, «Tekshirish» tugmasini bosing 👇"),
    "t_banned": TDef("🚫 Ban xabari", "🚫 Siz botdan foydalana olmaysiz."),
}

# kalit: (nomi, turi, standart qiymat)
SETTINGS: dict[str, tuple[str, str, str | None]] = {
    "shop_enabled": ("🛒 Xarid (buyurtma qabul qilish)", "bool", "1"),
    "stars_enabled": ("⭐ Telegram Stars to'lovi", "bool", "1"),
    "stars_rate": ("⭐ 1 Star = necha so'm", "int", None),
    "manual_enabled": ("💳 Qo'lda (karta) to'lov", "bool", "1"),
    "card_number": ("💳 Karta raqami", "str", None),
    "card_owner": ("👤 Karta egasi", "str", None),
    "min_topup": ("⬇️ Minimal to'ldirish summasi", "int", None),
    "ref_bonus": ("🎁 Referal bonusi (so'm)", "int", "0"),
    "support": ("👨‍💻 Admin username", "str", None),
    "currency": ("💱 Valyuta nomi", "str", "so'm"),
    "sub_enabled": ("📢 Majburiy obuna", "bool", "1"),
}

SAMPLE = {
    "name": "Ali", "id": "123456789", "balance": "50 000 so'm", "uc": "60", "price": "12 000 so'm",
    "player_id": "5123456789", "order_id": "12", "amount": "20 000 so'm", "min": "5 000 so'm",
    "card": "8600 1234 5678 9012", "owner": "ALI VALIYEV", "pay_id": "7", "orders": "5", "refs": "3",
    "bonus": "1 000 so'm", "earned": "3 000 so'm", "link": "https://t.me/bot?start=ref_1",
    "list": "• 60 UC — 12 000 so'm\n• 325 UC — 60 000 so'm", "lack": "5 000 so'm", "currency": "so'm",
    "delta": "+10 000 so'm",
}

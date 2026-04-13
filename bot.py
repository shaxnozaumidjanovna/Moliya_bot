import os
import logging
import asyncio
from datetime import datetime, date
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import anthropic
from database import Database

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
WASTE_THRESHOLD = 20

CATEGORIES = {
    "daromad": "💰 Daromad",
    "investitsiya": "📈 Investitsiya",
    "bilim": "📚 Bilim",
    "ish": "💼 Ish",
    "oila": "👨‍👩‍👧 Oila",
    "oziq_ovqat": "🍽️ Oziq-ovqat",
    "transport": "🚗 Transport",
    "soglik": "🏥 Sogliq",
    "kiyim": "👗 Kiyim",
    "komshelik": "🏠 Kommunal",
    "korzinkaga": "🗑️ Keraksiz",
    "boshqa": "📦 Boshqa"
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()
ai_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Bugungi hisobot"), KeyboardButton(text="📅 Oylik hisobot")],
            [KeyboardButton(text="📆 Davr boyicha"), KeyboardButton(text="📈 Umumiy statistika")],
            [KeyboardButton(text="❓ Yordam")]
        ],
        resize_keyboard=True
    )
async def categorize_with_ai(text: str) -> dict:
    prompt = f"""Foydalanuvchi: "{text}"
JSON formatda qaytargin:
{{"type": "daromad" yoki "xarajat", "amount": raqam, "category": kategoriya, "description": tavsif, "is_waste": true/false}}
Kategoriyalar: daromad, investitsiya, bilim, ish, oila, oziq_ovqat, transport, soglik, kiyim, komshelik, korzinkaga, boshqa
Faqat JSON, boshqa hech narsa yozma.
Agar moliyaviy emas: {{"error": "topilmadi"}}"""
    response = ai_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    import json
    try:
        return json.loads(response.content[0].text.strip())
    except:
        return {"error": "xato"}
def format_report(data: dict, title: str) -> str:
    if not data:
        return f"📭 {title}\n\nMalumot topilmadi."
    total_income = data.get('total_income', 0)
    total_expense = data.get('total_expense', 0)
    balance = total_income - total_expense
    categories = data.get('categories', {})
    waste_amount = data.get('waste_amount', 0)
    report = f"📊 *{title}*\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    report += f"💰 *Daromad:* `{total_income:,.0f}` som\n"
    report += f"💸 *Xarajat:* `{total_expense:,.0f}` som\n"
    report += f"{'✅' if balance >= 0 else '❌'} *Balans:* `{balance:,.0f}` som\n\n"
    if categories:
        report += "📂 *Kategoriyalar:*\n"
        for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            if cat == 'daromad':
                continue
            if total_expense > 0:
                percent = (amount / total_expense) * 100
            else:
                percent = 0
            cat_name = CATEGORIES.get(cat, cat)
            report += f"{cat_name}: `{amount:,.0f}` som ({percent:.1f}%)\n"
    if waste_amount > 0 and total_expense > 0:
        waste_percent = (waste_amount / total_expense) * 100
        report += f"\n🗑️ Keraksiz: `{waste_amount:,.0f}` som ({waste_percent:.1f}%)\n"
        if waste_percent > WASTE_THRESHOLD:
            report += f"\n⚠️ *OGOHLANTIRISH:* Keraksiz xarajatlar {waste_percent:.0f}%!\n"
    return report
@dp.message(Command("start"))
async def cmd_start(message: Message):
    db.create_user(message.from_user.id)
    await message.answer(
        f"👋 Salom!\n\n"
        "💼 Men sizning moliya botingizman.\n\n"
        "📝 *Ishlatish:*\n"
        "• Daromad: `Maosh 3500000`\n"
        "• Xarajat: `Kafe 45000`\n"
        "• `Bilim kursi 200000`\n\n"
        "AI avtomatik kategoriyalaydi! 🤖",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

@dp.message(F.text == "📊 Bugungi hisobot")
async def today_report(message: Message):
    today = date.today().isoformat()
    data = db.get_report(message.from_user.id, today, today)
    report = format_report(data, f"Bugungi hisobot ({today})")
    await message.answer(report, parse_mode="Markdown")

@dp.message(F.text == "📅 Oylik hisobot")
async def monthly_report(message: Message):
    now = datetime.now()
    start = f"{now.year}-{now.month:02d}-01"
    end = date.today().isoformat()
    data = db.get_report(message.from_user.id, start, end)
    report = format_report(data, f"{now.strftime('%B %Y')} hisoboti")
    await message.answer(report, parse_mode="Markdown")

@dp.message(F.text == "📈 Umumiy statistika")
async def all_time_report(message: Message):
    data = db.get_report(message.from_user.id)
    report = format_report(data, "Umumiy statistika")
    await message.answer(report, parse_mode="Markdown")
@dp.message(F.text & ~F.text.startswith("/") & ~F.text.in_({
    "📊 Bugungi hisobot", "📅 Oylik hisobot", "📆 Davr boyicha",
    "📈 Umumiy statistika", "❓ Yordam"
}))
async def handle_transaction(message: Message):
    processing_msg = await message.answer("⏳ Tahlil qilinmoqda...")
    result = await categorize_with_ai(message.text)
    if "error" in result:
        await processing_msg.edit_text(
            "❓ Moliyaviy malumot topilmadi.\n\n"
            "Misol: `Maosh 3500000` yoki `Kafe 45000`"
        )
        return
    db.add_transaction(
        user_id=message.from_user.id,
        type=result['type'],
        amount=result['amount'],
        category=result['category'],
        description=result.get('description', message.text),
        is_waste=result.get('is_waste', False),
        date=date.today().isoformat()
    )
    cat_display = CATEGORIES.get(result['category'], result['category'])
    type_emoji = "💰" if result['type'] == 'daromad' else "💸"
    response = (
        f"✅ *Saqlandi!*\n\n"
        f"{type_emoji} *{'Daromad' if result['type'] == 'daromad' else 'Xarajat'}:* "
        f"`{result['amount']:,.0f}` som\n"
        f"📂 *Kategoriya:* {cat_display}\n"
        f"📝 {result.get('description', '')}"
    )
    if result.get('is_waste'):
        response += "\n\n🗑️ *Keraksiz xarajat!*"
    await processing_msg.edit_text(response, parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

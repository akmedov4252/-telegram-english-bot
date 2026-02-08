# ============================================
# TELEGRAM ENGLISH TESTING BOT - FINAL VERSION
# ============================================

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
)

from questions import UNIT_DATA, UNITS, UNIT_TITLES
from database import db

# ================= LOGGING =================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= CONFIG =================

BOT_TOKEN = "7723113091:AAFX7bZHW510lfMX-LFpaR6tcHf0E4q407E"
ADMIN_IDS = [678586766]

PASS_THRESHOLD = 60

# States
SELECTING_UNIT, GRAMMAR_TEST, VOCAB_TRAINING, VOCAB_TEST = range(4)


# ================= HELPER =================

def get_chat_id(update: Update):
    if update.callback_query:
        return update.callback_query.message.chat.id
    if update.message:
        return update.message.chat.id
    return None


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    context.user_data.clear()

    context.user_data["name"] = user.first_name or "Student"
    context.user_data["username"] = user.username or ""

    keyboard = []

    for i in range(0, len(UNITS), 2):
        row = []
        for unit in UNITS[i:i+2]:
            row.append(
                InlineKeyboardButton(
                    f"Unit {unit}",
                    callback_data=f"unit_{unit}"
                )
            )
        keyboard.append(row)

    await update.message.reply_text(
        "ENGLISH PLACEMENT TEST (A1)\n\n"
        "Select unit to start:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return SELECTING_UNIT


# ================= SELECT UNIT =================

async def select_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    unit = int(query.data.split("_")[1])

    context.user_data["current_unit"] = unit
    context.user_data["grammar_score"] = 0
    context.user_data["vocab_score"] = 0
    context.user_data["current_question"] = 0

    await query.edit_message_text(
        f"{UNIT_TITLES[unit]}\n\nGrammar test starting..."
    )

    await send_grammar_question(update, context)

    return GRAMMAR_TEST


# ================= SEND GRAMMAR QUESTION =================

async def send_grammar_question(update: Update, context: ContextTypes.DEFAULT_TYPE):

    unit = context.user_data["current_unit"]
    q = context.user_data["current_question"]

    questions = UNIT_DATA[unit]["grammar"]

    if q >= len(questions):
        return await start_vocab_training(update, context)

    data = questions[q]

    keyboard = []

    for i, option in enumerate(data["options"]):
        keyboard.append([
            InlineKeyboardButton(
                option,
                callback_data=f"grammar_{i}"
            )
        ])

    chat_id = get_chat_id(update)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Question {q+1}/20\n\n{data['question']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= HANDLE GRAMMAR ANSWER =================

async def handle_grammar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    answer = int(query.data.split("_")[1])

    unit = context.user_data["current_unit"]
    q = context.user_data["current_question"]

    correct = UNIT_DATA[unit]["grammar"][q]["correct"]

    if answer == correct:
        context.user_data["grammar_score"] += 1

    context.user_data["current_question"] += 1

    await query.delete_message()

    return await send_grammar_question(update, context)


# ================= VOCAB TRAINING =================

async def start_vocab_training(update: Update, context: ContextTypes.DEFAULT_TYPE):

    unit = context.user_data["current_unit"]

    context.user_data["current_question"] = 0

    vocab = UNIT_DATA[unit]["vocabulary"]

    chat_id = get_chat_id(update)

    await context.bot.send_message(
        chat_id=chat_id,
        text="VOCABULARY TRAINING"
    )

    for v in vocab:

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{v['word']} = {v['tajik']}\n{v.get('example_en','')}"
        )

    keyboard = [[InlineKeyboardButton("START TEST", callback_data="start_vocab")]]

    await context.bot.send_message(
        chat_id=chat_id,
        text="Start vocabulary test?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return VOCAB_TRAINING


# ================= START VOCAB TEST =================

async def start_vocab_test(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    await query.delete_message()

    return await send_vocab_question(update, context)


# ================= SEND VOCAB QUESTION =================

async def send_vocab_question(update: Update, context: ContextTypes.DEFAULT_TYPE):

    unit = context.user_data["current_unit"]
    q = context.user_data["current_question"]

    vocab = UNIT_DATA[unit]["vocabulary"]

    if q >= len(vocab):
        return await show_results(update, context)

    data = vocab[q]

    keyboard = []

    for i, option in enumerate(data["options"]):
        keyboard.append([
            InlineKeyboardButton(
                option,
                callback_data=f"vocab_{i}"
            )
        ])

    chat_id = get_chat_id(update)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Question {q+1}/10\n\n{data['question']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return VOCAB_TEST


# ================= HANDLE VOCAB =================

async def handle_vocab(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    answer = int(query.data.split("_")[1])

    unit = context.user_data["current_unit"]
    q = context.user_data["current_question"]

    correct = UNIT_DATA[unit]["vocabulary"][q]["correct"]

    if answer == correct:
        context.user_data["vocab_score"] += 1

    context.user_data["current_question"] += 1

    await query.delete_message()

    return await send_vocab_question(update, context)


# ================= SHOW RESULTS =================

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):

    grammar = context.user_data["grammar_score"]
    vocab = context.user_data["vocab_score"]

    total = grammar + vocab

    percent = round(total / 30 * 100, 1)

    status = "PASS" if percent >= PASS_THRESHOLD else "FAIL"

    user = update.effective_user

    result = db.save_result(
        student_id=user.id,
        name=context.user_data["name"],
        username=context.user_data["username"],
        unit=context.user_data["current_unit"],
        grammar_score=grammar,
        vocab_score=vocab,
        total_score=total,
        percentage=percent,
        status=status
    )

    chat_id = get_chat_id(update)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"RESULT\nScore: {total}/30\nPercent: {percent}%\nStatus: {status}"
    )

    for admin in ADMIN_IDS:
        await context.bot.send_message(
            chat_id=admin,
            text=f"New result\n{result['name']} {total}/30"
        )

    context.user_data.clear()

    return ConversationHandler.END


# ================= ADMIN =================

async def admin_results(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id not in ADMIN_IDS:
        return

    results = db.get_all_results()

    if not results:
        await update.message.reply_text("No results.")
        return

    text = "RESULTS\n\n"

    for r in results[-10:]:
        text += f"{r['name']} Unit {r['unit']} {r['total_score']}/30\n"

    await update.message.reply_text(text)


# ================= CANCEL =================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text("Cancelled.")

    return ConversationHandler.END


# ================= MAIN =================

def main():

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(

        entry_points=[CommandHandler("start", start)],

        states={

            SELECTING_UNIT: [
                CallbackQueryHandler(select_unit, pattern="unit_"),
            ],

            GRAMMAR_TEST: [
                CallbackQueryHandler(handle_grammar, pattern="grammar_"),
            ],

            VOCAB_TRAINING: [
                CallbackQueryHandler(start_vocab_test, pattern="start_vocab"),
            ],

            VOCAB_TEST: [
                CallbackQueryHandler(handle_vocab, pattern="vocab_"),
            ],

        },

        fallbacks=[CommandHandler("cancel", cancel)],

        allow_reentry=True

    )

    app.add_handler(conv)

    app.add_handler(CommandHandler("results", admin_results))

    print("BOT RUNNING")

    app.run_polling()


# ================= START =================

if __name__ == "__main__":
    main()

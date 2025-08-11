import os
import logging
import tempfile
from fpdf import FPDF
import smtplib
from email.message import EmailMessage
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

(
    COMPANY,
    CONTACT_NAME,
    PHONE,
    INDUSTRY,
    PRESSURE,
    FLOW,
    ACCESSORIES,
    COMMENTS,
) = range(8)

QUESTIONS = [
    ("Название компании:", COMPANY),
    ("Контактное лицо (ФИО):", CONTACT_NAME),
    ("Телефон / WhatsApp:", PHONE),
    ("Отрасль / Применение:", INDUSTRY),
    ("Требуемое рабочее давление (бар):", PRESSURE),
    ("Требуемая производительность (м³/мин или л/мин):", FLOW),
    ("Нужны ли осушитель / фильтры / ресивер? Укажи какие:", ACCESSORIES),
    ("Доп. пожелания / комментарии:", COMMENTS),
]

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

user_answers = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_answers[user.id] = {}
    await update.message.reply_text("Здравствуйте! Я помогу подобрать компрессор. Отвечайте на вопросы.")
    question_text = QUESTIONS[0][0]
    await update.message.reply_text(question_text)
    context.user_data["q_index"] = 0
    return QUESTIONS[0][1]

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    q_index = context.user_data.get("q_index", 0)
    question_label = QUESTIONS[q_index][0]
    user_answers.setdefault(user.id, {})[question_label] = text

    q_index += 1
    context.user_data["q_index"] = q_index

    if q_index < len(QUESTIONS):
        next_q = QUESTIONS[q_index][0]
        await update.message.reply_text(next_q)
        return QUESTIONS[q_index][1]
    else:
        await update.message.reply_text("Спасибо! Формирую PDF и отправляю на почту.")
        try:
            pdf_path = generate_pdf_for_user(user.id, user_answers[user.id])
            send_email_with_pdf(pdf_path, user.id, user_answers[user.id])
            await update.message.reply_text("Готово — заявка отправлена.")
        except Exception as e:
            logger.exception("Ошибка при отправке: %s", e)
            await update.message.reply_text("Ошибка при отправке заявки.")
        user_answers.pop(user.id, None)
        context.user_data.pop("q_index", None)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_answers.pop(user.id, None)
    await update.message.reply_text("Опрос отменён. Начните снова /start")
    return ConversationHandler.END

def generate_pdf_for_user(user_id: int, answers: dict) -> str:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, "Заявка с Telegram-бота", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", size=12)
    for k, v in answers.items():
        pdf.multi_cell(0, 8, f"{k} {v}")
        pdf.ln(2)
    tmpdir = tempfile.gettempdir()
    out_path = os.path.join(tmpdir, f"request_{user_id}.pdf")
    pdf.output(out_path)
    return out_path

def send_email_with_pdf(pdf_path: str, user_id: int, answers: dict):
    if not (EMAIL_USER and EMAIL_PASS and EMAIL_TO):
        raise RuntimeError("SMTP не настроен.")
    msg = EmailMessage()
    msg["Subject"] = "Новая заявка"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    body = ["Новая заявка:"]
    for k, v in answers.items():
        body.append(f"{k}: {v}")
    msg.set_content("\n".join(body))
    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename="request.pdf")
    if EMAIL_PORT == 465:
        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            COMPANY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            CONTACT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            INDUSTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            PRESSURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            FLOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            ACCESSORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            COMMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()

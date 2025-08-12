import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from fpdf import FPDF

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Этапы диалога
(Q1, Q2, Q3, Q4, Q5) = range(5)

# Данные пользователя
user_data = {}

# Вопросы
QUESTIONS = [
    "1️⃣ Какое рабочее давление (в барах) требуется?",
    "2️⃣ Какая производительность (м³/мин) нужна?",
    "3️⃣ Какая мощность двигателя (кВт) допустима?",
    "4️⃣ Нужен ли осушитель воздуха? (да/нет)",
    "5️⃣ Нужен ли ресивер? (да/нет)"
]

# Команда /start
def start(update, context):
    user_data[update.message.chat_id] = []
    update.message.reply_text("Привет! Я помогу подобрать компрессор. Отвечайте на вопросы по очереди.")
    update.message.reply_text(QUESTIONS[0])
    return Q1

# Вопрос 1
def answer_q1(update, context):
    user_data[update.message.chat_id].append(update.message.text)
    update.message.reply_text(QUESTIONS[1])
    return Q2

# Вопрос 2
def answer_q2(update, context):
    user_data[update.message.chat_id].append(update.message.text)
    update.message.reply_text(QUESTIONS[2])
    return Q3

# Вопрос 3
def answer_q3(update, context):
    user_data[update.message.chat_id].append(update.message.text)
    update.message.reply_text(QUESTIONS[3])
    return Q4

# Вопрос 4
def answer_q4(update, context):
    user_data[update.message.chat_id].append(update.message.text)
    update.message.reply_text(QUESTIONS[4])
    return Q5

# Вопрос 5 — финал
def answer_q5(update, context):
    user_data[update.message.chat_id].append(update.message.text)

    # Формируем PDF
    pdf_path = generate_pdf(update.message.chat_id)

    # Отправляем на email
    send_email(pdf_path)

    update.message.reply_text("✅ Спасибо! Заявка отправлена на обработку.")
    return ConversationHandler.END

# Генерация PDF
def generate_pdf(chat_id):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, "Заявка на подбор компрессора", ln=True, align="C")
    pdf.ln(10)

    for i, answer in enumerate(user_data[chat_id]):
        pdf.cell(0, 10, f"{QUESTIONS[i]} {answer}", ln=True)

    pdf_path = f"/tmp/request_{chat_id}.pdf"
    pdf.output(pdf_path)
    return pdf_path

# Отправка email с PDF
def send_email(pdf_path):
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    EMAIL_TO = "d.gabd@igateway.ltd"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = "Заявка с Telegram-бота"

    # Текст
    msg.attach(MIMEText("В приложении анкета пользователя."))

    # PDF вложение
    with open(pdf_path, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
        msg.attach(attach)

    # SMTP отправка
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

# Отмена
def cancel(update, context):
    update.message.reply_text("Опрос отменён.")
    return ConversationHandler.END

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Диалог
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            Q1: [MessageHandler(Filters.text & ~Filters.command, answer_q1)],
            Q2: [MessageHandler(Filters.text & ~Filters.command, answer_q2)],
            Q3: [MessageHandler(Filters.text & ~Filters.command, answer_q3)],
            Q4: [MessageHandler(Filters.text & ~Filters.command, answer_q4)],
            Q5: [MessageHandler(Filters.text & ~Filters.command, answer_q5)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    logger.info("Бот запущен и ждёт сообщений...")
    updater.idle()

if __name__ == "__main__":
    main()

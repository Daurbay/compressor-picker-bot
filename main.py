# main.py
main_py = """\
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

ASK_PRESSURE, ASK_FLOW, ASK_POWER, ASK_PURPOSE = range(4)

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "465"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

def start(update, context):
    update.message.reply_text("Здравствуйте! Давайте подберем вам компрессор.\\nКакое рабочее давление вам нужно (бар)?")
    return ASK_PRESSURE

def ask_flow(update, context):
    context.user_data['pressure'] = update.message.text
    update.message.reply_text("Какая производительность (м³/мин)?")
    return ASK_FLOW

def ask_power(update, context):
    context.user_data['flow'] = update.message.text
    update.message.reply_text("Какая мощность (кВт)?")
    return ASK_POWER

def ask_purpose(update, context):
    context.user_data['power'] = update.message.text
    update.message.reply_text("Для чего будет использоваться компрессор?")
    return ASK_PURPOSE

def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, "Заявка на подбор компрессора", ln=True, align="C")
    pdf.set_font("Arial", size=12)
    for key, value in data.items():
        pdf.cell(200, 10, f"{key}: {value}", ln=True)
    filename = "request.pdf"
    pdf.output(filename)
    return filename

def send_email(file_path):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    msg['Subject'] = "Заявка с Telegram-бота"

    part = MIMEBase('application', 'octet-stream')
    with open(file_path, 'rb') as f:
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="request.pdf"')
    msg.attach(part)

    import ssl
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def finish(update, context):
    context.user_data['purpose'] = update.message.text
    pdf_file = generate_pdf(context.user_data)
    send_email(pdf_file)
    update.message.reply_text("Спасибо! Ваша заявка отправлена.")
    return ConversationHandler.END

def cancel(update, context):
    update.message.reply_text("Заявка отменена.")
    return ConversationHandler.END

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_PRESSURE: [MessageHandler(Filters.text & ~Filters.command, ask_flow)],
            ASK_FLOW: [MessageHandler(Filters.text & ~Filters.command, ask_power)],
            ASK_POWER: [MessageHandler(Filters.text & ~Filters.command, ask_purpose)],
            ASK_PURPOSE: [MessageHandler(Filters.text & ~Filters.command, finish)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
"""


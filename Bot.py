import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "COLE_SEU_TOKEN_NOVO_AQUI"
CHAT_ID = -1003971306082

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == CHAT_ID:
        await update.message.reply_text("Bot online. Manda /jogos pra ver a análise de hoje.")

async def jogos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    
    msg = """
🏆 *Análises Copa 2026 - Hoje*

*Brasil x Argentina - 21h*
Média de gols do confronto: 2.8

Últimos 5 jogos: 4 tiveram Over 1.5
Tendência: *Over 1.5 gols*

⚠️ Isso é análise, não dica de aposta. Jogue com responsabilidade.
"""
    await update.message.reply_text(msg, parse_mode='Markdown')

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jogos", jogos))
    print("Bot rodando...")
    app.run_polling()

if __name__ == '__main__':
    main()

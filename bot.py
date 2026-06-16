import os
import asyncio
from telegram import Bot

TOKEN = os.getenv("TOKEN")

async def main():
    bot = Bot(TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook deletado com sucesso")

asyncio.run(main())

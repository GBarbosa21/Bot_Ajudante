import discord
from discord.ext import commands
from discord import app_commands
import os
import gspread
import json
from flask import Flask, request
from threading import Thread
import asyncio

# --- CONFIGURAÇÃO INICIAL (Gspread e Intents) ---
# ... (toda a sua configuração inicial de gspread continua aqui) ...
google_credentials_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if google_credentials_str:
    try:
        google_credentials_dict = json.loads(google_credentials_str)
        gc = gspread.service_account_from_dict(google_credentials_dict)
        print("Credenciais do Google carregadas com sucesso!")
        spreadsheet = gc.open("Cópia de @Status clientes 2025")
        worksheet = spreadsheet.worksheet("AGOSTO 2025")
        print(f"Conectado à planilha '{spreadsheet.title}' e à aba '{worksheet.title}'.")
    except Exception as e:
        print(f"ERRO ao conectar à planilha: {e}")
        spreadsheet = None
else:
    gc = None
    spreadsheet = None
    print("AVISO: Secret 'GOOGLE_CREDENTIALS_JSON' não encontrado.")


# --- BOT, FLASK E CONFIGURAÇÕES DE SEGURANÇA ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
SECRET_KEY = os.environ.get("NOTIFY_SECRET_KEY")
TARGET_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID"))

app = Flask('')

# --- LÓGICA DO SERVIDOR WEB ---

# --- INÍCIO DA CORREÇÃO ---
@app.route('/')
def health_check():
    """
    Esta é a rota de "Health Check".
    Ela responde aos pings do Render para manter o serviço online.
    """
    return "Bot is alive and listening!", 200
# --- FIM DA CORREÇÃO ---


@app.route('/notify', methods=['POST'])
def handle_notification():
    auth_key = request.headers.get('Authorization')
    if auth_key != SECRET_KEY:
        return "Unauthorized", 401

    data = request.json
    mensagem = data.get('message')

    if not mensagem:
        return "Bad Request: 'message' not found in JSON", 400

    bot.loop.call_soon_threadsafe(
        asyncio.create_task,
        enviar_notificacao_discord(mensagem)
    )
    
    return "Notification received!", 200

async def enviar_notificacao_discord(mensagem: str):
    try:
        channel = await bot.fetch_channel(TARGET_CHANNEL_ID)
        if channel:
            await channel.send(mensagem)
            print(f"Notificação enviada para o canal {TARGET_CHANNEL_ID}")
    except Exception as e:
        print(f"Erro ao enviar notificação para o Discord: {e}")

# --- EVENTOS E COMANDOS DO DISCORD ---
# ... (Todos os seus comandos /verificar, /ajuda, etc. continuam aqui) ...
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    await bot.tree.sync()
    print('---------------------------')

# --- FUNÇÕES PARA RODAR TUDO JUNTO ---
def run_flask():
    app.run(host='0.0.0.0', port=8080)

def run_bot():
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("ERRO CRÍTICO FINAL: Impossível iniciar o bot. Token do Discord não encontrado.")

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    run_bot()

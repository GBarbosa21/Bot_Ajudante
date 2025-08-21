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
        # Removido print daqui para um log mais limpo
        spreadsheet = gc.open("Cópia de @Status clientes 2025")
        worksheet = spreadsheet.worksheet("AGOSTO 2025")
        print(f"Conectado à planilha '{spreadsheet.title}'.")
    except Exception as e:
        print(f"ERRO CRÍTICO ao conectar à planilha: {e}")
        spreadsheet = None
else:
    gc = None; spreadsheet = None
    print("AVISO: Secret 'GOOGLE_CREDENTIALS_JSON' não encontrado.")

# --- BOT, FLASK E CONFIGURAÇÕES DE SEGURANÇA ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
SECRET_KEY = os.environ.get("NOTIFY_SECRET_KEY")
TARGET_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID"))

app = Flask('')

# --- LÓGICA DO SERVIDOR WEB (COM LOGS DETALHADOS) ---
@app.route('/')
def health_check():
    return "Bot is alive and listening!", 200

@app.route('/notify', methods=['POST'])
def handle_notification():
    print("\n--- ROTA /notify ACIONADA! ---")
    
    # Log 1: Verifica o cabeçalho de autorização
    auth_key = request.headers.get('Authorization')
    print(f"Cabeçalho de autorização recebido: '{auth_key}'")
    
    if auth_key != SECRET_KEY:
        print("!!! FALHA DE AUTORIZAÇÃO !!! Chave secreta não confere.")
        return "Unauthorized", 401

    print(">>> Autorização OK.")
    
    # Log 2: Tenta processar os dados JSON
    try:
        data = request.json
        print(f"Dados JSON recebidos: {data}")
        mensagem = data.get('message')
    except Exception as e:
        print(f"!!! ERRO AO PROCESSAR JSON !!! Detalhes: {e}")
        return "JSON Error", 400

    # Log 3: Verifica se a mensagem existe
    if not mensagem:
        print("!!! FALHA: 'message' não encontrada no JSON.")
        return "Bad Request: 'message' not found in JSON", 400
    
    print(">>> Mensagem extraída com sucesso. Agendando tarefa no Discord...")
    
    # Log 4: Agenda a tarefa no loop do bot
    bot.loop.call_soon_threadsafe(
        asyncio.create_task,
        enviar_notificacao_discord(mensagem)
    )
    
    print("--- ROTA /notify CONCLUÍDA COM SUCESSO ---")
    return "Notification received!", 200

async def enviar_notificacao_discord(mensagem: str):
    try:
        channel = await bot.fetch_channel(TARGET_CHANNEL_ID)
        if channel:
            await channel.send(mensagem)
            print(f">>> Notificação enviada para o canal {TARGET_CHANNEL_ID}")
    except Exception as e:
        print(f">>> ERRO ao tentar enviar notificação para o Discord: {e}")

# --- EVENTOS E COMANDOS DO DISCORD ---
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    await bot.tree.sync()
    print('---------------------------')
# ... (Seus comandos /verificar, /ajuda, etc. continuam aqui) ...

# --- FUNÇÕES PARA RODAR TUDO JUNTO ---
def run_flask():
    app.run(host='0.0.0.0', port=8080)
def run_bot():
    if TOKEN: bot.run(TOKEN)
    else: print("ERRO CRÍTICO FINAL: Token do Discord não encontrado.")

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    run_bot()

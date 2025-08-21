import discord
from discord.ext import commands
from discord import app_commands
import os
import gspread
import json
import asyncio

# --- NOVAS BIBLIOTECAS PARA O SERVIDOR WEB ---
from fastapi import FastAPI, Request, HTTPException

# --- CONFIGURAÇÃO INICIAL (Gspread e Intents) ---
google_credentials_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
spreadsheet = None
worksheet = None
if google_credentials_str:
    try:
        google_credentials_dict = json.loads(google_credentials_str)
        gc = gspread.service_account_from_dict(google_credentials_dict)
        spreadsheet = gc.open("Cópia de @Status clientes 2025")
        worksheet = spreadsheet.worksheet("AGOSTO 2025")
        print(f"Conectado à planilha '{spreadsheet.title}'.")
    except Exception as e:
        print(f"ERRO CRÍTICO ao conectar à planilha: {e}")
else:
    print("AVISO: Secret 'GOOGLE_CREDENTIALS_JSON' não encontrado.")

# --- BOT, FASTAPI E CONFIGURAções DE SEGURANÇA ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
SECRET_KEY = os.environ.get("NOTIFY_SECRET_KEY")
TARGET_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID"))

app = FastAPI(docs_url=None, redoc_url=None) # Desativa a documentação automática

# --- LÓGICA DO SERVIDOR WEB (FASTAPI) ---

# --- INÍCIO DA CORREÇÃO ---
# Em vez de @app.get, usamos @app.api_route para aceitar tanto GET quanto HEAD.
@app.api_route("/", methods=["GET", "HEAD"])
def health_check():
    """Rota de Health Check para o Render."""
    return {"status": "Bot is alive and listening!"}
# --- FIM DA CORREÇÃO ---

@app.post("/notify")
async def handle_notification(request: Request):
    """Recebe a notificação do Google Apps Script."""
    auth_key = request.headers.get('Authorization')
    if auth_key != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        data = await request.json()
        mensagem = data.get('message')
        if not mensagem:
            raise HTTPException(status_code=400, detail="Bad Request: 'message' not found")
        
        channel = await bot.fetch_channel(TARGET_CHANNEL_ID)
        if channel:
            await channel.send(mensagem)
            print(f"Notificação enviada para o canal {TARGET_CHANNEL_ID}")
            return {"status": "Notification sent!"}
        else:
            raise HTTPException(status_code=500, detail="Discord channel not found")
            
    except Exception as e:
        print(f"Erro ao processar notificação: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# --- EVENTOS E COMANDOS DO DISCORD ---
# ... (Todos os seus comandos /verificar, /ajuda, etc. continuam aqui) ...
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    await bot.tree.sync()
    print('---------------------------')

# --- INICIALIZAÇÃO DO BOT E DO SERVIDOR ---
@app.on_event("startup")
async def startup_event():
    """Inicia o bot do Discord como uma tarefa de fundo."""
    asyncio.create_task(bot.start(TOKEN))
    print("Tarefa de inicialização do bot do Discord criada.")

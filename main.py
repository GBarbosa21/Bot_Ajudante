import discord
from discord.ext import commands
from discord import app_commands
import os
import gspread
import json
import asyncio
import re

# --- BIBLIOTECAS PARA O SERVIDOR WEB DE PRODUÇÃO ---
from fastapi import FastAPI, Request, HTTPException

# --- CONFIGURAÇÃO INICIAL (Gspread e Intents) ---
# ... (sua configuração de conexão com a planilha continua a mesma) ...
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

# --- BOT, FASTAPI E CONFIGURAÇÕES DE SEGURANÇA ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
SECRET_KEY = os.environ.get("NOTIFY_SECRET_KEY")
TARGET_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID"))

app = FastAPI(docs_url=None, redoc_url=None)

# --- LÓGICA DO SERVIDOR WEB (FASTAPI) ---

@app.api_route("/", methods=["GET", "HEAD"])
def health_check():
    return {"status": "Bot is alive and listening!"}

@app.post("/notify")
async def handle_notification(request: Request):
    if request.headers.get('Authorization') != SECRET_KEY:
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

# --- FUNÇÃO AUXILIAR PARA O LEMBRETE ---
def parse_time(time_str: str) -> int:
    match = re.match(r"(\d+)([smh])$", time_str.lower())
    if not match: return None
    value, unit = match.groups()
    value = int(value)
    if unit == 's': return value
    if unit == 'm': return value * 60
    if unit == 'h': return value * 3600
    return None

# --- EVENTOS E COMANDOS DO DISCORD ---

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    await bot.tree.sync()
    print('---------------------------')

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user: return
    if str(reaction.emoji) == '👍':
        message = reaction.message
        if message.author == bot.user and "pronto para Impressão!" in message.content and "(impresso)" not in message.content:
            novo_conteudo = message.content + " (impresso)"
            await message.edit(content=novo_conteudo)
            print(f"Mensagem {message.id} editada para adicionar '(impresso)'")

# --- Seus Comandos de Barra ---
@bot.tree.command(name="ajuda", description="Mostra uma lista de todos os comandos disponíveis.")
# ... (código do /ajuda) ...

@bot.tree.command(name="verificar", description="Verifica orçamentos com status pendentes na planilha.")
# ... (código do /verificar) ...

@bot.tree.command(name="lembrete", description="Agenda um lembrete para você.")
# ... (código do /lembrete) ...

@bot.tree.command(name="ponto", description="Agenda um lembrete de 1 hora para bater o ponto.")
# ... (código do /ponto) ...

# --- Seus Comandos de Prefixo ---
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def mengao(ctx):
    await ctx.send('O mengão ganhou, hoje é no amor!')

@bot.command()
async def ler(ctx, celula: str):
    # ... (código do !ler) ...
    pass

# --- INICIALIZAÇÃO DO BOT E DO SERVIDOR ---
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(bot.start(TOKEN))
    print("Tarefa de inicialização do bot do Discord criada.")

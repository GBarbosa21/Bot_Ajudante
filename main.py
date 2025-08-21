print("--- INICIANDO SCRIPT DE DIAGNÓSTICO ---")

print("PASSO 1: Carregando bibliotecas...")
import discord
from discord.ext import commands
from discord import app_commands
import os
import gspread
import json
from flask import Flask, request
from threading import Thread
import asyncio
print("...Bibliotecas carregadas.")

# --- VALIDAÇÃO DAS VARIÁVEIS DE AMBIENTE (SECRETS) ---
print("\nPASSO 2: Lendo variáveis de ambiente (Secrets)...")
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
TARGET_CHANNEL_ID_STR = os.environ.get("DISCORD_CHANNEL_ID")
SECRET_KEY = os.environ.get("NOTIFY_SECRET_KEY")

print(f"...Token do Discord encontrado: {'Sim' if TOKEN else 'NÃO'}")
print(f"...Credenciais do Google encontradas: {'Sim' if GOOGLE_CREDENTIALS_JSON else 'NÃO'}")
print(f"...ID do Canal encontrado: {'Sim' if TARGET_CHANNEL_ID_STR else 'NÃO'}")
print(f"...Chave Secreta encontrada: {'Sim' if SECRET_KEY else 'NÃO'}")

# --- CONFIGURAÇÃO DA CONEXÃO COM GOOGLE SHEETS ---
print("\nPASSO 3: Configurando a conexão com Google Sheets...")
spreadsheet = None
worksheet = None
if GOOGLE_CREDENTIALS_JSON:
    try:
        google_credentials_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        gc = gspread.service_account_from_dict(google_credentials_dict)
        print("...Autenticação com Google OK.")
        
        spreadsheet = gc.open("Cópia de @Status clientes 2025")
        worksheet = spreadsheet.worksheet("AGOSTO 2025")
        print(f"...Conectado com sucesso à planilha '{spreadsheet.title}'.")
    except json.JSONDecodeError:
        print("ERRO CRÍTICO NO PASSO 3: O conteúdo do Secret 'GOOGLE_CREDENTIALS_JSON' não é um JSON válido.")
    except Exception as e:
        print(f"ERRO CRÍTICO NO PASSO 3: Falha ao conectar com Google Sheets. Detalhes: {e}")
else:
    print("...Credenciais do Google não encontradas, pulando conexão.")

# --- CONFIGURAÇÃO DO BOT DISCORD ---
print("\nPASSO 4: Configurando o bot do Discord...")
try:
    TARGET_CHANNEL_ID = int(TARGET_CHANNEL_ID_STR)
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    print("...Configuração do bot OK.")
except Exception as e:
    print(f"ERRO CRÍTICO NO PASSO 4: Falha ao configurar o bot. Verifique o DISCORD_CHANNEL_ID. Detalhes: {e}")

# --- CONFIGURAÇÃO DO SERVIDOR WEB (FLASK) ---
print("\nPASSO 5: Configurando o servidor Flask...")
app = Flask('')
print("...Configuração do Flask OK.")

@app.route('/notify', methods=['POST'])
def handle_notification():
    # ... (A lógica do Flask permanece a mesma) ...
    pass

# --- EVENTOS E COMANDOS DO DISCORD ---
# ... (Todos os seus comandos /verificar, /ajuda, etc. devem estar aqui) ...
@bot.event
async def on_ready():
    print(f'\n--- BOT CONECTADO COMO {bot.user} ---')
    await bot.tree.sync()
    print('------------------------------------')


# --- FUNÇÕES PARA INICIALIZAÇÃO ---
def run_flask():
    print("...Tentando iniciar o servidor Flask...")
    app.run(host='0.0.0.0', port=8080)

def run_bot():
    if TOKEN:
        print("...Tentando iniciar o bot do Discord...")
        bot.run(TOKEN)
    else:
        print("ERRO CRÍTICO FINAL: Impossível iniciar o bot. Token do Discord não encontrado.")

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    print("\nPASSO 6: Iniciando o bot e o servidor...")
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    run_bot()

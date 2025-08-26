import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# Carrega as variáveis do arquivo .env (para testes locais)
load_dotenv()
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

# --- INÍCIO DA PARTE DO SERVIDOR WEB ---
# Criamos um servidor web mínimo apenas para manter o Render feliz.
app = Flask('')

@app.route('/')
def health_check():
    """Esta rota responde aos 'pings' do Render e do UptimeRobot."""
    return "Bot de comandos está online!", 200

def run_flask():
    """Roda o servidor Flask na porta que o Render espera."""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
# --- FIM DA PARTE DO SERVIDOR WEB ---


# --- CONFIGURAÇÃO DO BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True # Adicionado para eventos de reação
bot = commands.Bot(command_prefix='!', intents=intents)

# --- EVENTO ON_READY ---
@bot.event
async def on_ready():
    """Evento que roda quando o bot está online e pronto."""
    print(f'Bot conectado como {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos de barra.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
    print('---------------------------')

# --- FUNÇÃO PRINCIPAL ---
async def main():
    """Função principal que carrega os cogs e inicia o bot."""
    print("Carregando Cogs...")
    # Itera sobre os arquivos na pasta 'cogs'
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"Cog '{filename[:-3]}' carregado com sucesso.")
            except Exception as e:
                print(f"Falha ao carregar o cog {filename[:-3]}: {e}")
    
    # Inicia o bot
    if TOKEN:
        await bot.start(TOKEN)
    else:
        print("ERRO CRÍTICO: O Secret DISCORD_BOT_TOKEN não foi encontrado.")

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    # Inicia o servidor web Flask em uma thread de fundo
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Roda o bot do Discord na thread principal usando asyncio
    asyncio.run(main())

import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

# Define as intenções do bot
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True # Adicionado para o evento de reação

# Cria a instância do bot
bot = commands.Bot(command_prefix='!', intents=intents)

# --- Carregamento dos Cogs ---
async def load_cogs():
    """Encontra e carrega todos os Cogs na pasta /cogs."""
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
            print(f"Cog '{filename[:-3]}' carregado.")

# --- Evento on_ready ---
@bot.event
async def on_ready():
    """Evento que roda quando o bot está online e pronto."""
    print(f'Bot conectado como {bot.user}')
    # Sincroniza os comandos de barra com o Discord
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos de barra.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
    print('---------------------------')

# --- Função Principal ---
async def main():
    """Função principal que carrega os cogs e inicia o bot."""
    async with bot:
        await load_cogs()
        if TOKEN:
            await bot.start(TOKEN)
        else:
            print("ERRO CRÍTICO: O Secret DISCORD_BOT_TOKEN não foi encontrado.")

# --- Inicialização ---
if __name__ == "__main__":
    asyncio.run(main())

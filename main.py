import discord
from discord.ext import commands
from discord import app_commands
import os
import gspread
import json
import asyncio
import re

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
    print("AVISO: Secret 'GOOGLE_CREDENTIALS_JSON' não encontrado. Funções da planilha desativadas.")

# --- BOT E CONFIGURAÇÕES DE SEGURANÇA ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

# --- EVENTOS E COMANDOS DO DISCORD ---

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos de barra.")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
    print('---------------------------')

# --- COMANDOS DE BARRA (SLASH COMMANDS) ---

@bot.tree.command(name="verificar", description="Verifica orçamentos com status pendentes na planilha.")
@app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos no canal.")
async def verificar(interaction: discord.Interaction, efemero: bool = True):
    if not spreadsheet:
        await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=efemero)
        return
    try:
        await interaction.response.defer(ephemeral=efemero)
        status_para_procurar = ["16 Cart.Tradução", "17 Cart.Original", "Embalar", "05 Imprimir"]
        todos_os_dados = worksheet.get_all_values()
        orcamentos_encontrados = {}
        for linha in todos_os_dados[1:]:
            try:
                status_da_linha = linha[7]  # Coluna H
                id_orcamento = linha[3]   # Coluna D
                nome_cliente = linha[2]   # Coluna C
            except IndexError:
                continue
            if status_da_linha in status_para_procurar:
                if status_da_linha not in orcamentos_encontrados:
                    orcamentos_encontrados[status_da_linha] = []
                if id_orcamento and nome_cliente:
                    linha_formatada = f"{id_orcamento} - {nome_cliente}"
                    orcamentos_encontrados[status_da_linha].append(linha_formatada)
        
        if not orcamentos_encontrados:
            await interaction.followup.send("Nenhum orçamento encontrado com os status de verificação.", ephemeral=efemero)
            return
            
        resposta_texto = "📋 **Orçamentos Pendentes Encontrados:**\n\n"
        for status, orcamentos in orcamentos_encontrados.items():
            if orcamentos:
                resposta_texto += f"**{status}**\n"
                lista_de_orcamentos = "\n".join(orcamentos)
                resposta_texto += f"```{lista_de_orcamentos}```\n"
        
        if len(resposta_texto) > 2000:
            resposta_texto = resposta_texto[:1990] + "\n...(lista muito longa, foi cortada)"
            
        await interaction.followup.send(resposta_texto, ephemeral=efemero)

    except Exception as e:
        await interaction.followup.send(f"Ocorreu um erro ao verificar a planilha: {e}", ephemeral=efemero)

# Adicione outros comandos (/ajuda, /ponto, etc.) aqui se desejar.

# --- INICIALIZAÇÃO DO BOT ---
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERRO CRÍTICO FINAL: O Secret DISCORD_BOT_TOKEN não foi encontrado.")

import discord
from discord.ext import commands
from discord import app_commands
import os
import gspread
import json
from flask import Flask, request
from threading import Thread
import asyncio

# --- CONFIGURAÇÃO INICIAL (Gspread) ---
google_credentials_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if google_credentials_str:
    try:
        google_credentials_dict = json.loads(google_credentials_str)
        gc = gspread.service_account_from_dict(google_credentials_dict)
        print("Credenciais do Google carregadas com sucesso!")

        # Conecta à planilha
        spreadsheet = gc.open("Cópia de @Status clientes 2025")
        worksheet = spreadsheet.worksheet("AGOSTO 2025")
        print(f"Conectado à planilha '{spreadsheet.title}' e à aba '{worksheet.title}'.")
    except Exception as e:
        print(f"ERRO ao conectar à planilha: {e}")
        spreadsheet = None
else:
    gc = None
    spreadsheet = None
    print("AVISO: Secret 'GOOGLE_CREDENTIALS_JSON' não encontrado. Funções da planilha desativadas.")

# --- BOT, FLASK E CONFIGURAÇÕES DE SEGURANÇA ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True # Habilita o recebimento de eventos de reação
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
SECRET_KEY = os.environ.get("NOTIFY_SECRET_KEY")
TARGET_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID"))

# Cria a aplicação web Flask
app = Flask('')

# --- LÓGICA PARA ARMAZENAR IDs DE MENSAGENS DE IMPRESSÃO (Opcional, mas útil para otimização) ---
mensagens_impressao = {} # Um dicionário para guardar {message_id: True}

# --- LÓGICA DO SERVIDOR WEB (O "OUVIDO" DO BOT) ---

@app.route('/notify', methods=['POST'])
def handle_notification():
    auth_key = request.headers.get('Authorization')
    if auth_key != SECRET_KEY:
        print(f"Tentativa de acesso não autorizada. Chave recebida: {auth_key}")
        return "Unauthorized", 401

    data = request.json
    mensagem = data.get('message')
    id_orcamento = data.get('id_orcamento') # Podemos enviar o ID do orçamento também

    if not mensagem:
        return "Bad Request: 'message' not found in JSON", 400

    bot.loop.call_soon_threadsafe(
        asyncio.create_task,
        enviar_notificacao_impressao_discord(mensagem, id_orcamento)
    )

    return "Notification received!", 200

async def enviar_notificacao_impressao_discord(mensagem: str, id_orcamento=None):
    """Função assíncrona para enviar a notificação de impressão e armazenar o ID da mensagem."""
    try:
        channel = await bot.fetch_channel(TARGET_CHANNEL_ID)
        if channel:
            sent_message = await channel.send(mensagem)
            if id_orcamento:
                mensagens_impressao.update({sent_message.id: id_orcamento}) # Armazena o ID da mensagem
            print(f"Notificação de impressão enviada para o canal {TARGET_CHANNEL_ID} (ID: {sent_message.id})")
    except Exception as e:
        print(f"Erro ao enviar notificação de impressão para o Discord: {e}")

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

@bot.event
async def on_reaction_add(reaction, user):
    """Evento chamado quando uma reação é adicionada a uma mensagem."""
    if user == bot.user:
        return # Ignora as próprias reações do bot

    if str(reaction.emoji) == '👍': # Verifica se a reação é o emoji desejado
        message = await reaction.message.fetch() # Garante que temos a versão mais recente da mensagem
        if message.author == bot.user and "pronto para Impressão!" in message.content and "(impresso)" not in message.content:
            novo_conteudo = message.content + " (impresso)"
            await message.edit(content=novo_conteudo)
            print(f"Mensagem {message.id} editada para adicionar '(impresso)'")

# Comandos de Barra
@bot.tree.command(name="verificar", description="Verifica orçamentos com status pendentes na planilha.")
@app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos no canal.")
async def verificar(interaction: discord.Interaction, efemero: bool = True):
    if not spreadsheet:
        await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=efemero)
        return
    try:
        await interaction.response.defer(ephemeral=efemero)
        status_para_procurar = [
            "16 Cart.Tradução",
            "17 Cart.Original",
            "Embalar",
            "05 Imprimir"
        ]
        todos_os_dados = worksheet.get_all_values()
        orcamentos_encontrados = {}
        for linha in todos_os_dados:
            if linha:
                try:
                    status_da_linha = linha[-1] # Assumindo que o status é a última coluna
                    id_orcamento = linha[-2] if len(linha) > 1 else "N/A" # Assumindo ID é a penúltima
                    nome_cliente = linha[-3] if len(linha) > 2 else "N/A" # Assumindo nome é a antepenúltima
                except IndexError:
                    continue
                if status_da_linha in status_para_procurar:
                    if status_da_linha not in orcamentos_encontrados:
                        orcamentos_encontrados.setdefault(status_da_linha, [])
                    orcamentos_encontrados.setdefault(status_da_linha, []).append(f"{id_orcamento} - {nome_cliente}")

        if not orcamentos_encontrados:
            await interaction.followup.send("Nenhum orçamento encontrado com os status de verificação.", ephemeral=efemero)
            return

        resposta_texto = "📋 **Orçamentos Pendentes Encontrados:**\n\n"
        for status, orcamentos in orcamentos_encontrados.items():
            if orcamentos:
                resposta_texto += f"**{status}**\n"
                lista_de_orcamentos = "\n".join(orcamentos)
                resposta_texto += f"```{lista_de_orcamentos}'''\n"
        if len(resposta_texto) > 2000:
            resposta_texto = resposta_texto[:1990] + "\n...(lista muito longa, foi cortada)"
        await interaction.followup.send(resposta_texto, ephemeral=efemero)
    except Exception as e:
        await interaction.followup.send(f"Ocorreu um erro ao verificar a planilha: {e}", ephemeral=efemero)

# Comandos de Prefixo
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def pong(ctx):
    await ctx.send('Ping!')

@bot.command()
async def ler(ctx, celula: str):
    if not spreadsheet:
        await ctx.send("Desculpe, a conexão com a planilha não foi estabelecida.")
        return
    try:
        valor = worksheet.acell(celula.upper()).value
        await ctx.send(f'O valor da célula {celula.upper()} é: **{valor}**')
    except Exception as e:
        await ctx.send(f"Ocorreu um erro: {e}")

# --- FUNÇÕES PARA RODAR TUDO JUNTO ---

def run_flask():
    """Roda o servidor Flask."""
    app.run(host='0.0.0.0', port=8080)

def run_bot():
    """Roda o bot do Discord."""
    if TOKEN is None:
        print("ERRO CRÍTICO: O Secret DISCORD_BOT_TOKEN não foi encontrado.")
        return
    bot.run(TOKEN)

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    run_bot()

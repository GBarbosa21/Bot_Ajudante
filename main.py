import discord
from discord.ext import commands
from discord import app_commands
import os
import gspread
import json
import asyncio
import re
import time # <-- Adicionado

# --- BIBLIOTECAS PARA O SERVIDOR WEB DE PRODUÇÃO ---
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
    print("AVISO: Secret 'GOOGLE_CREDENTIALS_JSON' não encontrado. Funções da planilha desativadas.")

# --- BOT, FASTAPI E CONFIGURAÇÕES DE SEGURANÇA ---
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
SECRET_KEY = os.environ.get("NOTIFY_SECRET_KEY")
TARGET_CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID"))

app = FastAPI(docs_url=None, redoc_url=None)

# --- LÓGICA ANTI-DUPLICIDADE ---
notification_locks = {}
LOCK_COOLDOWN_SECONDS = 30

# --- LÓGICA DO SERVIDOR WEB (FASTAPI) ---

@app.api_route("/", methods=["GET", "HEAD"])
def health_check():
    """Rota de Health Check para o Render."""
    return {"status": "Bot is alive and listening!"}

@app.post("/notify")
async def handle_notification(request: Request):
    """Recebe a notificação do Google Apps Script e aplica a trava anti-duplicidade."""
    if request.headers.get('Authorization') != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        data = await request.json()
        mensagem = data.get('message')
        row_number = data.get('row_number')

        if not mensagem or not row_number:
            raise HTTPException(status_code=400, detail="Bad Request: 'message' ou 'row_number' faltando no JSON")

        # --- LÓGICA ANTI-DUPLICIDADE EM AÇÃO ---
        current_time = time.time()
        if row_number in notification_locks and (current_time - notification_locks[row_number]) < LOCK_COOLDOWN_SECONDS:
            print(f"Notificação duplicada para a linha {row_number} ignorada.")
            return {"status": "Duplicate ignored"}
        
        notification_locks[row_number] = current_time
        # --- FIM DA LÓGICA ANTI-DUPLICIDADE ---
        
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

# --- EVENTOS DO DISCORD ---

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

# --- COMANDOS DE BARRA (SLASH COMMANDS) ---

@bot.tree.command(name="ajuda", description="Mostra uma lista de todos os comandos disponíveis.")
async def ajuda(interaction: discord.Interaction):
    embed = discord.Embed(title="Ajuda do Bot", description="Aqui está uma lista de todos os comandos que eu entendo:", color=discord.Color.blue())
    for command in bot.tree.get_commands():
        embed.add_field(name=f"/{command.name}", value=command.description, inline=False)
    embed.set_footer(text="Use os comandos em um canal ou na minha mensagem direta.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="verificar", description="Verifica orçamentos com status pendentes na planilha.")
@app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos no canal.")
async def verificar(interaction: discord.Interaction, efemero: bool = True):
    if not spreadsheet:
        await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=efemero)
        return
    try:
        await interaction.response.defer(ephemeral=efemero)
        status_para_procurar = ["16 Cart Tradução", "17 Cart Original", "Embalar", "05 Imprimir"]
        todos_os_dados = worksheet.get_all_values()
        orcamentos_encontrados = {}
        for linha in todos_os_dados[1:]:
            try:
                status_da_linha = linha[7]
                id_orcamento = linha[3]
                nome_cliente = linha[2]
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

@bot.tree.command(name="lembrete", description="Agenda um lembrete para você.")
@app_commands.describe(tempo="O tempo até o lembrete (ex: 10s, 5m, 1h).", mensagem="A mensagem que você quer receber.")
async def lembrete(interaction: discord.Interaction, tempo: str, mensagem: str):
    segundos = parse_time(tempo)
    if segundos is None:
        await interaction.response.send_message(f"Formato de tempo inválido: '{tempo}'. Use 's', 'm', ou 'h'.", ephemeral=True)
        return
    await interaction.response.send_message(f"Ok! Lembrete agendado para daqui a **{tempo}**.", ephemeral=True)
    await asyncio.sleep(segundos)
    try:
        await interaction.user.send(f"⏰ **Lembrete:** {mensagem}")
    except discord.Forbidden:
        await interaction.followup.send(f"⏰ {interaction.user.mention}, seu lembrete: {mensagem}", ephemeral=False)

@bot.tree.command(name="ponto", description="Agenda um lembrete de 1 hora para bater o ponto.")
async def ponto(interaction: discord.Interaction):
    segundos = 3600
    mensagem = "Lembre de bater o ponto"
    await interaction.response.send_message("Ok! Agendei seu lembrete para bater o ponto daqui a **1 hora**.", ephemeral=True)
    await asyncio.sleep(segundos)
    try:
        await interaction.user.send(f"⏰ **Lembrete:** {mensagem}")
    except discord.Forbidden:
        await interaction.followup.send(f"⏰ {interaction.user.mention}, seu lembrete: {mensagem}", ephemeral=False)

# --- COMANDOS DE PREFIXO ---
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def mengao(ctx):
    await ctx.send('O mengão ganhou, hoje é no amor!')

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

# --- INICIALIZAÇÃO DO BOT E DO SERVIDOR ---
@app.on_event("startup")
async def startup_event():
    """Inicia o bot do Discord como uma tarefa de fundo."""
    asyncio.create_task(bot.start(TOKEN))
    print("Tarefa de inicialização do bot do Discord criada.")

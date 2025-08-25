import discord
from discord.ext import commands
from discord import app_commands
import os
import gspread
import json
from datetime import datetime
from flask import Flask
from threading import Thread

# --- CONFIGURAÇÃO INICIAL (Gspread) ---
spreadsheet = None
worksheet = None
google_credentials_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
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
bot = commands.Bot(command_prefix='!', intents=intents)
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

# --- FUNÇÕES AUXILIARES ---
def formatar_data_br(data_str: str) -> str:
    """Tenta formatar uma string de data para o padrão dd/mm/YYYY."""
    if not data_str:
        return "N/A"
    try:
        # Tenta adivinhar o formato da data vindo da planilha
        dt_obj = datetime.strptime(data_str, '%d/%m/%Y')
        return dt_obj.strftime('%d/%m/%Y')
    except ValueError:
        return data_str # Retorna o texto original se não conseguir formatar
    except Exception:
        return data_str

# --- EVENTOS DO DISCORD ---
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
    if not worksheet:
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

@bot.tree.command(name="buscar_orcamento", description="Busca os detalhes de um orçamento pelo seu ID.")
@app_commands.describe(id="O número do orçamento que você quer encontrar.")
async def buscar_orcamento(interaction: discord.Interaction, id: str):
    if not worksheet:
        await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        todos_os_dados = worksheet.get_all_values()
        linha_encontrada = None
        
        # Procura na Coluna D (índice 3) pelo ID fornecido
        for linha in todos_os_dados[1:]:
            if len(linha) > 3 and linha[3] == id:
                linha_encontrada = linha
                break

        if linha_encontrada:
            # Pega os dados da linha encontrada usando os índices corretos
            cliente = linha_encontrada[2]       # Coluna C
            num_orcamento = linha_encontrada[3] # Coluna D
            qtd_docs = linha_encontrada[4]      # Coluna E
            status = linha_encontrada[7]        # Coluna H
            data_entrega_str = linha_encontrada[1] # Coluna B
            
            # Formata a data usando nossa função auxiliar
            data_formatada = formatar_data_br(data_entrega_str)

            embed = discord.Embed(
                title=f"Detalhes do Orçamento: {num_orcamento}",
                color=discord.Color.green()
            )
            embed.add_field(name="Cliente", value=cliente, inline=True)
            embed.add_field(name="Status Atual", value=status, inline=True)
            embed.add_field(name="Qtd. Documentos", value=qtd_docs, inline=True)
            embed.add_field(name="Data de Entrega", value=data_formatada, inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"Não foi possível encontrar nenhum orçamento com o ID `{id}`.", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"Ocorreu um erro ao buscar na planilha: {e}", ephemeral=True)

@bot.tree.command(name="atrasados", description="Lista todos os projetos que estão com a data de entrega vencida.")
@app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos.")
async def atrasados(interaction: discord.Interaction, efemero: bool = True):
    if not worksheet:
        await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=efemero)

    try:
        # Defina os status que indicam que um projeto já foi concluído
        status_finalizados = ["09 Pronto", "10 Entregue", "12 Cancelado"]
        
        # Pega a data de hoje, sem as horas, para a comparação
        hoje = datetime.now().date()
        
        todos_os_dados = worksheet.get_all_values()
        projetos_atrasados = []
        
        # Índices das colunas da sua planilha
        COLUNA_DATA_ENTREGA_IDX = 1 # Coluna B
        COLUNA_ID_ORCAMENTO_IDX = 3 # Coluna D
        COLUNA_CLIENTE_IDX = 2      # Coluna C
        COLUNA_STATUS_IDX = 7       # Coluna H
        
        for linha in todos_os_dados[1:]: # Pula o cabeçalho
            try:
                data_entrega_str = linha[COLUNA_DATA_ENTREGA_IDX]
                status_da_linha = linha[COLUNA_STATUS_IDX]
                
                # Pula a linha se o status for de finalizado ou se a data estiver vazia
                if status_da_linha in status_finalizados or not data_entrega_str:
                    continue
                    
                # Converte a data da planilha para um objeto de data
                data_entrega = datetime.strptime(data_entrega_str, '%d/%m/%Y').date()
                
                # A MÁGICA: Compara se a data de entrega é anterior a hoje
                if data_entrega < hoje:
                    id_orcamento = linha[COLUNA_ID_ORCAMENTO_IDX]
                    nome_cliente = linha[COLUNA_CLIENTE_IDX]
                    projetos_atrasados.append(f"`{id_orcamento}` - {nome_cliente} (Venceu em: {data_entrega_str})")

            except (ValueError, IndexError):
                # Ignora linhas com data em formato incorreto ou mal formatadas
                continue

        if not projetos_atrasados:
            embed = discord.Embed(
                title="✅ Nenhum Projeto Atrasado",
                description="Ótima notícia! Todos os projetos estão em dia.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=efemero)
            return
            
        # Monta a resposta com os projetos atrasados
        embed = discord.Embed(
            title="🚨 Projetos Atrasados",
            description="Os seguintes projetos estão com a data de entrega vencida e precisam de atenção:",
            color=discord.Color.red()
        )
        
        lista_projetos_str = "\n".join(projetos_atrasados)
        if len(lista_projetos_str) > 4000:
            lista_projetos_str = lista_projetos_str[:4000] + "\n...(lista muito longa)"

        embed.description = lista_projetos_str
        
        await interaction.followup.send(embed=embed, ephemeral=efemero)

    except Exception as e:
        await interaction.followup.send(f"Ocorreu um erro ao verificar os projetos atrasados: {e}", ephemeral=efemero)



# Adicione outros comandos (/ajuda, /ponto, etc.) aqui se desejar.

@app.route('/')
def health_check():
    """Esta rota responde aos 'pings' do Render e do UptimeRobot."""
    return "Bot de comandos está online!", 200

def run_flask():
    """Roda o servidor Flask na porta que o Render espera."""
    # Render fornece a porta através de uma variável de ambiente PORT, com 10000 como padrão.
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    # Inicia o servidor web em uma thread de fundo
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Roda o bot na thread principal
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("ERRO CRÍTICO FINAL: O Secret DISCORD_BOT_TOKEN não foi encontrado.")

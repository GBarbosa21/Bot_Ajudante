import discord
from discord.ext import commands
from discord import app_commands
import gspread
import json
import os
from datetime import datetime

# --- Função Auxiliar de Formatação ---
def formatar_data_br(data_str: str) -> str:
    if not data_str: return "N/A"
    try:
        # Tenta adivinhar o formato da data vindo da planilha
        dt_obj = datetime.strptime(data_str, '%d/%m/%Y')
        return dt_obj.strftime('%d/%m/%Y')
    except ValueError:
        return data_str # Retorna o texto original se não conseguir formatar
    except Exception:
        return data_str

# --- Classe do Cog ---
class SpreadsheetCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.worksheet = None
        self.connect_to_sheet()

    def connect_to_sheet(self):
        """Conecta-se à planilha Google."""
        google_credentials_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if google_credentials_str:
            try:
                google_credentials_dict = json.loads(google_credentials_str)
                gc = gspread.service_account_from_dict(google_credentials_dict)
                spreadsheet = gc.open("Cópia de @Status clientes 2025")
                self.worksheet = spreadsheet.worksheet("AGOSTO 2025")
                print(f"Cog 'Spreadsheet': Conectado à planilha '{spreadsheet.title}'.")
            except Exception as e:
                print(f"Cog 'Spreadsheet': ERRO CRÍTICO ao conectar à planilha: {e}")
        else:
            print("Cog 'Spreadsheet': AVISO: Secret 'GOOGLE_CREDENTIALS_JSON' não encontrado.")

    # --- Comandos (Corrigidos com a indentação correta) ---
    
    @app_commands.command(name="verificar", description="Verifica orçamentos com status pendentes.")
    @app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos no canal.")
    async def verificar(self, interaction: discord.Interaction, efemero: bool = True):
        if not self.worksheet:
            await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=efemero)
            return
        try:
            await interaction.response.defer(ephemeral=efemero)
            status_para_procurar = ["16 Cart.Tradução", "17 Cart.Original", "Embalar", "05 Imprimir"]
            todos_os_dados = self.worksheet.get_all_values()
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

    @app_commands.command(name="buscar_orcamento", description="Busca os detalhes de um orçamento pelo ID.")
    @app_commands.describe(id="O número do orçamento que você quer encontrar.")
    async def buscar_orcamento(self, interaction: discord.Interaction, id: str):
        if not self.worksheet:
            await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            todos_os_dados = self.worksheet.get_all_values()
            linha_encontrada = None
            
            for linha in todos_os_dados[1:]:
                if len(linha) > 3 and linha[3] == id:
                    linha_encontrada = linha
                    break
            
            if linha_encontrada:
                cliente = linha_encontrada[2]
                num_orcamento = linha_encontrada[3]
                qtd_docs = linha_encontrada[4]
                status = linha_encontrada[7]
                data_entrega_str = linha_encontrada[1]
                
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
    
    @app_commands.command(name="atrasados", description="Lista todos os projetos com data de entrega vencida.")
    @app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos.")
    async def atrasados(self, interaction: discord.Interaction, efemero: bool = True):
        if not self.worksheet:
            await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=efemero)
        
        try:
            status_finalizados = ["09 Pronto", "10 Entregue", "12 Cancelado"]
            hoje = datetime.now().date()
            todos_os_dados = self.worksheet.get_all_values()
            projetos_atrasados = []
            
            COLUNA_DATA_ENTREGA_IDX = 1
            COLUNA_ID_ORCAMENTO_IDX = 3
            COLUNA_CLIENTE_IDX = 2
            COLUNA_STATUS_IDX = 7
            
            for linha in todos_os_dados[1:]:
                try:
                    data_entrega_str = linha[COLUNA_DATA_ENTREGA_IDX]
                    status_da_linha = linha[COLUNA_STATUS_IDX]
                    
                    if status_da_linha in status_finalizados or not data_entrega_str:
                        continue
                        
                    data_entrega = datetime.strptime(data_entrega_str, '%d/%m/%Y').date()
                    
                    if data_entrega < hoje:
                        id_orcamento = linha[COLUNA_ID_ORCAMENTO_IDX]
                        nome_cliente = linha[COLUNA_CLIENTE_IDX]
                        projetos_atrasados.append(f"`{id_orcamento}` - {nome_cliente} (Venceu em: {data_entrega_str})")
                
                except (ValueError, IndexError):
                    continue
            
            if not projetos_atrasados:
                embed = discord.Embed(
                    title="✅ Nenhum Projeto Atrasado",
                    description="Ótima notícia! Todos os projetos estão em dia.",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=efemero)
                return
                
            embed = discord.Embed(
                title="🚨 Projetos Atrasados",
                description="Os seguintes projetos estão com a data de entrega vencida:",
                color=discord.Color.red()
            )
            
            lista_projetos_str = "\n".join(projetos_atrasados)
            if len(lista_projetos_str) > 4000:
                lista_projetos_str = lista_projetos_str[:4000] + "\n...(lista muito longa)"
            
            embed.description = lista_projetos_str
            
            await interaction.followup.send(embed=embed, ephemeral=efemero)
        
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao verificar os projetos atrasados: {e}", ephemeral=efemero)

    
    @app_commands.command(name="listar_status", description="Lista todos os orçamentos com um status específico.")
    @app_commands.describe(status="Escolha o status que você deseja listar.")
    # Cria a lista de opções para o usuário escolher
    @app_commands.choices(status=[
        app_commands.Choice(name="01 Scan", value="01 Scan"),
        app_commands.Choice(name="03 Tradução", value="03 Tradução"),
        app_commands.Choice(name="04 Revisão", value="04 Revisão"),
        app_commands.Choice(name="05 Imprimir", value="05 Imprimir"),
        app_commands.Choice(name="06 Numerar", value="06 Numerar"),
        app_commands.Choice(name="07 Assinar Digital", value="07 Assinar Digital"),
        app_commands.Choice(name="09 Pronto", value="09 Pronto"),
        app_commands.Choice(name="10 Entregue", value="10 Entregue"),
        app_commands.Choice(name="11 Enviar e-mail", value="11 Enviar e-mail"),
        app_commands.Choice(name="15 Aguardando doc", value="15 Aguardando doc"),
        app_commands.Choice(name="16 Cart.Tradução", value="16 Cart.Tradução"),
        app_commands.Choice(name="17 Cart. Original", value="17 Cart. Original")
    ])
    async def listar_status(self, interaction: discord.Interaction, status: str, efemero: bool = True):
        if not self.worksheet:
            await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=efemero)
            return

        await interaction.response.defer(ephemeral=efemero)

        try:
            todos_os_dados = self.worksheet.get_all_values()
            orcamentos_encontrados = []
            
            for linha in todos_os_dados[1:]: # Pula o cabeçalho
                try:
                    status_da_linha = linha[7] # Coluna H
                    # Compara o status da linha com o status escolhido pelo usuário
                    if status_da_linha == status:
                        id_orcamento = linha[3]   # Coluna D
                        nome_cliente = linha[2]   # Coluna C
                        orcamentos_encontrados.append(f"`{id_orcamento}` - {nome_cliente}")
                except IndexError:
                    continue

            if not orcamentos_encontrados:
                embed = discord.Embed(
                    title=f"Nenhum Projeto Encontrado",
                    description=f"Não há nenhum orçamento com o status `{status}` no momento.",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, ephemeral=efemero)
                return
            
            # Monta a resposta com os projetos encontrados
            embed = discord.Embed(
                title=f"Orçamentos com Status: '{status}'",
                color=discord.Color.blue()
            )
            
            lista_projetos_str = "\n".join(orcamentos_encontrados)
            if len(lista_projetos_str) > 4000:
                lista_projetos_str = lista_projetos_str[:4000] + "\n...(lista muito longa)"

            embed.description = lista_projetos_str
            
            await interaction.followup.send(embed=embed, ephemeral=efemero)

        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao listar os projetos: {e}", ephemeral=efemero)


    @app_commands.command(name="revisao_dia", description="Mostra todos os Orçamentos do dia com Status: 04 Revisão")
    @app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos.")
    async def revisao_dia(self, interaction: discord.Interaction, efemero: bool = True):
        if not self.worksheet:
            await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=efemero)
        
        try:
            hoje = datetime.now().date()
            orcamentos_do_dia = []
            status_revisao = "04 Revisão"
            todos_os_dados = self.worksheet.get_all_values()

            COLUNA_DATA_IDX = 1  # Coluna B
            COLUNA_ID_ORCAMENTO_IDX = 3
            COLUNA_CLIENTE_IDX = 2
            COLUNA_STATUS_IDX = 7
            
            for linha in todos_os_dados[1:]:
                try:
                    data_str = linha[COLUNA_DATA_IDX]
                    status_da_linha = linha[COLUNA_STATUS_IDX]
                    
                    if not data_str:
                        continue
                    
                    data_da_linha = datetime.strptime(data_str, '%d/%m/%Y').date()
                    
                    # Verifica se a data é hoje E se o status é '04 Revisão'
                    if data_da_linha == hoje and status_da_linha == status_revisao:
                        id_orcamento = linha[COLUNA_ID_ORCAMENTO_IDX]
                        nome_cliente = linha[COLUNA_CLIENTE_IDX]
                        orcamentos_do_dia.append(f"`{id_orcamento}` - {nome_cliente}")
                
                except (ValueError, IndexError):
                    continue
            
            if not orcamentos_do_dia:
                embed = discord.Embed(
                    title="✅ Nenhuma Revisão para Hoje",
                    description="Não há orçamentos com data de hoje e status '04 Revisão'.",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=efemero)
                return
            
            embed = discord.Embed(
                title="🗓️ Revisões de Hoje",
                description="Os seguintes orçamentos estão em revisão hoje:",
                color=discord.Color.blue()
            )
            
            lista_projetos_str = "\n".join(orcamentos_do_dia)
            embed.description = lista_projetos_str
            
            await interaction.followup.send(embed=embed, ephemeral=efemero)
        
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao verificar as revisões do dia: {e}", ephemeral=efemero)

# --- Função de Setup para Carregar o Cog ---
async def setup(bot):
    await bot.add_cog(SpreadsheetCommands(bot))

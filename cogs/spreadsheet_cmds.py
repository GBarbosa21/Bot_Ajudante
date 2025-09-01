import discord
from discord.ext import commands
from discord import app_commands
import gspread
import json
import os
from datetime import datetime

# --- Função Auxiliar de Formatação (Atualizada) ---
def formatar_data_br(data_str: str) -> str:
    """Tenta formatar uma string de data para o padrão dd/mm/YYYY."""
    if not data_str: return "N/A"
    try:
        # Adiciona o ano atual se a string for apenas dd/mm
        if len(data_str.strip()) <= 5:
            ano_atual = datetime.now().year
            data_completa_str = f"{data_str.strip()}/{ano_atual}"
            dt_obj = datetime.strptime(data_completa_str, '%d/%m/%Y')
            return dt_obj.strftime('%d/%m/%Y')
        else:
            # Tenta formatar a data completa se ela já tiver o ano
            dt_obj = datetime.strptime(data_str, '%d/%m/%Y')
            return dt_obj.strftime('%d/%m/%Y')
    except:
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
                spreadsheet = gc.open("@Status clientes 2025")
                self.worksheet = spreadsheet.worksheet("SET 25")
                print(f"Cog 'Spreadsheet': Conectado à planilha '{spreadsheet.title}'.")
            except Exception as e:
                print(f"Cog 'Spreadsheet': ERRO CRÍTICO ao conectar à planilha: {e}")
        else:
            print("Cog 'Spreadsheet': AVISO: Secret 'GOOGLE_CREDENTIALS_JSON' não encontrado.")

    # --- Comandos---
    @app_commands.command(name="verificar", description="Verifica orçamentos com status de trabalho pendentes.")
    @app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos no canal.")
    async def verificar(self, interaction: discord.Interaction, efemero: bool = True):
        if not self.worksheet:
            await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=efemero)
            return
        try:
            await interaction.response.defer(ephemeral=efemero)
            status_para_procurar = [
                "01 Escanear", "03 Traduzir", "04 Revisar", "05 Imprimir", 
                "07 Assinar Digitalmente", "08 Assinar e Imprimir", "10 Numerar", 
                "15 Cart. Tradução", "16 Cart. Original", "17 Conferência", 
                "18 Tradução Externa", "19 Embalar"
            ]
            todos_os_dados = self.worksheet.get_all_values()
            orcamentos_encontrados = {}
            for linha in todos_os_dados[1:]:
                try:
                    status_da_linha = linha[7].strip()
                    if status_da_linha in status_para_procurar:
                        id_orcamento = linha[3]
                        nome_cliente = linha[2]
                        if status_da_linha not in orcamentos_encontrados:
                            orcamentos_encontrados[status_da_linha] = []
                        if id_orcamento and nome_cliente:
                            linha_formatada = f"{id_orcamento} - {nome_cliente}"
                            orcamentos_encontrados[status_da_linha].append(linha_formatada)
                except IndexError:
                    continue
            
            if not orcamentos_encontrados:
                await interaction.followup.send("Nenhum orçamento encontrado com os status de verificação.", ephemeral=efemero)
                return
                
            resposta_texto = "📋 **Orçamentos com Status Ativo:**\n\n"
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
            # --- LISTA DE STATUS FINALIZADOS ATUALIZADA ---
            status_finalizados = ["09 Pronto", "11 Entregue", "12 Enviar e-mail", "20 Cancelado"]
            hoje = datetime.now().date()
            todos_os_dados = self.worksheet.get_all_values()
            projetos_atrasados = []
            
            for linha in todos_os_dados[1:]:
                try:
                    data_entrega_str = linha[1] # Coluna B
                    status_da_linha = linha[7].strip()
                    
                    if status_da_linha in status_finalizados or not data_entrega_str:
                        continue
                        
                    data_completa_str = f"{data_entrega_str.strip()}/{hoje.year}"
                    data_entrega = datetime.strptime(data_completa_str, '%d/%m/%Y').date()
                    
                    if data_entrega < hoje:
                        id_orcamento = linha[3]
                        nome_cliente = linha[2]
                        projetos_atrasados.append(f"`{id_orcamento}` - {nome_cliente} (Venceu em: {data_entrega_str})")
                
                except (ValueError, IndexError):
                    continue
            
            if not projetos_atrasados:
                embed = discord.Embed(title="✅ Nenhum Projeto Atrasado", description="Ótima notícia! Todos os projetos estão em dia.", color=discord.Color.green())
                await interaction.followup.send(embed=embed, ephemeral=efemero)
                return
                
            embed = discord.Embed(title="🚨 Projetos Atrasados", description="Os seguintes projetos estão com a data de entrega vencida:", color=discord.Color.red())
            
            lista_projetos_str = "\n".join(projetos_atrasados)
            embed.description = lista_projetos_str
            
            await interaction.followup.send(embed=embed, ephemeral=efemero)
        
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao verificar os projetos atrasados: {e}", ephemeral=efemero)
    
    @app_commands.command(name="listar_status", description="Lista todos os orçamentos com um status específico.")
    @app_commands.describe(status="Escolha o status que você deseja listar.")
    # Cria a lista de opções para o usuário escolher
    @app_commands.choices(status=[
        app_commands.Choice(name="01 Escanear", value="01 Escanear"),
        app_commands.Choice(name="03 Traduzir", value="03 Traduzir"),
        app_commands.Choice(name="04 Revisar", value="04 Revisar"),
        app_commands.Choice(name="05 Imprimir", value="05 Imprimir"),
        app_commands.Choice(name="07 Assinar Digitalmente", value="07 Assinar Digitalmente"),
        app_commands.Choice(name="08 Assinar e Imprimir", value="08 Assinar e Imprimir"),
        app_commands.Choice(name="09 Pronto", value="09 Pronto"),
        app_commands.Choice(name="10 Numerar", value="10 Numerar"),
        app_commands.Choice(name="11 Entregue", value="11 Entregue"),
        app_commands.Choice(name="12 Enviar e-mail", value="12 Enviar e-mail"),
        app_commands.Choice(name="13 Stand by", value="13 Stand by"),
        app_commands.Choice(name="14 Aguardando Orig.", value="14 Aguardando Orig."),
        app_commands.Choice(name="15 Cart.Tradução", value="15 Cart.Tradução"),
        app_commands.Choice(name="16 Cart. Original", value="16 Cart. Original"),
        app_commands.Choice(name="17 Conferência", value="17 Conferência"),
        app_commands.Choice(name="18 Tradução Externa", value="18 Tradução Externa"),
        app_commands.Choice(name="19 Embalar", value="19 Embalar"),
        app_commands.Choice(name="20 Cancelado", value="20 Cancelado")
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


    @app_commands.command(name="revisao_dia", description="Mostra todos os orçamentos do dia com Status: 04 Revisão")
    @app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos.")
    async def revisao_dia(self, interaction: discord.Interaction, efemero: bool = True):
        if not self.worksheet:
            await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=efemero)
        
        try:
            hoje = datetime.now().date()
            orcamentos_do_dia = []
            status_revisao_esperado = "04 Revisão"
            todos_os_dados = self.worksheet.get_all_values()

            COLUNA_DATA_IDX = 1
            COLUNA_ID_ORCAMENTO_IDX = 3
            COLUNA_CLIENTE_IDX = 2
            COLUNA_STATUS_IDX = 7
            
            for linha in todos_os_dados[1:]:
                try:
                    data_str = linha[COLUNA_DATA_IDX]
                    status_da_linha = linha[COLUNA_STATUS_IDX].strip()
                    
                    if not data_str:
                        continue
                    
                    data_completa_str = f"{data_str.strip()}/{hoje.year}"
                    data_da_linha = datetime.strptime(data_completa_str, '%d/%m/%Y').date()
                    
                    if data_da_linha == hoje and status_da_linha == status_revisao_esperado:
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

    @app_commands.command(name="traducoes_ate", description="Lista projetos em tradução com entrega até uma data específica.")
    @app_commands.describe(data="A data limite no formato DD/MM (ex: 28/08)",efemero="Escolha 'Falso' para mostrar a resposta para todos.")
    async def traducoes_ate(self, interaction: discord.Interaction, data: str, efemero: bool = True):
        if not self.worksheet:
            await interaction.response.send_message("Desculpe, a conexão com a planilha não foi estabelecida.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=efemero)

        try:
            # 1. Valida e formata a data de entrada do usuário
            ano_atual = datetime.now().year
            data_limite_str = f"{data.strip()}/{ano_atual}"
            try:
                data_limite = datetime.strptime(data_limite_str, '%d/%m/%Y').date()
            except ValueError:
                await interaction.followup.send(f"Formato de data inválido: '{data}'. Por favor, use `DD/MM`.", ephemeral=True)
                return

            projetos_encontrados = []
            status_traducao = "03 Traduzir"
            todos_os_dados = self.worksheet.get_all_values()

            for linha in todos_os_dados[1:]:
                try:
                    data_entrega_str = linha[1] # Coluna B
                    status_da_linha = linha[7].strip() # Coluna H
                    
                    if not data_entrega_str or status_da_linha != status_traducao:
                        continue
                    
                    # Formata a data da planilha para comparação
                    data_entrega_completa_str = f"{data_entrega_str.strip()}/{ano_atual}"
                    data_entrega = datetime.strptime(data_entrega_completa_str, '%d/%m/%Y').date()
                    
                    # A LÓGICA PRINCIPAL: verifica se a entrega é ANTES OU IGUAL à data limite
                    if data_entrega <= data_limite:
                        id_orcamento = linha[3]
                        nome_cliente = linha[2]
                        projetos_encontrados.append(f"`{id_orcamento}` - {nome_cliente} (Entrega: {data_entrega_str})")
                
                except (ValueError, IndexError):
                    continue
            
            if not projetos_encontrados:
                embed = discord.Embed(
                    title=f"✅ Nenhuma Tradução Encontrada",
                    description=f"Não há projetos com status '{status_traducao}' com entrega até **{data}**.",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed, ephemeral=efemero)
                return
            
            embed = discord.Embed(
                title=f"📝 Traduções com Entrega até {data}",
                description=f"Os seguintes orçamentos com status '{status_traducao}' têm entrega até a data informada:",
                color=discord.Color.blue()
            )
            
            lista_projetos_str = "\n".join(projetos_encontrados)
            embed.description = lista_projetos_str
            
            await interaction.followup.send(embed=embed, ephemeral=efemero)

        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao buscar as traduções: {e}", ephemeral=efemero)


# --- Função de Setup para Carregar o Cog ---
async def setup(bot):
    await bot.add_cog(SpreadsheetCommands(bot))

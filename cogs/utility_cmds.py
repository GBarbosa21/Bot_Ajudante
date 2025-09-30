import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
import random

# --- Classe do Cog ---
class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Lista de piadas para o comando /piada
        self.lista_de_piadas = [
            "O que o pato falou para a pata? Vem Quá!",
            "Por que a velhinha não usa relógio? Porque ela é uma sem hora.",
            "Qual é o cúmulo da sorte? Ser atropelado por uma ambulância.",
            "O que um cromossomo disse para o outro? Cromossomos felizes!",
            "Sabe como o Batman faz para entrar na bat-caverna? Ele bat-palma.",
            "Por que o jacaré tirou o filho da escola? Porque ele réptil de ano.",
            "Qual o rei dos queijos? O Reiqueijão.",
            "O que a impressora disse para a outra? Essa folha é sua ou é impressão minha?",
            "O que o tomate foi fazer no banco? Foi tirar o extrato.",
            "Por que a planta não responde? Porque ela é clorofila da puta."
        ]

    # --- Funções Auxiliares ---
    def parse_time(self, time_str: str) -> int | None:
        """Converte uma string de tempo (ex: 10s, 5m, 1h) para segundos."""
        match = re.match(r"(\d+)([smh])$", time_str.lower())
        if not match:
            return None
        value, unit = match.groups()
        value = int(value)
        if unit == 's': return value
        if unit == 'm': return value * 60
        if unit == 'h': return value * 3600
        return None

    # --- Comandos ---
    @app_commands.command(name="ajuda", description="Mostra uma lista de todos os comandos disponíveis.")
    async def ajuda(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Ajuda do Bot Ajudante",
            description="Aqui está uma lista de todos os comandos que eu entendo, organizados por módulo:",
            color=discord.Color.blue()
        )

        # Abordagem mais robusta: iterar por cada Cog carregado no bot
        for cog_name in self.bot.cogs:
            cog = self.bot.get_cog(cog_name)
            
            # Pega apenas os comandos de barra (app_commands) deste cog
            commands_in_cog = [cmd for cmd in cog.get_app_commands() if isinstance(cmd, app_commands.Command)]
            
            if commands_in_cog: # Só adiciona a seção se o Cog tiver comandos de barra
                
                # Monta a string com a lista de comandos para este Cog
                command_list_str = ""
                for command in commands_in_cog:
                    command_list_str += f"**`/{command.name}`** - {command.description}\n"
                
                # Adiciona um campo para o Cog e sua lista de comandos
                embed.add_field(name=f"⚙️ Módulo: {cog_name}", value=command_list_str, inline=False)

        embed.set_footer(text="Use os comandos em um canal ou na minha mensagem direta.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="lembrete", description="Agenda um lembrete para você.")
    @app_commands.describe(
        tempo="O tempo até o lembrete (ex: 10s, 5m, 1h).",
        mensagem="A mensagem que você quer receber."
    )
    async def lembrete(self, interaction: discord.Interaction, tempo: str, mensagem: str):
        segundos = self.parse_time(tempo)
        if segundos is None:
            await interaction.response.send_message(f"Formato de tempo inválido: '{tempo}'. Use 's', 'm', ou 'h'.", ephemeral=True)
            return
            
        await interaction.response.send_message(f"Ok! Lembrete agendado para daqui a **{tempo}**.", ephemeral=True)
        await asyncio.sleep(segundos)
        
        try:
            await interaction.user.send(f"⏰ **Lembrete:** {mensagem}")
        except discord.Forbidden:
            await interaction.followup.send(f"⏰ {interaction.user.mention}, seu lembrete: {mensagem}", ephemeral=False)

    @app_commands.command(name="ponto", description="Agenda um lembrete de 1 hora para bater o ponto.")
    async def ponto(self, interaction: discord.Interaction):
        segundos = 3600 # 1 hora
        mensagem = "Lembre de bater o ponto"
        await interaction.response.send_message("Ok! Agendei seu lembrete para bater o ponto daqui a **1 hora**.", ephemeral=True)
        await asyncio.sleep(segundos)
        
        try:
            await interaction.user.send(f"⏰ **Lembrete:** {mensagem}")
        except discord.Forbidden:
            await interaction.followup.send(f"⏰ {interaction.user.mention}, seu lembrete: {mensagem}", ephemeral=False)

    @app_commands.command(name="status_bot", description="Verifica a saúde e as conexões do bot.")
    @app_commands.describe(efemero="Escolha 'Falso' para mostrar a resposta para todos.")
    async def status_bot(self, interaction: discord.Interaction, efemero: bool = True):
        await interaction.response.defer(ephemeral=efemero)

        # 1. Verifica a latência com o Discord
        latencia_ms = round(self.bot.latency * 1000)
        
        # 2. Verifica a conexão com a Planilha Google
        status_planilha = "Com Falha ❌"
        # Acessa o outro Cog para verificar o status da planilha
        spreadsheet_cog = self.bot.get_cog('SpreadsheetCommands')
        if spreadsheet_cog and spreadsheet_cog.worksheet:
            try:
                # Tenta uma operação de leitura rápida e inofensiva
                spreadsheet_cog.worksheet.cell(1, 1).value
                status_planilha = "Ativa e Funcionando ✅"
            except Exception as e:
                print(f"Erro no health check da planilha: {e}")
                status_planilha = f"Com Falha ❌ (Verificar Logs)"
        else:
             status_planilha = "Desativada (Secret não encontrada) ⚠️"

        # 3. Monta a resposta
        embed = discord.Embed(
            title="Status do Ajudante",
            color=discord.Color.dark_grey()
        )
        embed.add_field(name="Status Geral", value="Online ✅", inline=False)
        embed.add_field(name="Latência com o Discord", value=f"{latencia_ms}ms ⚡", inline=False)
        embed.add_field(name="Conexão com Google Sheets", value=status_planilha, inline=False)
        
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        embed.set_footer(text=f"Verificado em: {timestamp}")
        
        await interaction.followup.send(embed=embed, ephemeral=efemero)

    @app_commands.command(name="avaliacao", description="Envia o formulário de avaliação de atendimento.")
    async def avaliacao(self, interaction: discord.Interaction):
        # O texto do formulário
        texto_formulario = """
            **Avaliação Rápida de Atendimento de Suporte de TI**
            
            A sua opinião é essencial para melhorarmos nossos serviços. Por favor, dedique um minuto para avaliar o suporte que você recebeu.
            
            **Nº do Chamado/Ticket:** _______________
            **Data do Atendimento:** ______/______/______
            
            **Instruções:** Para cada pergunta abaixo, por favor, selecione uma nota de 1 a 5.
            *1 = Muito Insatisfeito | 2 = Insatisfeito | 3 = Neutro | 4 = Satisfeito | 5 = Muito Satisfeito*
            ---
            **1. Cordialidade e profissionalismo do técnico:**
            ( ) 1   ( ) 2   ( ) 3   ( ) 4   ( ) 5
            
            **2. Clareza na comunicação e nas explicações:**
            ( ) 1   ( ) 2   ( ) 3   ( ) 4   ( ) 5
            
            **3. Tempo para a resolução do seu problema:**
            ( ) 1   ( ) 2   ( ) 3   ( ) 4   ( ) 5
            
            **4. A solução apresentada foi eficaz?**
            ( ) 1   ( ) 2   ( ) 3   ( ) 4   ( ) 5
            
            **5. Qual seu nível de satisfação GERAL com o atendimento?**
            ( ) 1   ( ) 2   ( ) 3   ( ) 4   ( ) 5
            ---
            **Comentários ou sugestões (opcional):**
            *O que mais gostou no atendimento? O que podemos melhorar?*
            \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_
            
            Obrigado pela sua colaboração!
            """
        
        # Cria um Embed para a mensagem ficar mais organizada
        embed = discord.Embed(
            description=texto_formulario,
            color=discord.Color.from_rgb(0, 153, 255) # Um tom de azul
        )
        
        # Envia a resposta no canal
        await interaction.response.send_message(embed=embed)

    @app_-commands.command(name="piada", description="Eu te conto uma piada aleatória.")
    async def piada(self, interaction: discord.Interaction):
        """Escolhe e envia uma piada aleatória da lista."""
        
        # Escolhe uma piada da lista de forma aleatória
        piada_escolhida = random.choice(self.lista_de_piadas)
        
        # Envia a piada no canal
        await interaction.response.send_message(f"😂 ... {piada_escolhida}")
    
    @commands.command()
    async def ping(self, ctx):
        await ctx.send('Pong!')

    @commands.command()
    async def pong(self, ctx):
        await ctx.send('ping')

    @commands.command()
    async def enlouqueci(self, ctx):
        await ctx.send('FORAM VOCÊS!')

# --- Função de Setup para Carregar o Cog ---
async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))

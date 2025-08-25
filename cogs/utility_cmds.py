import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re

# --- Classe do Cog ---
class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
    @app_commands.command(name="ajuda", description="Mostra uma lista de todos os comandos.")
    async def ajuda(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Ajuda do Bot",
            description="Aqui está uma lista de todos os comandos que eu entendo:",
            color=discord.Color.blue()
        )
        # Pega todos os comandos de barra registrados na árvore de comandos do bot
        for command in self.bot.tree.get_commands():
            embed.add_field(name=f"/{command.name}", value=command.description, inline=False)
        
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


    @commands.command()
    async def ping(self, ctx):
        await ctx.send('Pong!')

    @commands.command()
    async def pong(self, ctx):
        await ctx.send('ping')


# --- Função de Setup para Carregar o Cog ---
async def setup(bot):
    await bot.add_cog(UtilityCommands(bot))

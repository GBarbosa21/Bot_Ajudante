# Bot Ajudante para Google Sheets & Discord

![Python](https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python)
![discord.py](https://img.shields.io/badge/discord.py-2.3-7289DA?style=for-the-badge&logo=discord)
![gspread](https://img.shields.io/badge/gspread-5.12-0F9D58?style=for-the-badge)

Um bot multifuncional para Discord, escrito em Python, projetado para se conectar a uma Planilha Google e servir como uma poderosa ferramenta de consulta e produtividade para a equipe. O bot é capaz de ler, filtrar e apresentar dados da planilha diretamente no Discord através de comandos simples.

## ✨ Funcionalidades

O bot é organizado em módulos ("Cogs") para facilitar a manutenção.

### 📋 Comandos da Planilha
-   **/verificar:** Varre a planilha e lista todos os orçamentos que estão em status de trabalho (Impressão, Embalar, etc.).
-   **/buscar\_orcamento `id`:** Busca um orçamento específico pelo seu número e exibe um resumo completo dos seus dados (Cliente, Status, Data de Entrega, etc.).
-   **/atrasados:** Lista todos os projetos cuja data de entrega já passou e que ainda não foram concluídos, servindo como um alerta de prioridades.
-   **/listar\_status `status`:** Lista todos os orçamentos que correspondem a um status específico, selecionado de um menu de opções.
-   **/revisao\_dia:** Um comando especializado que filtra e mostra todos os projetos com status "04 Revisão" cuja data na planilha corresponde ao dia atual.
-   **!ler `célula`:** Lê e retorna o valor de uma célula específica (ex: `!ler A1`).

### 🛠️ Comandos de Utilidade
-   **/ajuda:** Exibe uma lista completa e dinâmica de todos os comandos de barra disponíveis, organizada por categoria.
-   **/lembrete `tempo` `mensagem`:** Agenda um lembrete pessoal que o bot envia por DM após o tempo especificado (ex: `10s`, `30m`, `1h`).
-   **/ponto:** Um atalho que agenda um lembrete fixo de 1 hora para "Lembre de bater o ponto".
-   **/status\_bot:** Realiza um diagnóstico completo, verificando a latência com o Discord e o status da conexão com a API do Google Sheets.

## 📂 Estrutura do Projeto

O bot utiliza o padrão de Cogs para uma organização de código limpa e escalável.
</br>/BotAjudante/<br>
├── main.py                 # Ponto de entrada: carrega secrets, cogs e inicia o bot. </br>
├── requirements.txt        # Lista de dependências Python.<br>
├── .env.example            # Arquivo de exemplo para as variáveis de ambiente.<br>
├── .gitignore              # Ignora arquivos sensíveis e desnecessários.<br>
└── /cogs/<br>
├── spreadsheet_cmds.py # Cog com os comandos que interagem com a planilha.<br>
└── utility_cmds.py     # Cog com os comandos de utilidade e ajuda.<br>


## 🚀 Instalação e Configuração

Siga os passos abaixo para rodar o bot em seu próprio ambiente.

### Pré-requisitos
-   Python 3.8+
-   Uma conta no Discord com permissão para criar aplicações.
-   Uma conta no Google Cloud para configurar as APIs.

### Passo 1: Configuração do Discord
1.  Vá ao [Portal de Desenvolvedores do Discord](https://discord.com/developers/applications).
2.  Crie uma **"New Application"**.
3.  Vá para a aba **"Bot"**, clique em **"Add Bot"** e copie o **Token** (`DISCORD_BOT_TOKEN`).
4.  Nesta mesma página, ative a **"Message Content Intent"** em "Privileged Gateway Intents".
5.  Vá para **OAuth2 > URL Generator**, selecione os escopos `bot` e `applications.commands` e conceda as permissões necessárias (como "Send Messages"). Use a URL gerada para convidar o bot ao seu servidor.

### Passo 2: Configuração do Google Cloud
1.  Crie um projeto no [Console do Google Cloud](https://console.cloud.google.com/).
2.  Ative a **"Google Drive API"** e a **"Google Sheets API"**.
3.  Crie uma **Conta de Serviço (Service Account)** e gere uma **chave JSON** para ela. Um arquivo `.json` será baixado.

### Passo 3: Configuração da Planilha
1.  Abra o arquivo `.json` baixado e copie o `"client_email"`.
2.  Na sua Planilha Google, clique em **Compartilhar** e cole o `client_email`, dando a ele permissão de **Editor**.

### Passo 4: Configuração do Projeto
1.  Clone este repositório: `git clone [URL_DO_SEU_REPOSITORIO]`
2.  Crie um ambiente virtual: `python -m venv venv` e ative-o.
3.  Instale as dependências: `pip install -r requirements.txt`
4.  Crie um arquivo chamado `.env` na raiz do projeto. Ele deve conter:
    ```
    # Token do seu bot do Discord
    DISCORD_BOT_TOKEN="COLE_SEU_TOKEN_AQUI"

    # Conteúdo completo do seu arquivo de chave .json do Google em uma única linha
    GOOGLE_CREDENTIALS_JSON='COLE_O_CONTEUDO_DO_SEU_JSON_AQUI'
    ```
5.  Execute o bot localmente: `python main.py`

### Passo 5: Deploy 24/7 (Exemplo com Render)
1.  Crie um novo serviço no Render do tipo **`Background Worker`** (Plano Gratuito).
2.  Conecte seu repositório do GitHub.
3.  Configure os comandos:
    -   **Build Command:** `pip install -r requirements.txt`
    -   **Start Command:** `python main.py`
4.  Na seção "Environment", adicione as mesmas variáveis do seu arquivo `.env` (`DISCORD_BOT_TOKEN` e `GOOGLE_CREDENTIALS_JSON`).

## ⚖️ Licença
Distribuído sob a Licença MIT.

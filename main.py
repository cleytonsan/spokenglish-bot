import os
import logging
import discord
from dotenv import load_dotenv
from discord.ext import commands
import google.generativeai as genai
from gtts import gTTS
from flask import Flask, request
import asyncio # Mantenha asyncio
import sys # Para graceful shutdown

# Carrega variáveis de ambiente do .env
load_dotenv()

# ---------------------- LOGGING PROFISSIONAL ----------------------
# Configura o logging para exibir no console (stdout)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)] # Direciona para stdout
)
logger = logging.getLogger(__name__) # Use um logger específico para o módulo

# ---------------------- VERIFICAÇÃO E CONFIGURAÇÕES ----------------------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Assegura que as chaves estão configuradas
if not GEMINI_API_KEY:
    logger.critical("Erro FATAL: GEMINI_API_KEY não configurada. O bot não funcionará.")
    sys.exit(1) # Sai imediatamente com código de erro

if not DISCORD_BOT_TOKEN:
    logger.critical("Erro FATAL: DISCORD_BOT_TOKEN não configurado. O bot não funcionará.")
    sys.exit(1) # Sai imediatamente com código de erro

# Configura a API do Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Configura as intenções do Discord Bot
intents = discord.Intents.default()
intents.message_content = True # Necessário para ler o conteúdo das mensagens

bot = commands.Bot(command_prefix='!', intents=intents)

# ---------------------- EVENTO DE INICIALIZAÇÃO DO BOT ----------------------
@bot.event
async def on_ready():
    logger.info(f'spokEnglish Bot conectado como {bot.user} (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="Aprendendo Inglês"))
    logger.info("Bot está pronto e online.")

# ---------------------- COMANDO: !traduzir ----------------------
@bot.command(name='traduzir', help='Gera uma lição completa para uma palavra, phrasal verb ou gíria.')
async def translate_text(ctx, *, text_to_translate: str):
    if not text_to_translate:
        await ctx.send("Por favor, forneça uma palavra ou frase. Ex: `!traduzir figure out`")
        return

    await ctx.send(f"Gerando lição completa para '{text_to_translate}'...")
    logger.info(f"Comando !traduzir invocado para: '{text_to_translate}'")

    prompt = f"""
    Gere uma lição completa para a seguinte palavra ou expressão em inglês: "**{text_to_translate}**".

    Inclua:
    1. **Palavra/Frase:** [negrito]
    2. **Significado:** [português]
    3. **Sinônimos/Expressões Similares:** [mínimo 3]
    4. **Explicação Contextual/Mapa Mental**
    5. **Exemplos:** com tradução
    """

    try:
        response = await asyncio.to_thread(model.generate_content, prompt) # Garante que a chamada à API Gemini não bloqueie o loop de eventos
        lesson_content = response.text.strip()

        embed = discord.Embed(
            title=f"📚 Lição: **{text_to_translate}**",
            description=lesson_content,
            color=0x4B0082 # Roxo vibrante
        )
        embed.set_footer(text="Gerado por spokEnglish via Gemini AI")
        await ctx.send(embed=embed)
        logger.info(f"Lição gerada e enviada com sucesso para: '{text_to_translate}'")

    except Exception as e:
        logger.error(f"Erro ao gerar lição com Gemini para '{text_to_translate}': {e}", exc_info=True) # exc_info para traceback completo
        await ctx.send("Erro ao gerar a lição. Tente novamente mais tarde.")

# ---------------------- COMANDO: !pronunciar ----------------------
@bot.command(name='pronunciar', help='Gera áudio com a pronúncia de uma palavra ou frase.')
async def pronounce_text(ctx, *, text_to_pronounce: str):
    if not text_to_pronounce:
        await ctx.send("Forneça uma palavra ou frase. Ex: `!pronunciar hello`")
        return

    await ctx.send(f"Gerando áudio para '{text_to_pronounce}'...")
    logger.info(f"Comando !pronunciar invocado para: '{text_to_pronounce}'")

    try:
        # Nome do arquivo temporário com hash para evitar colisões
        import hashlib
        file_hash = hashlib.md5(text_to_pronounce.encode()).hexdigest()
        audio_file_name = f"pronuncia_{file_hash}.mp3"

        tts = gTTS(text=text_to_pronounce, lang='en', slow=False)
        await asyncio.to_thread(tts.save, audio_file_name) # Executa em um thread para não bloquear o loop

        # Verifica se o arquivo foi criado antes de tentar enviar
        if os.path.exists(audio_file_name):
            await ctx.send(file=discord.File(audio_file_name))
            await asyncio.to_thread(os.remove, audio_file_name) # Remove em um thread
            logger.info(f"Áudio gerado e enviado com sucesso para: '{text_to_pronounce}'")
        else:
            raise FileNotFoundError(f"Arquivo de áudio '{audio_file_name}' não foi criado.")

    except Exception as e:
        logger.error(f"Erro ao gerar áudio com gTTS para '{text_to_pronounce}': {e}", exc_info=True)
        await ctx.send("Erro ao gerar o áudio. Tente novamente mais tarde.")
        # Tenta remover o arquivo mesmo se houver erro no envio, se existir
        if os.path.exists(audio_file_name):
            try:
                await asyncio.to_thread(os.remove, audio_file_name)
            except Exception as cleanup_e:
                logger.warning(f"Erro ao tentar limpar arquivo de áudio '{audio_file_name}': {cleanup_e}")


# ---------------------- KEEP-ALIVE COM FLASK (ASSÍNCRONO) ----------------------
app = Flask(__name__) # Use __name__ para o nome do módulo

@app.route('/')
def home():
    logger.info("Requisição GET / recebida.")
    return "✅ spokEnglish Bot está vivo!"

@app.route('/status')
def status():
    logger.info("Requisição GET /status recebida.")
    return "✅ Status: Bot funcional e online!", 200

# Endpoint para depuração de variáveis de ambiente (CUIDADO EM PROD!)
@app.route('/env')
def show_env():
    if request.args.get('debug_key') == os.getenv("DEBUG_ACCESS_KEY"): # Adicione uma chave para acesso
        env_vars = "\n".join([f"{key} = {value}" for key, value in os.environ.items()])
        return f"<pre>{env_vars}</pre>", 200
    return "Acesso Negado", 403

# Função para iniciar o bot Discord dentro do loop de eventos do Flask
async def start_discord_bot():
    try:
        await bot.start(DISCORD_BOT_TOKEN) # Usa bot.start() em vez de bot.run()
    except discord.LoginFailure:
        logger.critical("Erro: Token inválido. Verifique o DISCORD_BOT_TOKEN.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Ocorreu um erro FATAL ao iniciar o bot: {e}", exc_info=True)
        sys.exit(1)

# ---------------------- EXECUÇÃO PRINCIPAL ----------------------
if __name__ == "__main__":
    # Inicia o bot Discord em segundo plano no loop de eventos principal
    # Esta é a chave para rodar Flask e Discord juntos de forma assíncrona
    # A Railway vai esperar que a porta 8080 (ou $PORT) seja bindada.
    # Uvicorn é um bom servidor assíncrono para apps ASGI/WSGI.
    # No entanto, para simplicidade e compatibilidade com Flask puro, podemos usar o servidor de desenvolvimento para o keep-alive
    # OU usar Gunicorn/Waitress (para WSGI) e iniciar o bot via Thread ou asyncio.
    # A maneira mais limpa para Railway é:

    # 1. Start do bot em uma tarefa asyncio
    asyncio.create_task(start_discord_bot())

    # 2. Start do servidor Flask (bloqueante)
    # A porta padrão da Railway é $PORT, que geralmente é 8080
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Iniciando servidor Flask na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=False) # debug=False em produção

    # Nota: Com app.run(), o código abaixo dele só será executado quando o servidor Flask parar.
    # O bot Discord estará rodando no loop de eventos assíncrono criado por asyncio.create_task().
    

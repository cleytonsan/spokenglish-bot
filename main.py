import os
import logging
import discord
from dotenv import load_dotenv
from discord.ext import commands
import google.generativeai as genai
from gtts import gTTS
from flask import Flask, request
import asyncio
import sys
import hashlib

# Carrega variáveis de ambiente
load_dotenv()

# ---------------------- LOGGING ----------------------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ---------------------- CONFIGURAÇÕES ----------------------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.critical("Erro FATAL: GEMINI_API_KEY não configurada.")
    sys.exit(1)

if not DISCORD_BOT_TOKEN:
    logger.critical("Erro FATAL: DISCORD_BOT_TOKEN não configurado.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'spokEnglish Bot conectado como {bot.user} (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="Aprendendo Inglês"))

@bot.command(name='traduzir', help='Gera uma lição completa para uma palavra ou expressão.')
async def translate_text(ctx, *, text_to_translate: str):
    if not text_to_translate:
        await ctx.send("Forneça uma palavra. Ex: `!traduzir figure out`")
        return

    await ctx.send(f"Gerando lição para '{text_to_translate}'...")
    logger.info(f"Traduzindo: {text_to_translate}")

    prompt = f"""
    Gere uma lição completa para: "**{text_to_translate}**".
    Inclua:
    1. Palavra/Frase
    2. Significado
    3. Sinônimos
    4. Mapa mental / contexto
    5. Exemplos com tradução
    """

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        lesson_content = response.text.strip()

        embed = discord.Embed(
            title=f"📚 Lição: **{text_to_translate}**",
            description=lesson_content,
            color=0x4B0082
        )
        embed.set_footer(text="Gerado por spokEnglish via Gemini AI")
        await ctx.send(embed=embed)
    except Exception as e:
        logger.error(f"Erro com Gemini: {e}", exc_info=True)
        await ctx.send("Erro ao gerar a lição. Tente novamente mais tarde.")

@bot.command(name='pronunciar', help='Gera áudio com a pronúncia.')
async def pronounce_text(ctx, *, text_to_pronounce: str):
    if not text_to_pronounce:
        await ctx.send("Exemplo: `!pronunciar hello`")
        return

    await ctx.send(f"Gerando áudio para '{text_to_pronounce}'...")
    logger.info(f"Pronunciando: {text_to_pronounce}")

    try:
        file_hash = hashlib.md5(text_to_pronounce.encode()).hexdigest()
        audio_file_name = f"pronuncia_{file_hash}.mp3"

        tts = gTTS(text=text_to_pronounce, lang='en', slow=False)
        await asyncio.to_thread(tts.save, audio_file_name)

        if os.path.exists(audio_file_name):
            await ctx.send(file=discord.File(audio_file_name))
            await asyncio.to_thread(os.remove, audio_file_name)
        else:
            raise FileNotFoundError(f"Arquivo não criado: {audio_file_name}")
    except Exception as e:
        logger.error(f"Erro ao gerar áudio: {e}", exc_info=True)
        await ctx.send("Erro ao gerar o áudio.")
        if os.path.exists(audio_file_name):
            await asyncio.to_thread(os.remove, audio_file_name)

# ---------------------- FLASK (keep-alive) ----------------------
app = Flask(__name__)

@app.route('/')
def home():
    logger.info("GET / recebida.")
    return "✅ spokEnglish Bot está vivo!"

@app.route('/status')
def status():
    logger.info("GET /status recebida.")
    return "✅ Status: Bot funcional e online!", 200

@app.route('/env')
def show_env():
    if request.args.get('debug_key') == os.getenv("DEBUG_ACCESS_KEY"):
        return f"<pre>{os.environ}</pre>", 200
    return "Acesso Negado", 403

# ---------------------- INÍCIO DO BOT + FLASK ----------------------
def start_async_bot():
    loop = asyncio.get_event_loop()
    loop.create_task(start_discord_bot())

async def start_discord_bot():
    try:
        logger.info("Iniciando bot do Discord...")
        await bot.start(DISCORD_BOT_TOKEN)
    except discord.LoginFailure:
        logger.critical("Token inválido.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Erro ao iniciar o bot: {e}", exc_info=True)
        sys.exit(1)

start_async_bot()  # Importante para o Gunicorn iniciar o bot

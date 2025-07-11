import os
import logging
import discord
from dotenv import load_dotenv
load_dotenv()
from discord.ext import commands
import google.generativeai as genai
from gtts import gTTS
from flask import Flask
from threading import Thread
import asyncio

print("\n[DEBUG] Variáveis de ambiente disponíveis no container Railway:")
for key, value in os.environ.items():
    print(f"{key} = {value}")
print("\n--- Fim das variáveis ---\n")

# ---------------------- LOGGING PROFISSIONAL ----------------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# ---------------------- CONFIGURAÇÕES ----------------------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"[DEBUG] Variável GEMINI_API_KEY: {GEMINI_API_KEY}")

if not GEMINI_API_KEY:
    logging.error("Erro: GEMINI_API_KEY não configurada. O bot não funcionará.")
    exit(1)

if not DISCORD_BOT_TOKEN:
    logging.error("Erro: DISCORD_BOT_TOKEN não configurado. O bot não funcionará.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ---------------------- EVENTO DE INICIALIZAÇÃO ----------------------
@bot.event
async def on_ready():
    logging.info(f'spokEnglish Bot conectado como {bot.user} (ID: {bot.user.id})')
    await bot.change_presence(activity=discord.Game(name="Aprendendo Inglês"))

# ---------------------- COMANDO: !traduzir ----------------------
@bot.command(name='traduzir', help='Gera uma lição completa para uma palavra, phrasal verb ou gíria.')
async def translate_text(ctx, *, text_to_translate: str):
    if not text_to_translate:
        await ctx.send("Por favor, forneça uma palavra ou frase. Ex: `!traduzir figure out`")
        return

    await ctx.send(f"Gerando lição completa para '{text_to_translate}'...")

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
        response = model.generate_content(prompt)
        lesson_content = response.text.strip()

        embed = discord.Embed(
            title=f"📚 Lição: **{text_to_translate}**",
            description=lesson_content,
            color=0x4B0082
        )
        embed.set_footer(text="Gerado por spokEnglish via Gemini AI")
        await ctx.send(embed=embed)

    except Exception as e:
        logging.error(f"Erro ao gerar lição com Gemini: {e}")
        await ctx.send("Erro ao gerar a lição. Tente novamente mais tarde.")

# ---------------------- COMANDO: !pronunciar ----------------------
@bot.command(name='pronunciar', help='Gera áudio com a pronúncia de uma palavra ou frase.')
async def pronounce_text(ctx, *, text_to_pronounce: str):
    if not text_to_pronounce:
        await ctx.send("Forneça uma palavra ou frase. Ex: `!pronunciar hello`")
        return

    await ctx.send(f"Gerando áudio para '{text_to_pronounce}'...")

    try:
        audio_file_name = f"pronuncia_{text_to_pronounce.replace(' ', '_').lower()}.mp3"
        tts = gTTS(text=text_to_pronounce, lang='en', slow=False)
        await asyncio.to_thread(tts.save, audio_file_name)
        await ctx.send(file=discord.File(audio_file_name))
        await asyncio.to_thread(os.remove, audio_file_name)

    except Exception as e:
        logging.error(f"Erro ao gerar áudio com gTTS: {e}")
        await ctx.send("Erro ao gerar o áudio. Tente novamente mais tarde.")

# ---------------------- KEEP-ALIVE COM FLASK ----------------------
app = Flask('')

@app.route('/')
def home():
    return "✅ spokEnglish Bot está vivo!"

@app.route('/status')
def status():
    return "✅ Status: Bot funcional e online!", 200

def run_flask_app():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server = Thread(target=run_flask_app)
    server.start()

# ---------------------- EXECUÇÃO PRINCIPAL ----------------------
if __name__ == "__main__":
    keep_alive()
    try:
        bot.run(DISCORD_BOT_TOKEN)
    except discord.LoginFailure:
        logging.error("Erro: Token inválido. Verifique o DISCORD_BOT_TOKEN.")
    except Exception as e:
        logging.error(f"Ocorreu um erro ao iniciar o bot: {e}")

import discord
from discord.ext import commands
from discord.utils import get
import yt_dlp
import asyncio
import keep_alive
from functools import partial

# Get the API token from the .env file.
intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='Por favor ', intents=intents)

yt_dlp.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address':
    '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
    'options': '-vn',
    'before_options':
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

queue = asyncio.Queue()


async def check_queue(ctx):
    if queue.qsize() > 0:
        await player_loop(ctx)


async def player_loop(ctx):
    """Our main player loop."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        origin = await queue.get()
        try:
            for key, val in origin.items():
                guild = bot.get_guild(key)
                source = val
        except:
            guild = ctx.guild
            source = origin
        async with ctx.typing():
            voice = get(bot.voice_clients, guild=guild)
            URL = source[0]
            try:
                voice.play(discord.FFmpegOpusAudio(URL, **ffmpeg_options),
                           after=lambda _:
                           (await check_queue(ctx) for _ in '_').__anext__())
            except:
                await queue.put(source)
                continue
        await ctx.send('**Reproduciendo:** {}'.format(source[1]))


@bot.event
async def on_ready():
    print("Ready!")


@bot.command(name='ven', help='Haz que Guru-Guru se una al canal de voz.')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(
            "{}, por favor, con??ctate a un canal de voz antes.".format(
                ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()
    await ctx.send("??Hola!")
    print(ctx.guild)


@bot.command(name='fuera', help='Haz que Guru-Guru se vaya del canal de voz.')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
        await ctx.send("??Hasta otra!")
    else:
        await ctx.send("Lo siento, no estoy en ning??n canal.")


@bot.command(
    name='pon',
    help=
    '??Escribe el t??tulo de tu canci??n deseada y Guru-Guru te la reproducir??! (IMPORTANTE: haz que se una al chat de voz antes de pedirle que reproduzca nada)'
)
async def play(ctx, *, url):
    if ctx.message.guild.voice_client.is_playing():
        await ctx.send(
            "Ya estoy poniendo una canci??n, ??podr??as probar a a??adirla a la cola?"
        )
        return
    if "https://" in url:
      url = f"<{url}>"
    dict = {}
    with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
        info = ydl.extract_info(url, download=False)
    Entries = []
    for i in info['entries']:
        Entries.append(i)
    dict[ctx.guild.id] = [Entries[0].get('url'), Entries[0].get('title')]
    await queue.put(dict)
    await check_queue(ctx)


@bot.command(
    name='a??ade',
    help='A??ade una canci??n a la cola mientras otra se est?? reproduciendo.')
async def add(ctx, *, url):
    if "https://" in url:
      url = f"<{url}>"
    dict = {}
    with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
        info = ydl.extract_info(url, download=False)
    Entries = []
    for i in info['entries']:
        Entries.append(i)
    dict[ctx.guild.id] = [Entries[0].get('url'), Entries[0].get('title')]
    await ctx.send("??Canci??n **{}** a??adida a la cola!".format(
        Entries[0].get("title")))
    await queue.put(dict)


@bot.command(name='pausa', help='Pon la canci??n en pausa.')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("Lo siento, no estoy tocando nada.")


@bot.command(name='sigue', help='Resume la canci??n.')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("No tengo canci??n que resumir. ??P??deme que ponga otra!")


@bot.command(
    name='para',
    help=
    'Haz que Guru-Guru se calle. (NECESITA SER EJECUTADO DOS VECES SEGUIDAS)')
async def stop(ctx):
    a = []
    while not queue.empty():
        a.append(queue.get_nowait())
        print("a")
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("??Como digas!")
        voice_client.stop()
    else:
        await ctx.send("Lo siento, no estoy tocando nada.")


@bot.command(name='siguiente',
             help='Reproduce la siguiente canci??n de la cola.')
async def next(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("??Marchando!")
    else:
        await ctx.send("Lo siento, no estoy tocando nada.")


@bot.command(name="lista", help="Muestra la lista de canciones pendientes.")
async def queue_info(ctx):
    a = []
    while not queue.empty():
        a.append(queue.get_nowait())
        await ctx.send(a[len(a) - 1][1])
    for song in a:
        await queue.put(a)


keep_alive.keep_alive()
if __name__ == "__main__":
    bot.run(
        "token"
    )

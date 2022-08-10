import discord
from discord.ext import commands
from discord.utils import get
import yt_dlp
import asyncio
import keep_alive
from functools import partial

#Prepara el bot indicando el prefijo.
intents = discord.Intents().all()
client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='Por favor ', intents=intents)

#Configuraciones de yt_dlp y de ffmpeg.
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
    '0.0.0.0'
}
ffmpeg_options = {
    'options': '-vn',
    'before_options':
    '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

#Prepara la cola
queue = asyncio.Queue()

#Estas dos funciones son el loop que irá mirando la cola y reproduciendo las canciones.
#La primera simplemente mira si hay algo en la cola y llama a la segunda.
async def check_queue(ctx):
    if queue.qsize() > 0:
        await player_loop(ctx)

#Esta función se ocupa de todo.
async def player_loop(ctx):
    await bot.wait_until_ready()
    while not bot.is_closed():
            #Primero, conseguimos la información del servidor y de la fuente extraídas de la cola.
            origin = await queue.get()
            try:
              for key, val in origin.items():
                guild = bot.get_guild(key)
                source = val
            except:
              guild = ctx.guild
              source = origin
            
            #Luego, lo reproducimos.
            async with ctx.typing():
                voice = get(bot.voice_clients, guild=guild)
                URL = source[0]
                try:
                    voice.play(discord.FFmpegOpusAudio(URL, **ffmpeg_options),
                               after=lambda _: (await check_queue(ctx)
                                                for _ in '_').__anext__())
                except:
                    #Si falla porque ya hay otra canción en marcha, devolvemos la canción a la cola.
                    await queue.put(source)
                    continue
            await ctx.send('**Reproduciendo:** {}'.format(source[1]))

#Configuración de la fuente.
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info,
                         url=data['webpage_url'],
                         download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']),
                   data=data,
                   requester=requester)


@bot.event
async def on_ready():
    print("Ready!")

#Comando bastante autoexplicatorio.
@bot.command(name='ven', help='Haz que Guru-Guru se una al canal de voz.')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send(
            "{}, por favor, conéctate a un canal de voz antes.".format(
                ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()
    await ctx.send("¡Hola!")
    
    #Esto lo puse para ver si pillaba el servidor bien.
    print(ctx.guild)


@bot.command(name='fuera', help='Haz que Guru-Guru se vaya del canal de voz.')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
        await ctx.send("¡Hasta otra!")
    else:
        await ctx.send("Lo siento, no estoy en ningún canal.")

#El infierno hecho comando.
@bot.command(
    name='pon',
    help=
    '¡Escribe el título de tu canción deseada y Guru-Guru te la reproducirá! (IMPORTANTE: haz que se una al chat de voz antes de pedirle que reproduzca nada)'
)
async def play(ctx, *, url):
    #Crea un diccionario.
    dict = {}
    
    #Pilla la información del vídeo.
    with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
        info = ydl.extract_info(url, download=False)
    Entries = []
    for i in info['entries']:
        Entries.append(i)
        
    #Añade el enlace junto al título como value, y la key es la ID del servidor.
    dict[ctx.guild.id] = [Entries[0].get('url'), Entries[0].get('title')]
    
    #Lo pone en la cola y lo reproduce.
    await queue.put(dict)
    await check_queue(ctx)


#Igual que el anterior pero sin reproducirlo al final.
@bot.command(
    name='añade',
    help='Añade una canción a la cola mientras otra se está reproduciendo.')
async def add(ctx, *, url):
    dict = {}
    with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
        info = ydl.extract_info(url, download=False)
    Entries = []
    for i in info['entries']:
        Entries.append(i)
    dict[ctx.guild.id] = [Entries[0].get('url'), Entries[0].get('title')]
    print(dict)
    await ctx.send("¡Canción {} añadida a la cola!".format(
        Entries[0].get("title")))
    await ctx.send("Hay {} canciones en la cola.".format(queue.qsize() + 1))
    await queue.put(dict)


@bot.command(name='pausa', help='Pon la canción en pausa.')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("Lo siento, no estoy tocando nada.")


@bot.command(name='sigue', help='Resume la canción.')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("No tengo canción que resumir. ¡Pídeme que ponga otra!")


#Vacía la cola y para la reproducción.
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
        await ctx.send("¡Como digas!")
        voice_client.stop()
    else:
        await ctx.send("Lo siento, no estoy tocando nada.")


@bot.command(name='siguiente',
             help='Reproduce la siguiente canción de la cola.')
async def next(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.send("¡Marchando!")
    else:
        await ctx.send("Lo siento, no estoy tocando nada.")

#Esto aún no va bien.
@bot.command(name="lista", help="Muestra la lista de canciones pendientes.")
async def queue_info(ctx):
    a = []
    while not queue.empty():
        a.append(queue.get_nowait())
        await ctx.send(a[len(a)-1][1])
    for song in a:
        await queue.put(a)

#Esta parte es para poder hostearlo en Replit.
keep_alive.keep_alive()
if __name__ == "__main__":
    bot.run(
        "token"
    )

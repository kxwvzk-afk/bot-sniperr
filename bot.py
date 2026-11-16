import asyncio
import os
import random
import string
import aiohttp
import discord
from discord.ext import commands

# ================= CONFIGURACIÓN =================
TOKEN = "MTU3MDU1MjMzMTI5OTE5NzAwOQ.G_nfBz.QxCubB_P5BWHIpQga4spgU1Br1eOl-OqIzc6h4"  # Token de tu bot de Discord
OWNER_ID = 1263303729118056449  # Tu ID de Discord para recibir alertas por DM

PROXY_USER = "75a6fccc22843dea44ba"
PROXY_PASS = "f2fa40ff356cd9b6"
PROXY_HOST = "gw.dataimpulse.com"
PROXY_PORT = "823"

URL = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
CARACTERES = string.ascii_lowercase + string.digits

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Estado global del sniper
sniper_activo = False
vistos = set()
estadisticas = {"terminados": 0, "validos": 0, "errores": 0, "limites": 0}


async def verificar_usuario(session, nick, channel_or_dm):
    global sniper_activo
    if not sniper_activo:
        return

    # Rotación por solicitud de DataImpulse
    session_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    proxy_url = f"http://{PROXY_USER}-session-{session_id}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

    try:
        async with session.post(
            URL,
            json={"username": nick},
            proxy=proxy_url,
            timeout=8
        ) as respuesta:

            if respuesta.status == 429:
                estadisticas["limites"] += 1
                estadisticas["terminados"] += 1
                return

            if respuesta.status != 200:
                estadisticas["errores"] += 1
                estadisticas["terminados"] += 1
                return

            try:
                datos = await respuesta.json()
            except Exception:
                estadisticas["errores"] += 1
                estadisticas["terminados"] += 1
                return

            if isinstance(datos, dict) and "taken" in datos:
                if datos["taken"] is False:
                    estadisticas["validos"] += 1
                    if nick not in vistos:
                        vistos.add(nick)
                        
                        # Guardar localmente en el servidor
                        with open("disponibles.txt", "a", encoding="utf-8") as f:
                            f.write(f"{nick}\n")

                        # Alerta inmediata por Discord
                        alerta = f"¡HIT ENCONTRADO! El usuario **@{nick}** está disponible 🎉"
                        try:
                            await channel_or_dm.send(alerta)
                        except Exception:
                            pass
                
            estadisticas["terminados"] += 1

    except Exception:
        estadisticas["errores"] += 1
        estadisticas["terminados"] += 1

    await asyncio.sleep(0.05)


async def bucle_sniper(target):
    global sniper_activo
    connector = aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)
    
    async with aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    ) as session:
        while sniper_activo:
            lote = set()
            while len(lote) < 30:  # Concurrencia segura y rápida en la nube
                nick = "".join(random.choices(CARACTERES, k=4))
                if nick not in vistos:
                    lote.add(nick)

            await asyncio.gather(*(verificar_usuario(session, nick, target) for nick in lote))
            await asyncio.sleep(0.02)


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")


@bot.command(name="sniper")
async def cmd_sniper(ctx, accion: str = None):
    global sniper_activo
    
    if accion == "start":
        if sniper_activo:
            await ctx.send("El sniper ya está corriendo en la nube 🚀.")
            return
        
        sniper_activo = True
        asyncio.create_task(bucle_sniper(ctx))
        await ctx.send("¡Sniper iniciado en la nube! Buscando nombres de 4 letras...")

    elif accion == "stop":
        sniper_activo = False
        await ctx.send("Sniper detenido.")

    elif accion == "status":
        await ctx.send(
            f"📊 Estado del Sniper:\n"
            f"- Activo: {sniper_activo}\n"
            f"- Terminados: {estadisticas['terminados']}\n"
            f"- Válidos (Hits): {estadisticas['validos']}\n"
            f"- Límites (429): {estadisticas['limites']}\n"
            f"- Errores: {estadisticas['errores']}"
        )
    else:
        await ctx.send("Uso correcto: `!sniper start`, `!sniper stop` o `!sniper status`")


if __name__ == "__main__":
    bot.run(TOKEN)
              

import discord
import os
import io
import contextlib

from discord.ext import commands, tasks
from dotenv import load_dotenv
from time import time
from textwrap import indent

from scraper import get_notices

load_dotenv()

# constants
TOKEN = os.environ.get("UNB_TOKEN")
INTENTS = discord.Intents.all()
REFRESH_TIME = 600 # 10 minutes

class UIUNoticeBot(commands.Bot):
    def __init__(self):
        self.start_time = time()
        self.update_channel = None
        self.last_notice_title = None


        super(UIUNoticeBot, self).__init__(
            command_prefix="-",
            intents=INTENTS,
            help_command=None,
            strip_after_prefix=True,
            case_insensitive=True,
        )

    async def setup_hook(self):
        self.update_channel = await self.fetch_channel(1212622283735302225) # Updates channel
    
    async def on_message(self, message: discord.Message):
        if message.author.bot: # Ignoring a bot message
            return None
        else:
            return await self.process_commands(message)
    
    async def on_command_error(self, ctx: commands.Context, err: commands.CommandError):
        if isinstance(err, commands.CommandNotFound):
            return await ctx.send(":x: **Command not found!**")
        elif isinstance(err, commands.NotOwner):
            return await ctx.send(":x: **Private command!**")
        else:
            await ctx.send(":warning: **An unknown Error has occured! Please wait for the next update for a fix.**")
            raise err

news_bot = UIUNoticeBot()

async def send_notice(date, title, link, context=None):
    context = context or news_bot.update_channel
    if not isinstance(context, commands.Context) and title==news_bot.last_notice_title:
        return None
    news_bot.last_notice_title = title
    emb = discord.Embed(
        title="New Notice",
        description=f"Notice date: *{date}*\n\n**{title}**",
        color=discord.Colour.random(),
        timestamp=discord.utils.utcnow()
    )
    emb.set_thumbnail(url="https://uiu.ac.bd/wp-content/uploads/2023/10/header-logo.png")
    emb.set_footer(text=news_bot.user.name)
	
    view = discord.ui.View(timeout=None)
    view.add_item(
		discord.ui.Button(label="Read more", url=link)
    )

    return await context.send(embed=emb, view=view)

@news_bot.listen()
async def on_ready():
    await news_bot.tree.sync()
    print("Logged in as {0.name} | {0.id}".format(news_bot.user))

@news_bot.hybrid_command(name="notices", aliases=['n', 'notice', 'news'])
async def send_news(ctx: commands.Context):
    """Get the latest notice manually in this channel"""
    if ctx.interaction:
        await ctx.defer(ephemeral=True)
    else:
        await ctx.typing()
    date, title, link = get_notices()
    await send_notice(date, title, link, context=ctx)

@news_bot.hybrid_command(name='ping')
async def latency(ctx):
    ping = round(news_bot.latency * 1000)

    return await ctx.send(f"**Ping: {ping} ms**")

@news_bot.hybrid_command(name='help')


@tasks.loop(seconds=600, reconnect=True)
async def send_auto_update():
    date, title, link = get_notices()
    await send_notice(date, title, link)


@news_bot.command()
@commands.is_owner()
async def start(ctx):
    await ctx.send("Task started successfully!")
    send_auto_update.start()

@news_bot.command()
@commands.is_owner()
async def stop(ctx):
    await ctx.send("Task stopped successfully!")
    send_auto_update.stop()


@news_bot.command(name='x:eval', aliases=['x:evaluate', "x:ev"])
@commands.guild_only()
@commands.is_owner()
async def x_evaluate(ctx, *, cmd):
    if "input(" in cmd.lower() or "input (" in cmd.lower():
        return await ctx.send(":x: Cannot Execute input method!")
    cmd = cmd.strip('`')
    try:
        res = eval(cmd)
    except Exception as e:
        return await ctx.send("\U0000274CFailed!\n{0.__class__.__name__}: {0}".format(e))
    else:
        ev_emb = discord.Embed(
            description=f'{res}', color=discord.Color.green())
        return await ctx.send(embed=ev_emb)


@news_bot.command(name="x:exec", aliases=["x:execute", "x:exc"])
@commands.guild_only()
@commands.is_owner()
async def x_execute(ctx, *, cmd: str):
    if "input(" in cmd.lower() or "input (" in cmd.lower():
        return await ctx.send(":x: Cannot Execute input method!")
    if cmd.startswith("``") and cmd.endswith("``"):
        cmd = ("\n".join(cmd.split("\n")[1:])).rstrip('`')
    local_vars = {
        'discord': discord,
        'commands': commands,
        'client': news_bot,
        'ctx': ctx
    }
    no_error = True
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(f"async def eval_func():\n{indent(cmd, '    ')}", local_vars)
            returned_val = await local_vars['eval_func']()
            result = f"**\U00002705Output**\n\n{output.getvalue()}\n\n`Returned value: {returned_val}`"
    except Exception as e:
        result = f"**\U0000274CFailed to Execute!**\n{e.__class__.__name__}: {e}"
        no_error = False
    finally:
        eval_emb = discord.Embed(title="Code Execution", description=result,
                                    color=discord.Color.green() if no_error else discord.Color.dark_red())
        eval_emb.set_footer(text=str(news_bot.user.name))
        eval_emb.timestamp = discord.utils.utcnow()
        await ctx.send(embed=eval_emb)


if __name__=="__main__":
	news_bot.run(TOKEN)
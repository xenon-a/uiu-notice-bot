import discord
import os
import io
import contextlib
# TODO: Set uptime viewer in ping command
from discord.ext import commands, tasks
from dotenv import load_dotenv
from time import time
from textwrap import indent

from scraper import get_notices

load_dotenv()

# constants
TOKEN = os.environ.get("UNB_TOKEN")
INTENTS = discord.Intents.all()
REFRESH_INTERVAL = 600 #SECONDS

class UIUNoticeBot(commands.AutoShardedBot):
    def __init__(self):
        self.start_time = time()
        self.update_channel = None
        self.owner = None

        super(UIUNoticeBot, self).__init__(
            command_prefix="-",
            intents=INTENTS,
            allowed_mentions=discord.AllowedMentions(everyone=True),
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
            await self.owner.send(f"{err.__class__.__name__}: {str(err)}")
            raise err


notice_bot = UIUNoticeBot()


async def send_notice(date, title, link, context=None):
    context = context or notice_bot.update_channel
    with open("last_notice_title.txt", "r") as title_file:
        last_notice_title = title_file.read()
    mention = str()
    if not isinstance(context, commands.Context):
        if title==last_notice_title:
            return None
        else:
            mention = "@everyone"
    else:
        mention = context.author.mention
    with open("last_notice_title.txt", "w") as title_file:
        title_file.write(title)
    emb = discord.Embed(
        title="New Notice",
        description=f"{mention} \n\nDate: `{date}`\n\nTitle: **{title}**\n",
        color=discord.Colour.random(),
        timestamp=discord.utils.utcnow()
    )
    emb.set_thumbnail(url="https://uiu.ac.bd/wp-content/uploads/2023/10/header-logo.png")
    emb.set_footer(text=notice_bot.user.name)
	
    view = discord.ui.View(timeout=None)
    view.add_item(
		discord.ui.Button(label="Read Notice", url=link)
    )

    return await context.send(embed=emb, view=view)


@notice_bot.listen()
async def on_ready():
    await notice_bot.tree.sync()
    notice_bot.owner = await notice_bot.fetch_user(425590285943439362)
    if not send_auto_update.is_running():
        print("Starting Task.")
        send_auto_update.start()
        print("Task started")
    await notice_bot.change_presence(status=discord.Status.idle, activity=discord.Activity(name="UIU Notices", type=discord.ActivityType.listening))
    print("Logged in as {0.name} | {0.id}".format(notice_bot.user))


@notice_bot.hybrid_command(name="notices", aliases=['n', 'notice', 'news'])
async def send_news(ctx: commands.Context):
    """Get the latest notice manually in this channel"""
    if ctx.interaction:
        await ctx.defer(ephemeral=True)
    else:
        await ctx.typing()
    date, title, link = get_notices()
    await send_notice(date, title, link, context=ctx)


@notice_bot.hybrid_command(name='ping')
async def latency(ctx):
    ping = round(notice_bot.latency * 1000)
    uptime = round(time() - notice_bot.start_time)
    mins, secs = divmod(uptime, 60)
    hrs, mins = divmod(mins, 60)

    return await ctx.send(f"Ping: **{ping} ms**\nUptime: **{hrs} hours {mins} minutes {secs} seconds**")


@tasks.loop(seconds=REFRESH_INTERVAL, reconnect=True)
async def send_auto_update():
    date, title, link = get_notices()
    await send_notice(date, title, link)


@send_auto_update.error
async def send_update_error(err):
    await notice_bot.owner.send(f"{err.__class__.__name__}: {str(err)}")
    raise err


@notice_bot.command()
@commands.is_owner()
async def start(ctx):
    if send_auto_update.is_running():
        return await ctx.send("The task is already running!")
    send_auto_update.start()
    await ctx.send("Task started successfully!")

@notice_bot.command()
@commands.is_owner()
async def stop(ctx):
    if not send_auto_update.is_running():
        return await ctx.send("The task is not running!")
    send_auto_update.stop()
    await ctx.send("Task stopped successfully!")


@notice_bot.command(name='x:eval', aliases=['x:evaluate', "x:ev"])
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


@notice_bot.command(name="x:exec", aliases=["x:execute", "x:exc"])
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
        'client': notice_bot,
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
        eval_emb.set_footer(text=str(notice_bot.user.name))
        eval_emb.timestamp = discord.utils.utcnow()
        await ctx.send(embed=eval_emb)


if __name__=="__main__":
    if not os.path.exists("last_notice_title.txt"):
        open("last_notice_title.txt", "x").close()
    notice_bot.run(TOKEN)
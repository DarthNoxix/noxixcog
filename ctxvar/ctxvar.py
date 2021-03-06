import discord
import typing
from redbot.core import commands
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import box
from copy import copy

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel.
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

class CtxVar(commands.Cog):
    """A cog to list and display the contents of all sub-functions of `ctx`!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.command()
    async def ctxvar(self, ctx, args: typing.Optional[str]=""):
        instance = ctx
        if not args == "":
            if not hasattr(instance, f"{args}"):
                await ctx.send("The argument you specified is not a subclass of the instance.")
                return
            args = f".{args}"
        instance_name = "ctx"
        full_instance_name = f"{instance_name}{args}"
        if len(f"**{full_instance_name}**") > 256:
            return None
        embed: discord.Embed = discord.Embed()
        embed.title = f"**{full_instance_name}**"
        embed.description = f"Here are all the variables and their associated values that can be used in this class."
        embed.color = 0x01d758
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/2048px-Python-logo-notext.svg.png")
        one_l = []
        for x in eval(f"dir(instance{args})"):
            if not eval(f"hasattr(instance{args}.{x}, '__call__')") and not "__" in x:
                one_l.append(x)
        lists = []
        while True:
            l = one_l[0:20]
            one_l = one_l[20:]
            lists.append(l)
            if one_l == []:
                break
        embeds = []
        for l in lists:
            e = copy(embed)
            for x in l:
                if not len(f"{x}") > 256:
                    e.add_field(
                        inline=True,
                        name=f"{x}",
                        value=box(str(eval(f"instance{args}.{x}"))[:100]))
            embeds.append(e)

        page = 0
        for embed in embeds:
            page += 1
            embed.set_footer(text=f"Page {page}/{len(embeds)}")

        await menu(ctx, pages=embeds, controls=DEFAULT_CONTROLS)
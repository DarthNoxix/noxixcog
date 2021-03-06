from random import choice

import discord, typing, logging, datetime
from typing import List
from redbot.core import checks, Config, commands, data_manager
from redbot.core.utils.chat_formatting import escape, humanize_list, inline, humanize_timedelta, pagify
from copy import copy

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to TrustyJAID for the code (a bit modified to work here and to improve as needed) for the log messages sent! (https://github.com/TrustyJAID/Trusty-cogs/tree/master/extendedmodlog)
# Thanks to Kreusada for the code (with modifications to make it work and match the syntax of the rest) to add a log channel or remove it if no channel is specified! (https://github.com/Kreusada/Kreusada-Cogs/tree/master/captcha)
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

class CmdChannel(commands.Cog):
    """A cog to send the result of a command to another channel!"""

    def __init__(self, bot):
        self.bot = bot
        self.data: Config = Config.get_conf(
            self,
            identifier=793502759720,
            force_registration=True,
        )
        self.cmd_guild = {
            "logschannel": None, # The channel for logs.
            "enabled_cmdchannel": True, # Enable the possibility of commands.
            "confirmation_cmdchannel": False, # Enable the confirmation.
            "deletemessage_cmdchannel": False, # Enable the message delete.
            "informationmessage_cmdchannel": False, # Enable the information message.
            "enabled_cmduser": True, # Enable the possibility of commands.
            "confirmation_cmduser": False, # Enable the confirmation.
            "deletemessage_cmduser": False, # Enable the message delete.
            "informationmessage_cmduser": False, # Enable the information message.
            "enabled_cmduserchannel": True, # Enable the possibility of commands.
            "confirmation_cmduserchannel": False, # Enable the confirmation.
            "deletemessage_cmduserchannel": False, # Enable the message delete.
            "informationmessage_cmduserchannel": False, # Enable the information message.
        }

        self.data.register_guild(**self.cmd_guild)

    @commands.guild_only()
    @commands.mod()
    @commands.command(aliases=["channelcmd"])
    async def cmdchannel(self, ctx, guild: typing.Optional[discord.Guild]=None, channel: typing.Optional[typing.Union[discord.TextChannel, int]]=None, *, command: str = ""):
        """Act as if the command had been typed in the channel of your choice.
        The prefix must be entered if it is a command. Otherwise, it will be a message only.
        If you do not specify a channel, the current one will be used, unless the command you want to use is the name of an existing channel (help or test for example).
        """
        if channel is not None:
            if isinstance(channel, int):
                if guild is not None:
                    channel = guild.get_channel(channel)
                else:
                    if ctx.author.id in ctx.bot.owner_ids:
                        await ctx.send("Please specify a server if you want to use a command in another server.")
                        return
                    else:
                        channel = None

        if channel is None:
            channel = ctx.channel

        guild = channel.guild

        if channel not in ctx.guild.channels and not ctx.author.id in ctx.bot.owner_ids:
            await ctx.send("Only a bot owner can use a command from another server.")
            return

        member = guild.get_member(ctx.author.id)
        if member is None:
            await ctx.send("To send commands to another server, you must be there.")
            return

        if not command and not ctx.message.embeds and not ctx.message.attachments:
            await ctx.send_help()
            return

        config = await self.data.guild(guild).all()
        logschannel = config["logschannel"]
        actual_state_enabled = config["enabled_cmdchannel"]
        actual_state_confirmation = config["confirmation_cmdchannel"]
        actual_state_deletemessage = config["deletemessage_cmdchannel"]
        actual_state_information = config["informationmessage_cmdchannel"]
        cmd_colour = await self.bot.get_embed_colour(guild.text_channels[0])
        if actual_state_enabled:
            permissions = channel.permissions_for(ctx.author)
            if permissions.read_messages and permissions.send_messages:
                if actual_state_information:
                    await channel.send(f"The command issued in this channel is:\n```{command}```")
                if logschannel:
                    can_run = await self.member_can_run(ctx)
                    embed = discord.Embed(
                        description=f"CmdChannel - Command used: {command}",
                        colour=cmd_colour,
                    )
                    embed.add_field(name=("Imitated user"), value=ctx.author.mention)
                    embed.add_field(name=("Channel"), value=channel.mention)
                    embed.add_field(name=("Can Run"), value=str(can_run))
                    author_title = ("{member} ({m_id}) - Used a Command").format(
                        member=ctx.author, m_id=ctx.author.id
                    )
                    embed.set_author(name=author_title, icon_url=ctx.author.avatar_url)
                    logschannel = ctx.bot.get_channel(logschannel)
                    await logschannel.send(embed=embed)
                msg = ctx.message
                msg.content = command
                new_ctx = await ctx.bot.get_context(msg)
                if new_ctx.valid:
                    new_ctx.guild = guild
                    new_ctx.channel = channel
                    new_ctx.author = ctx.author
                    await ctx.bot.invoke(new_ctx)
                else:
                    new_ctx.message.channel = channel
                    new_ctx.message.author = ctx.author
                    ctx.bot.dispatch("message", new_ctx.message)
                if actual_state_confirmation:
                    try:
                        await ctx.author.send(f"The `{command}` command has been launched in the {channel} channel. You can check if it worked.")
                    except discord.Forbidden:
                        await ctx.send(f"The `{command}` command has been launched in the {channel} channel. You can check if it worked.")
            else:
                try:
                    await ctx.author.send(f"You cannot run this command because you do not have the permissions to send messages in the {channel} channel.")
                except discord.Forbidden:
                    await ctx.send(f"You cannot run this command because you do not have the permissions to send messages in the {channel} channel.")
        else:
            try:
                await ctx.author.send("CommandChannel have been disabled by an administrator of this server.")
            except discord.Forbidden:
                await ctx.send("CommandChannel have been disabled by an administrator of this server.")
            return

    @commands.guild_only()
    @commands.is_owner()
    @commands.command(aliases=["usercmd"])
    async def cmduser(self, ctx, user: typing.Optional[discord.Member]=None, *, command: str = ""):
        """Act as if the command had been typed by imitating the specified user.
        The prefix must be entered if it is a command. Otherwise, it will be a message only.
        If you do not specify a user, the author will be used.
        """
        if user is None:
            user = ctx.author

        if not command and not ctx.message.embeds and not ctx.message.attachments:
            await ctx.send_help()
            return

        config = await self.data.guild(ctx.guild).all()
        logschannel = config["logschannel"]
        actual_state_enabled = config["enabled_cmduser"]
        actual_state_confirmation = config["confirmation_cmduser"]
        actual_state_deletemessage = config["deletemessage_cmduser"]
        actual_state_information = config["informationmessage_cmduser"]
        cmd_colour = await self.bot.get_embed_colour(ctx.guild.text_channels[0])
        if actual_state_enabled:
            permissions = ctx.channel.permissions_for(ctx.author)
            if permissions.read_messages and permissions.send_messages:
                if actual_state_information:
                    await ctx.channel.send(f"The command issued in this channel is:\n```{command}```")
                if logschannel:
                    can_run = await self.member_can_run(ctx)
                    embed = discord.Embed(
                        description=f"CmdUser - Command used: {command}",
                        colour=cmd_colour,
                    )
                    embed.add_field(name=("Imitated user"), value=user)
                    embed.add_field(name=("Channel"), value=ctx.channel.mention)
                    embed.add_field(name=("Can Run"), value=str(can_run))
                    author_title = ("{member} ({m_id}) - Used a Command").format(
                        member=ctx.author, m_id=ctx.author.id
                    )
                    embed.set_author(name=author_title, icon_url=ctx.author.avatar_url)
                    logschannel = ctx.bot.get_channel(logschannel)
                    await logschannel.send(embed=embed)
                msg = ctx.message
                msg.content = command
                new_ctx = await ctx.bot.get_context(msg)
                if new_ctx.valid:
                    new_ctx.guild = ctx.guild
                    new_ctx.channel = ctx.channel
                    new_ctx.author = user
                    await ctx.bot.invoke(new_ctx)
                else:
                    new_ctx.message.channel = ctx.channel
                    new_ctx.message.author = user
                    ctx.bot.dispatch("message", new_ctx.msg)
                if actual_state_confirmation:
                    try:
                        await ctx.author.send(f"The `{command}` command has been launched in the {ctx.channel} channel by imitating the {user} user. You can check if it worked.")
                    except discord.Forbidden:
                        await ctx.send(f"The `{command}` command has been launched in the {ctx.channel} channel by imitating the {user} user. You can check if it worked.")
            else:
                try:
                    await ctx.author.send(f"You cannot run this command because you do not have the permissions to send messages in the {ctx.channel} channel.")
                except discord.Forbidden:
                    await ctx.send(f"You cannot run this command because you do not have the permissions to send messages in the {ctx.channel} channel.")
        else:
            try:
                await ctx.author.send("CommandUser have been disabled by an administrator of this server.")
            except discord.Forbidden:
                await ctx.send("CommandUser have been disabled by an administrator of this server.")
            return

    @commands.guild_only()
    @commands.is_owner()
    @commands.command(aliases=["userchannelcmd"])
    async def cmduserchannel(self, ctx, user: typing.Optional[discord.Member]=None, channel: typing.Optional[discord.TextChannel]=None, *, command: str = ""):
        """Act as if the command had been typed in the channel of your choice by imitating the specified user.
        The prefix must be entered if it is a command. Otherwise, it will be a message only.
        If you do not specify a user, the author will be used.
        """
        if channel is None:
            channel = ctx.channel

        if user is None:
            user = ctx.author

        if not command and not ctx.message.embeds and not ctx.message.attachments:
            await ctx.send_help()
            return

        config = await self.data.guild(guild).all()
        logschannel = config["logschannel"]
        actual_state_enabled = config["enabled_cmduserchannel"]
        actual_state_confirmation = config["confirmation_cmduserchannel"]
        actual_state_deletemessage = config["deletemessage_cmduserchannel"]
        actual_state_information = config["informationmessage_cmduserchannel"]
        cmd_colour = await self.bot.get_embed_colour(guild.text_channels[0])
        if actual_state_enabled:
            permissions = channel.permissions_for(ctx.author)
            if permissions.read_messages and permissions.send_messages:
                if actual_state_information:
                    await channel.send(f"The command issued in this channel is:\n```{command}```")
                if logschannel:
                    can_run = await self.member_can_run(ctx)
                    embed = discord.Embed(
                        description=f"CmdUserChannel - Command used: {command}",
                        colour=cmd_colour,
                    )
                    embed.add_field(name=("Imitated user"), value=user)
                    embed.add_field(name=("Channel"), value=channel.mention)
                    embed.add_field(name=("Can Run"), value=str(can_run))
                    author_title = ("{member} ({m_id}) - Used a Command").format(
                        member=ctx.author, m_id=ctx.author.id
                    )
                    embed.set_author(name=author_title, icon_url=ctx.author.avatar_url)
                    logschannel = ctx.bot.get_channel(logschannel)
                    await logschannel.send(embed=embed)
                msg = ctx.message
                msg.content = command
                new_ctx = await ctx.bot.get_context(msg)
                if new_ctx.valid:
                    new_ctx.guild = ctx.guild
                    new_ctx.channel = channel
                    new_ctx.author = user
                    await ctx.bot.invoke(new_ctx)
                else:
                    new_ctx.message.channel = channel
                    new_ctx.message.author = user
                    ctx.bot.dispatch("message", new_ctx.msg)
                if actual_state_confirmation:
                    try:
                        await ctx.author.send(f"The `{command}` command has been launched in the {channel} channel by imitating the {user} user. You can check if it worked.")
                    except discord.Forbidden:
                        await ctx.send(f"The `{command}` command has been launched in the {channel} channel by imitating the {user} user. You can check if it worked.")
            else:
                try:
                    await ctx.author.send(f"You cannot run this command because you do not have the permissions to send messages in the {channel} channel.")
                except discord.Forbidden:
                    await ctx.send(f"You cannot run this command because you do not have the permissions to send messages in the {channel} channel.")
        else:
            try:
                await ctx.author.send("CommandUserChannel have been disabled by an administrator of this server.")
            except discord.Forbidden:
                await ctx.send("CommandUserChannel have been disabled by an administrator of this server.")
            return

    @commands.command()
    async def testvar(self, ctx):
        """Test variables.
        """
        embed: discord.Embed = discord.Embed()
        embed.title = "Testvar"
        embed.description = "Variables:"
        embed.add_field(
            name="Author:",
            value=f"{ctx.author}")
        embed.add_field(
            name="Channel:",
            value=f"{ctx.channel}")
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.guildowner_or_permissions(administrator=True)
    @commands.group(name="cmdset", aliases=["setcmd"])
    async def config(self, ctx):
        """Configure Command for your server."""

    @config.command(aliases=["lchann", "lchannel", "logschan", "logchannel", "logsc"], usage="<text_channel_or_'none'>")
    async def logschannel(self, ctx, *, channel: typing.Optional[discord.TextChannel]=None):
        """Set a channel where events are registered.

        ``channel``: Text channel.
        You can also use "None" if you wish to remove the logging channel.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        if channel is None:
            await self.data.guild(ctx.guild).logschannel.clear()
            await ctx.send("Logging channel removed.")
            return

        needperm = await self.check_permissions_in_channel(["embed_links", "read_messages", "read_message_history", "send_messages", "attach_files"], channel)
        if needperm:
            await ctx.send("The bot does not have at least one of the following permissions in this channel: `embed_links`, `read_messages`, `read_message_history`, `send_messages`, `attach_files`.")
            return

        await self.data.guild(ctx.guild).logschannel.set(channel.id)
        await ctx.send(f"Logging channel registered: {channel.mention}.")

    async def check_permissions_in_channel(self, permissions: List[str], channel: discord.TextChannel):
        """Function to checks if the permissions are available in a guild.
        This will return a list of the missing permissions.
        """
        return [
            permission
            for permission in permissions
            if not getattr(channel.permissions_for(channel.guild.me), permission)
        ]

    @commands.guildowner_or_permissions(administrator=True)
    @config.group(name="cmdchannel", aliases=["channelcmd"])
    async def cmdchannelconfig(self, ctx: commands.GuildContext):
        """Configure CmdChannel for your server."""

    @cmdchannelconfig.command(name="enable", aliases=["activate"], usage="<true_or_false>")
    async def activatecmdchannel(self, ctx, state: bool):
        """Enable or disable CommandChannel.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_enabled = config["enabled_cmdchannel"]
        if actual_state_enabled is state:
            await ctx.send(f"CommandChannel is already set on {state}.")
            return

        await self.data.guild(ctx.guild).enabled_cmdchannel.set(state)
        await ctx.send(f"CommandChannel state registered: {state}.")

    @cmdchannelconfig.command(name="confirmation", aliases=["confirm"], usage="<true_or_false>")
    async def confirmationcmdchannel(self, ctx, state: bool):
        """Enable or disable confirmation.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_confirmation = config["confirmation_cmdchannel"]
        if actual_state_confirmation is state:
            await ctx.send(f"Confirmation is already set on {state}.")
            return

        await self.data.guild(ctx.guild).confirmation_cmdchannel.set(state)
        await ctx.send(f"Confirmation state registered: {state}.")

    @cmdchannelconfig.command(name="delete", aliases=["deletemessage"], usage="<true_or_false>")
    async def deletemessagecmdchannel(self, ctx, state: bool):
        """Enable or disable message delete.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_delete = config["deletemessage_cmdchannel"]
        if actual_state_delete is state:
            await ctx.send(f"Message delete is already set on {state}.")
            return

        await self.data.guild(ctx.guild).deletemessage_cmdchannel.set(state)
        await ctx.send(f"Message delete state registered: {state}.")

    @cmdchannelconfig.command(name="information", aliases=["info"], usage="<true_or_false>")
    async def informationcmdchannel(self, ctx, state: bool):
        """Enable or disable information message.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_information = config["informationmessage_cmdchannel"]
        if actual_state_information is state:
            await ctx.send(f"Information message is already set on {state}.")
            return

        await self.data.guild(ctx.guild).informationmessage_cmdchannel.set(state)
        await ctx.send(f"Information message state registered: {state}.")

    @commands.guildowner_or_permissions(administrator=True)
    @config.group(name="cmduser", aliases=["usercmd"])
    async def cmduserconfig(self, ctx: commands.GuildContext):
        """Configure CmdUser for your server."""

    @cmduserconfig.command(name="enable", aliases=["activate"], usage="<true_or_false>")
    async def activatecmduser(self, ctx, state: bool):
        """Enable or disable CommandUser.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_enabled = config["enabled_cmduser"]
        if actual_state_enabled is state:
            await ctx.send(f"CommandUser is already set on {state}.")
            return

        await self.data.guild(ctx.guild).enabled_cmduser.set(state)
        await ctx.send(f"CommandUser state registered: {state}.")

    @cmduserconfig.command(name="confirmation", aliases=["confirm"], usage="<true_or_false>")
    async def confirmationcmduser(self, ctx, state: bool):
        """Enable or disable confirmation.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_confirmation = config["confirmation_cmduser"]
        if actual_state_confirmation is state:
            await ctx.send(f"CommandUser confirmation is already set on {state}.")
            return

        await self.data.guild(ctx.guild).confirmation_cmduser.set(state)
        await ctx.send(f"CommandUser confirmation state registered: {state}.")

    @cmduserconfig.command(name="delete", aliases=["deletemessage"], usage="<true_or_false>")
    async def deletemessagecmduser(self, ctx, state: bool):
        """Enable or disable message delete.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_delete = config["deletemessage_cmduser"]
        if actual_state_delete is state:
            await ctx.send(f"CommandUser message delete is already set on {state}.")
            return

        await self.data.guild(ctx.guild).deletemessage_cmduser.set(state)
        await ctx.send(f"CommandUser message delete state registered: {state}.")

    @cmduserconfig.command(name="information", aliases=["info"], usage="<true_or_false>")
    async def informationcmduser(self, ctx, state: bool):
        """Enable or disable information message.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_information = config["informationmessage_cmduser"]
        if actual_state_information is state:
            await ctx.send(f"CommandUser information message is already set on {state}.")
            return

        await self.data.guild(ctx.guild).informationmessage_cmduser.set(state)
        await ctx.send(f"CommandUser information message state registered: {state}.")

    @commands.guildowner_or_permissions(administrator=True)
    @config.group(name="cmduserchannel", aliases=["userchannelcmd"])
    async def cmduserchannelconfig(self, ctx: commands.GuildContext):
        """Configure CmdUserChannel for your server."""

    @cmduserchannelconfig.command(name="enable", aliases=["activate"], usage="<true_or_false>")
    async def activatecmduserchannel(self, ctx, state: bool):
        """Enable or disable CommandUserChannel.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_enabled = config["enabled_cmduserchannel"]
        if actual_state_enabled is state:
            await ctx.send(f"CommandUserChannel is already set on {state}.")
            return

        await self.data.guild(ctx.guild).enabled_cmduserchannel.set(state)
        await ctx.send(f"CommandUserChannel state registered: {state}.")

    @cmduserchannelconfig.command(name="confirmation", aliases=["confirm"], usage="<true_or_false>")
    async def confirmationcmduserchannel(self, ctx, state: bool):
        """Enable or disable confirmation.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_confirmation = config["confirmation_cmduserchannel"]
        if actual_state_confirmation is state:
            await ctx.send(f"CommandUserChannel confirmation is already set on {state}.")
            return

        await self.data.guild(ctx.guild).confirmation_cmduserchannel.set(state)
        await ctx.send(f"CommandUserChannel confirmation state registered: {state}.")

    @cmduserchannelconfig.command(name="delete", aliases=["deletemessage"], usage="<true_or_false>")
    async def deletemessagecmduserchannel(self, ctx, state: bool):
        """Enable or disable message delete.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_delete = config["deletemessage_cmduserchannel"]
        if actual_state_delete is state:
            await ctx.send(f"CommandUserChannel message delete is already set on {state}.")
            return

        await self.data.guild(ctx.guild).deletemessage_cmduserchannel.set(state)
        await ctx.send(f"CommandUserChannel message delete state registered: {state}.")

    @cmduserchannelconfig.command(name="information", aliases=["info"], usage="<true_or_false>")
    async def informationcmduserchannel(self, ctx, state: bool):
        """Enable or disable information message.

        Use `True` (Or `yes`) to enable or `False` (or `no`) to disable.
        """
        if not ctx.author.id == ctx.guild.owner.id:
            await ctx.send("Only the owner of this server can access these commands!")
            return

        config = await self.data.guild(ctx.guild).all()

        actual_state_information = config["informationmessage_cmduserchannel"]
        if actual_state_information is state:
            await ctx.send(f"CommandUserChannel information message is already set on {state}.")
            return

        await self.data.guild(ctx.guild).informationmessage_cmduserchannel.set(state)
        await ctx.send(f"CommandUserChannel information message state registered: {state}.")

    async def member_can_run(self, ctx: commands.Context) -> bool:
        """Check if a user can run a command.
        This will take the current context into account, such as the
        server and text channel.
        https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/release/3.0.0/redbot/cogs/permissions/permissions.py
        """
        command = ctx.message.content.replace(ctx.prefix, "")
        com = ctx.bot.get_command(command)
        if com is None:
            return False
        else:
            try:
                testcontext = await ctx.bot.get_context(ctx.message, cls=commands.Context)
                to_check = [*reversed(com.parents)] + [com]
                can = False
                for cmd in to_check:
                    can = await cmd.can_run(testcontext)
                    if can is False:
                        break
            except (commands.CheckFailure, commands.DisabledCommand):
                can = False
        return can

import discord
import datetime
import typing
from redbot.core import Config, commands, modlog
from redbot.core.bot import Red
from copy import copy
import io
import chat_exporter
from dislash import ActionRow, Button, ButtonStyle
from .settings import settings
from .utils import utils

# Credits:
# Thanks to @epic guy on Discord for the basic syntax (command groups, commands) and also commands (await ctx.send, await ctx.author.send, await ctx.message.delete())!
# Thanks to @YamiKaitou on Discord for the technique in the init file to load the interaction client only if it is not loaded! Before this fix, when a user clicked on a button, the actions would be launched about 10 times, which caused huge spam and a loop in the channel.
# Thanks to the developers of the cogs I added features to as it taught me how to make a cog! (Chessgame by WildStriker, Captcha by Kreusada, Speak by Epic guy and Rommer by Dav)
# Thanks to all the people who helped me with some commands in the #coding channel of the redbot support server!

class EmbassyTool(settings, commands.Cog):
    """A cog to manage an embassy system!"""

    def __init__(self, bot):
        self.bot = bot
        self.data: Config = Config.get_conf(
            self,
            identifier=937480369417,
            force_registration=True,
        )
        self.embassy_guild = {
            "settings": {
                "enable": False,
                "logschannel": None,
                "category_open": None,
                "category_close": None,
                "admin_role": None,
                "support_role": None,
                "embassy_role": None,
                "view_role": None,
                "ping_role": None,
                "nb_max": 5,
                "create_modlog": False,
                "close_on_leave": False,
                "create_on_react": False,
                "color": 0x01d758,
                "thumbnail": "http://www.quidd.it/wp-content/uploads/2017/10/Embassy-add-icon.png",
                "audit_logs": False,
                "close_confirmation": False,
                "emoji_open": "❓",
                "emoji_close": "🔒",
                "last_nb": 0000,
                "embed_button": {
                    "title": "Open An Embassy",
                    "description": ( "To open an embassy with us please press the button below.\n"
                                     "If you have a serious matter that you need handled now please dm Klaus or Valentinos.\n"
                                     "We hope you enjoy your stay!"),
                },
            },
            "embassys": {},
        }

        self.data.register_guild(**self.embassy_guild)

    async def get_config(self, guild: discord.Guild):
        config = await self.bot.get_cog("EmbassyTool").data.guild(guild).settings.all()
        if config["logschannel"] is not None:
            config["logschannel"] = guild.get_channel(config["logschannel"])
        if config["category_open"] is not None:
            config["category_open"] = guild.get_channel(config["category_open"])
        if config["category_close"] is not None:
            config["category_close"] = guild.get_channel(config["category_close"])
        if config["admin_role"] is not None:
            config["admin_role"] = guild.get_role(config["admin_role"])
        if config["support_role"] is not None:
            config["support_role"] = guild.get_role(config["support_role"])
        if config["embassy_role"] is not None:
            config["embassy_role"] = guild.get_role(config["embassy_role"])
        if config["view_role"] is not None:
            config["view_role"] = guild.get_role(config["view_role"])
        if config["ping_role"] is not None:
            config["ping_role"] = guild.get_role(config["ping_role"])
        return config

    async def get_embassy(self, channel: discord.TextChannel):
        config = await self.bot.get_cog("EmbassyTool").data.guild(channel.guild).embassys.all()
        if str(channel.id) in config:
            json = config[str(channel.id)]
        else:
            return None
        embassy = Embassy.from_json(json, self.bot)
        embassy.bot = self.bot
        embassy.guild = embassy.bot.get_guild(embassy.guild)
        embassy.owner = embassy.guild.get_member(embassy.owner)
        embassy.channel = embassy.guild.get_channel(embassy.channel)
        embassy.claim = embassy.guild.get_member(embassy.claim)
        embassy.created_by = embassy.guild.get_member(embassy.created_by)
        embassy.opened_by = embassy.guild.get_member(embassy.opened_by)
        embassy.closed_by = embassy.guild.get_member(embassy.closed_by)
        embassy.deleted_by = embassy.guild.get_member(embassy.deleted_by)
        embassy.renamed_by = embassy.guild.get_member(embassy.renamed_by)
        members = embassy.members
        embassy.members = []
        for m in members:
            embassy.members.append(channel.guild.get_member(m))
        if embassy.created_at is not None:
            embassy.created_at = datetime.datetime.fromtimestamp(embassy.created_at)
        if embassy.opened_at is not None:
            embassy.opened_at = datetime.datetime.fromtimestamp(embassy.opened_at)
        if embassy.closed_at is not None:
            embassy.closed_at = datetime.datetime.fromtimestamp(embassy.closed_at)
        if embassy.deleted_at is not None:
            embassy.deleted_at = datetime.datetime.fromtimestamp(embassy.deleted_at)
        if embassy.renamed_at is not None:
            embassy.renamed_at = datetime.datetime.fromtimestamp(embassy.renamed_at)
        if embassy.first_message is not None:
            embassy.first_message = embassy.channel.get_partial_message(embassy.first_message)
        return embassy

    async def get_audit_reason(self, guild: discord.Guild, author: typing.Optional[discord.Member]=None, reason: typing.Optional[str]=None):
        if reason is None:
            reason = "Action taken for the embassy system."
        config = await self.bot.get_cog("EmbassyTool").get_config(guild)
        if author is None or not config["audit_logs"]:
            return f"{reason}"
        else:
            return f"{author.name} ({author.id}) - {reason}"

    async def get_embed_important(self, embassy, more: bool, author: discord.Member, title: str, description: str):
        config = await self.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        actual_color = config["color"]
        actual_thumbnail = config["thumbnail"]
        embed: discord.Embed = discord.Embed()
        embed.title = f"{title}"
        embed.description = f"{description}"
        embed.set_thumbnail(url=actual_thumbnail)
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now()
        embed.set_author(name=author, url=author.avatar_url, icon_url=author.avatar_url)
        embed.set_footer(text=embassy.guild.name, icon_url=embassy.guild.icon_url)
        embed.add_field(
            inline=True,
            name="Embassy ID:",
            value=f"{embassy.id}")
        embed.add_field(
            inline=True,
            name="Owned by:",
            value=f"{embassy.owner.mention} ({embassy.owner.id})")
        embed.add_field(
            inline=True,
            name="Channel:",
            value=f"{embassy.channel.mention} - {embassy.channel.name} ({embassy.channel.id})")
        if more:
            if embassy.closed_by is not None:
                embed.add_field(
                    inline=False,
                    name="Closed by:",
                    value=f"{embassy.owner.mention} ({embassy.owner.id})")
            if embassy.deleted_by is not None:
                embed.add_field(
                    inline=True,
                    name="Deleted by:",
                    value=f"{embassy.deleted_by.mention} ({embassy.deleted_by.id})")
            if embassy.closed_at:
                embed.add_field(
                    inline=False,
                    name="Closed at:",
                    value=f"{embassy.closed_at}")
        embed.add_field(
            inline=False,
            name="Reason:",
            value=f"{embassy.reason}")
        return embed

    async def get_embed_action(self, embassy, author: discord.Member, action: str):
        config = await self.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        actual_color = config["color"]
        embed: discord.Embed = discord.Embed()
        embed.title = f"Embassy {embassy.id} - Action taken"
        embed.description = f"{action}"
        embed.color = actual_color
        embed.timestamp = datetime.datetime.now()
        embed.set_author(name=author, url=author.avatar_url, icon_url=author.avatar_url)
        embed.set_footer(text=embassy.guild.name, icon_url=embassy.guild.icon_url)
        embed.add_field(
            inline=False,
            name="Reason:",
            value=f"{embassy.reason}")
        return embed

    async def check_limit(self, member: discord.Member):
        config = await self.bot.get_cog("EmbassyTool").get_config(member.guild)
        data = await self.bot.get_cog("EmbassyTool").data.guild(member.guild).embassys.all()
        to_remove = []
        count = 1
        for id in data:
            channel = member.guild.get_channel(int(id))
            if channel is not None:
                embassy = await self.bot.get_cog("EmbassyTool").get_embassy(channel)
                if embassy.created_by == member and embassy.status == "open":
                    count += 1
            if channel is None:
                to_remove.append(id)
        if not to_remove == []:
            data = await self.bot.get_cog("EmbassyTool").data.guild(member.guild).embassys.all()
            for id in to_remove:
                del data[str(id)]
            await self.bot.get_cog("EmbassyTool").data.guild(member.guild).embassys.set(data)
        if count > config["nb_max"]:
            return False
        else:
            return True
        
    async def create_modlog(self, embassy, action: str, reason: str):
        config = await self.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        if config["create_modlog"]:
            case = await modlog.create_case(
                        embassy.bot,
                        embassy.guild,
                        embassy.created_at,
                        action_type=action,
                        user=embassy.created_by,
                        moderator=embassy.created_by,
                        reason=reason,
                    )
            return case
        return

    def decorator(enable_check: typing.Optional[bool]=False, embassy_check: typing.Optional[bool]=False, status: typing.Optional[str]=None, embassy_owner: typing.Optional[bool]=False, admin_role: typing.Optional[bool]=False, support_role: typing.Optional[bool]=False, embassy_role: typing.Optional[bool]=False, view_role: typing.Optional[bool]=False, guild_owner: typing.Optional[bool]=False, claim: typing.Optional[bool]=None, claim_staff: typing.Optional[bool]=False, members: typing.Optional[bool]=False):
        async def pred(ctx):
            config = await ctx.bot.get_cog("EmbassyTool").get_config(ctx.guild)
            if enable_check:
                if not config["enable"]:
                    return
            if embassy_check:
                embassy = await ctx.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
                if embassy is None:
                    return
                if status is not None:
                    if not embassy.status == status:
                        return False
                if claim is not None:
                    if embassy.claim is not None:
                        check = True
                    elif embassy.claim is None:
                        check = False
                    if not check == claim:
                        return False
                if ctx.author.id in ctx.bot.owner_ids:
                    return True
                if embassy_owner:
                    if ctx.author == embassy.owner:
                        return True
                if admin_role and config["admin_role"] is not None:
                    if ctx.author in config["admin_role"].members:
                        return True
                if support_role and config["support_role"] is not None:
                    if ctx.author in config["support_role"].members:
                        return True
                if embassy_role and config["embassy_role"] is not None:
                    if ctx.author in config["embassy_role"].members:
                        return True
                if view_role and config["view_role"] is not None:
                    if ctx.author in config["view_role"].members:
                        return True
                if guild_owner:
                    if ctx.author == ctx.guild.owner:
                        return True
                if claim_staff:
                    if ctx.author == embassy.claim:
                        return True
                if members:
                    if ctx.author in embassy.members:
                        return True
                return False
            return True
        return commands.check(pred)

    @commands.guild_only()
    @commands.group(name="embassy")
    async def embassy(self, ctx):
        """Commands for using the embassy system."""

    @embassy.command(name="create")
    async def command_create(self, ctx, *, reason: typing.Optional[str]="No reason provided."):
        """Create a embassy.
        """
        config = await self.bot.get_cog("EmbassyTool").get_config(ctx.guild)
        limit = config["nb_max"]
        category_open = config["category_open"]
        category_close = config["category_close"]
        if not config["enable"]:
            await ctx.send(f"The embassy system is not activated on this server. Please ask an administrator of this server to use the `{ctx.prefix}embassyset` subcommands to configure it.")
            return
        if not await self.bot.get_cog("EmbassyTool").check_limit(ctx.author):
            await ctx.send(f"Sorry. You have already reached the limit of {limit} open embassys.")
            return
        if not category_open.permissions_for(ctx.guild.me).manage_channels or not category_close.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send("The bot does not have `manage_channels` permission on the 'open' and 'close' categories to allow the embassy system to function properly. Please notify an administrator of this server.")
            return
        embassy = Embassy.instance(ctx, reason)
        await embassy.create()
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, embassy_check=True, status=None, embassy_owner=True, admin_role=True, support_role=False, embassy_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @embassy.command(name="export")
    async def command_export(self, ctx):
        """Export all the messages of an existing embassy in html format.
        Please note: all attachments and user avatars are saved with the Discord link in this file.
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        transcript = await chat_exporter.export(embassy.channel, embassy.guild)
        if not transcript is None:
            file = discord.File(io.BytesIO(transcript.encode()),
                                filename=f"transcript-embassy-{embassy.id}.html")
        await ctx.send("Here is the html file of the transcript of all the messages in this embassy.\nPlease note: all attachments and user avatars are saved with the Discord link in this file.", file=file)
        await ctx.tick(message="Done.")

    @decorator(enable_check=True, embassy_check=True, status="close", embassy_owner=True, admin_role=True, support_role=False, embassy_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @embassy.command(name="open")
    async def command_open(self, ctx, *, reason: typing.Optional[str]="No reason provided."):
        """Open an existing embassy.
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        embassy.reason = reason
        await embassy.open(ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, embassy_check=True, status="open", embassy_owner=True, admin_role=True, support_role=True, embassy_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @embassy.command(name="close")
    async def command_close(self, ctx, confirmation: typing.Optional[bool]=None, *, reason: typing.Optional[str]="No reason provided."):
        """Close an existing embassy.
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        config = await self.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        if confirmation is None:
            config = await self.bot.get_cog("EmbassyTool").get_config(embassy.guild)
            confirmation = not config["close_confirmation"]
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = f"Do you really want to close the embassy {embassy.id}?"
            embed.color = config["color"]
            embed.set_author(name=ctx.author.name, url=ctx.author.avatar_url, icon_url=ctx.author.avatar_url)
            response = await utils(embassy.bot).ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        embassy.reason = reason
        await embassy.close(ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, embassy_check=True, status=None, embassy_owner=True, admin_role=True, support_role=True, embassy_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @embassy.command(name="rename")
    async def command_rename(self, ctx, new_name: str, *, reason: typing.Optional[str]="No reason provided."):
        """Rename an existing embassy.
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        embassy.reason = reason
        await embassy.rename(new_name, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, embassy_check=True, status=None, embassy_owner=True, admin_role=True, support_role=False, embassy_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @embassy.command(name="delete")
    async def command_delete(self, ctx, confirmation: typing.Optional[bool]=False, *, reason: typing.Optional[str]="No reason provided."):
        """Delete an existing embassy.
        If a log channel is defined, an html file containing all the messages of this embassy will be generated.
        (Attachments are not supported, as they are saved with their Discord link)
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        config = await self.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        if not confirmation:
            embed: discord.Embed = discord.Embed()
            embed.title = f"Do you really want to delete all the messages of the embassy {embassy.id}?"
            embed.description = "If a log channel is defined, an html file containing all the messages of this embassy will be generated. (Attachments are not supported, as they are saved with their Discord link)"
            embed.color = config["color"]
            embed.set_author(name=ctx.author.name, url=ctx.author.avatar_url, icon_url=ctx.author.avatar_url)
            response = await utils(embassy.bot).ConfirmationAsk(ctx, embed=embed)
            if not response:
                return
        embassy.reason = reason
        await embassy.delete(ctx.author)

    @decorator(enable_check=False, embassy_check=True, status="open", embassy_owner=False, admin_role=True, support_role=True, embassy_role=False, view_role=False, guild_owner=True, claim=False, claim_staff=False, members=False)
    @embassy.command(name="claim")
    async def command_claim(self, ctx, member: typing.Optional[discord.Member]=None, *, reason: typing.Optional[str]="No reason provided."):
        """Claim an existing embassy.
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        embassy.reason = reason
        if member is None:
            member = ctx.author
        await embassy.claim_embassy(member, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, embassy_check=True, status=None, embassy_owner=False, admin_role=True, support_role=False, embassy_role=False, view_role=False, guild_owner=True, claim=True, claim_staff=True, members=False)
    @embassy.command(name="unclaim")
    async def command_unclaim(self, ctx, *, reason: typing.Optional[str]="No reason provided."):
        """Unclaim an existing embassy.
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        embassy.reason = reason
        await embassy.unclaim_embassy(embassy.claim, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, embassy_check=True, status="open", embassy_owner=True, admin_role=True, support_role=False, embassy_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=False, members=False)
    @embassy.command(name="owner")
    async def command_owner(self, ctx, new_owner: discord.Member, *, reason: typing.Optional[str]="No reason provided."):
        """Change the owner of an existing embassy.
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        embassy.reason = reason
        if new_owner is None:
            new_owner = ctx.author
        await embassy.change_owner(new_owner, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, embassy_check=True, status="open", embassy_owner=True, admin_role=True, support_role=False, embassy_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @embassy.command(name="add")
    async def command_add(self, ctx, member: discord.Member, *, reason: typing.Optional[str]="No reason provided."):
        """Add a member to an existing embassy.
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        embassy.reason = reason
        await embassy.add_member(member, ctx.author)
        await ctx.tick(message="Done.")

    @decorator(enable_check=False, embassy_check=True, status=None, embassy_owner=True, admin_role=True, support_role=False, embassy_role=False, view_role=False, guild_owner=True, claim=None, claim_staff=True, members=False)
    @embassy.command(name="remove")
    async def command_remove(self, ctx, member: discord.Member, *, reason: typing.Optional[str]="No reason provided."):
        """Remove a member to an existing embassy.
        """
        embassy = await self.bot.get_cog("EmbassyTool").get_embassy(ctx.channel)
        embassy.reason = reason
        await embassy.remove_member(member, ctx.author)
        await ctx.tick(message="Done.")

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        if inter.clicked_button.custom_id == "close_embassy_button":
            permissions = inter.channel.permissions_for(inter.author)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = inter.channel.permissions_for(inter.guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            embassy = await self.bot.get_cog("EmbassyTool").get_embassy(inter.channel)
            if embassy is not None:
                if embassy.status == "open":
                    async for message in inter.channel.history(limit=1):
                        p = await self.bot.get_valid_prefixes()
                        p = p[0]
                        msg = copy(message)
                        msg.author = inter.author
                        msg.content = f"{p}embassy close"
                        inter.bot.dispatch("message", msg)
                    await inter.send(f"You have chosen to close this embassy. If this embassy is not closed, you do not have the necessary permissions.", ephemeral=True)
        if inter.clicked_button.custom_id == "claim_embassy_button":
            permissions = inter.channel.permissions_for(inter.author)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = inter.channel.permissions_for(inter.guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            embassy = await self.bot.get_cog("EmbassyTool").get_embassy(inter.channel)
            if embassy is not None:
                if embassy.claim is None:
                    async for message in inter.channel.history(limit=1):
                        p = await self.bot.get_valid_prefixes()
                        p = p[0]
                        msg = copy(message)
                        msg.author = inter.author
                        msg.content = f"{p}embassy claim"
                        inter.bot.dispatch("message", msg)
                    await inter.send(f"You have chosen to claim this embassy. If this embassy is not claimed, you do not have the necessary permissions.", ephemeral=True)
        if inter.clicked_button.custom_id == "create_embassy_button":
            permissions = inter.channel.permissions_for(inter.author)
            if not permissions.read_messages and not permissions.send_messages:
                return
            permissions = inter.channel.permissions_for(inter.guild.me)
            if not permissions.read_messages and not permissions.read_message_history:
                return
            async for message in inter.channel.history(limit=1):
                p = await self.bot.get_valid_prefixes()
                p = p[0]
                msg = copy(message)
                msg.author = inter.author
                msg.content = f"{p}embassy create"
                inter.bot.dispatch("message", msg)
            await inter.send(f"Your embassy has been created!.", ephemeral=True)
        return

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, old_channel: discord.abc.GuildChannel):
        data = await self.bot.get_cog("EmbassyTool").data.guild(old_channel.guild).embassys.all()
        if not str(old_channel.id) in data:
            return
        del data[str(old_channel.id)]
        await self.bot.get_cog("EmbassyTool").data.guild(old_channel.guild).embassys.set(data)
        return

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = await self.bot.get_cog("EmbassyTool").get_config(member.guild)
        data = await self.bot.get_cog("EmbassyTool").data.guild(member.guild).embassys.all()
        if config["close_on_leave"]:
            for channel in data:
                channel = member.guild.get_channel(int(channel))
                embassy = await self.bot.get_cog("EmbassyTool").get_embassy(channel)
                if embassy.owner == member and embassy.status == "open":
                    await embassy.close(embassy.guild.me)
        return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id:
            return
        guild = payload.member.guild
        channel = guild.get_channel(payload.channel_id)
        member = guild.get_member(payload.user_id)
        if member == guild.me or member.bot:
            return
        config = await self.bot.get_cog("EmbassyTool").get_config(guild)
        if config["enable"]:
            if config["create_on_react"]:
                if str(payload.emoji) == str("🎟️"):
                    permissions = channel.permissions_for(member)
                    if not permissions.read_messages and not permissions.send_messages:
                        return
                    permissions = channel.permissions_for(guild.me)
                    if not permissions.read_messages and not permissions.read_message_history:
                        return
                    async for message in channel.history(limit=1):
                        p = await self.bot.get_valid_prefixes()
                        p = p[0]
                        msg = copy(message)
                        msg.author = member
                        msg.content = f"{p}embassy create"
                        self.bot.dispatch("message", msg)
        return

class Embassy:
    """Representation of a embassy"""

    def __init__(self,
                bot,
                id,
                owner,
                guild,
                channel,
                claim,
                created_by,
                opened_by,
                closed_by,
                deleted_by,
                renamed_by,
                members,
                created_at,
                opened_at,
                closed_at,
                deleted_at,
                renamed_at,
                status,
                reason,
                logs_messages,
                save_data,
                first_message):
        self.bot: Red = bot
        self.id: int = id
        self.owner: discord.Member = owner
        self.guild: discord.Guild = guild
        self.channel: discord.TextChannel = channel
        self.claim: discord.Member = claim
        self.created_by: discord.Member = created_by
        self.opened_by: discord.Member = opened_by
        self.closed_by: discord.Member = closed_by
        self.deleted_by: discord.Member = deleted_by
        self.renamed_by: discord.Member = renamed_by
        self.members: typing.List[discord.Member] = members
        self.created_at: datetime.datetime = created_at
        self.opened_at: datetime.datetime = opened_at
        self.closed_at: datetime.datetime = closed_at
        self.deleted_at: datetime.datetime = deleted_at
        self.renamed_at: datetime.datetime = renamed_at
        self.status: str = status
        self.reason: str = reason
        self.logs_messages: bool = logs_messages
        self.save_data: bool = save_data
        self.first_message: discord.Message = first_message

    @staticmethod
    def instance(ctx, reason: typing.Optional[str]="No reason provided."):
        embassy = Embassy(
            bot=ctx.bot,
            id=None,
            owner=ctx.author,
            guild=ctx.guild,
            channel=None,
            claim=None,
            created_by=ctx.author,
            opened_by=ctx.author,
            closed_by=None,
            deleted_by=None,
            renamed_by=None,
            members=[],
            created_at=datetime.datetime.now(),
            opened_at=None,
            closed_at=None,
            deleted_at=None,
            renamed_at=None,
            status="open",
            reason=reason,
            logs_messages=True,
            save_data=True,
            first_message=None,
        )
        return embassy

    @staticmethod
    def from_json(json: dict, bot: Red):
        embassy = Embassy(
            bot=bot,
            id=json["id"],
            owner=json["owner"],
            guild=json["guild"],
            channel=json["channel"],
            claim=json["claim"],
            created_by=json["created_by"],
            opened_by=json["opened_by"],
            closed_by=json["closed_by"],
            deleted_by=json["deleted_by"],
            renamed_by=json["renamed_by"],
            members=json["members"],
            created_at=json["created_at"],
            opened_at=json["opened_at"],
            closed_at=json["closed_at"],
            deleted_at=json["deleted_at"],
            renamed_at=json["renamed_at"],
            status=json["status"],
            reason=json["reason"],
            logs_messages=json["logs_messages"],
            save_data=json["save_data"],
            first_message=json["first_message"],
        )
        return embassy

    async def save(embassy):
        if not embassy.save_data:
            return
        bot = embassy.bot
        guild = embassy.guild
        channel = embassy.channel
        embassy.bot = None
        if embassy.owner is not None:
            embassy.owner = int(embassy.owner.id)
        if embassy.guild is not None:
            embassy.guild = int(embassy.guild.id)
        if embassy.channel is not None:
            embassy.channel = int(embassy.channel.id)
        if embassy.claim is not None:
            embassy.claim = embassy.claim.id
        if embassy.created_by is not None:
            embassy.created_by = int(embassy.created_by.id)
        if embassy.opened_by is not None:
            embassy.opened_by = int(embassy.opened_by.id)
        if embassy.closed_by is not None:
            embassy.closed_by = int(embassy.closed_by.id)
        if embassy.deleted_by is not None:
            embassy.deleted_by = int(embassy.deleted_by.id)
        if embassy.renamed_by is not None:
            embassy.renamed_by = int(embassy.renamed_by.id)
        members = embassy.members
        embassy.members = []
        for m in members:
            embassy.members.append(int(m.id))
        if embassy.created_at is not None:
            embassy.created_at = float(datetime.datetime.timestamp(embassy.created_at))
        if embassy.opened_at is not None:
            embassy.opened_at = float(datetime.datetime.timestamp(embassy.opened_at))
        if embassy.closed_at is not None:
            embassy.closed_at = float(datetime.datetime.timestamp(embassy.closed_at))
        if embassy.deleted_at is not None:
            embassy.deleted_at = float(datetime.datetime.timestamp(embassy.deleted_at))
        if embassy.renamed_at is not None:
            embassy.renamed_at = float(datetime.datetime.timestamp(embassy.renamed_at))
        if embassy.first_message is not None:
            embassy.first_message = int(embassy.first_message.id)
        json = embassy.__dict__
        data = await bot.get_cog("EmbassyTool").data.guild(guild).embassys.all()
        data[str(channel.id)] = json
        await bot.get_cog("EmbassyTool").data.guild(guild).embassys.set(data)
        return data
    
    async def create(embassy, name: typing.Optional[str]="embassy"):
        config = await embassy.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        logschannel = config["logschannel"]
        overwrites = await utils(embassy.bot).get_overwrites(embassy)
        emoji_open = config["emoji_open"]
        ping_role = config["ping_role"]
        embassy.id = config["last_nb"] + 1
        name = f"{emoji_open}-{name}-{embassy.id}"
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=embassy.created_by, reason=f"Creating the embassy {embassy.id}.")
        embassy.channel = await embassy.guild.create_text_channel(
                            name,
                            overwrites=overwrites,
                            category=config["category_open"],
                            topic=embassy.reason,
                            reason=reason,
                         )
        if config["create_modlog"]:
            await embassy.bot.get_cog("EmbassyTool").create_modlog(embassy, "embassy_created", reason)
        if embassy.logs_messages:
            buttons = ActionRow(
                Button(
                    style=ButtonStyle.grey,
                    label="Close",
                    emoji="🔒",
                    custom_id="close_embassy_button",
                    disabled=False
                ),
                Button(
                    style=ButtonStyle.grey,
                    label="Claim",
                    emoji="🙋‍♂️",
                    custom_id="claim_embassy_button",
                    disabled=False
                )
            )
            if ping_role is not None:
                optionnal_ping = f" ||{ping_role.mention}||"
            else:
                optionnal_ping = ""
            embed = await embassy.bot.get_cog("EmbassyTool").get_embed_important(embassy, False, author=embassy.created_by, title="Embassy Created", description="Thank you for creating a embassy on this server!")
            embassy.first_message = await embassy.channel.send(f"{embassy.created_by.mention}{optionnal_ping}", embed=embed, components=[buttons])
            if logschannel is not None:
                embed = await embassy.bot.get_cog("EmbassyTool").get_embed_important(embassy, True, author=embassy.created_by, title="Embassy Created", description=f"The embassy was created by {embassy.created_by}.")
                await logschannel.send(f"Report on the creation of the embassy {embassy.id}.", embed=embed)
        await embassy.bot.get_cog("EmbassyTool").data.guild(embassy.guild).settings.last_nb.set(embassy.id)
        if config["embassy_role"] is not None:
            if embassy.owner:
                try:
                    embassy.owner.add_roles(config["embassy_role"], reason=reason)
                except discord.HTTPException:
                    pass
        await embassy.save()
        return embassy

    async def export(embassy):
        if embassy.channel:
            transcript = await chat_exporter.export(embassy.channel, embassy.guild)
            if not transcript is None:
                transcript_file = discord.File(io.BytesIO(transcript.encode()),
                                  filename=f"transcript-embassy-{embassy.id}.html")
                return transcript_file
        return None

    async def open(embassy, author: typing.Optional[discord.Member]=None):
        config = await embassy.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=author, reason=f"Opening the embassy {embassy.id}.")
        logschannel = config["logschannel"]
        emoji_open = config["emoji_open"]
        emoji_close = config["emoji_close"]
        embassy.status = "open"
        embassy.opened_by = author
        embassy.opened_at = datetime.datetime.now()
        embassy.closed_by = None
        embassy.closed_at = None
        new_name = f"{embassy.channel.name}"
        new_name = new_name.replace(f"{emoji_close}-", "", 1)
        new_name = f"{emoji_open}-{new_name}"
        await embassy.channel.edit(name=new_name, category=config["category_open"], reason=reason)
        if embassy.logs_messages:
            embed = await embassy.bot.get_cog("EmbassyTool").get_embed_action(embassy, author=embassy.opened_by, action="Embassy Opened")
            await embassy.channel.send(embed=embed)
            if logschannel is not None:
                embed = await embassy.bot.get_cog("EmbassyTool").get_embed_important(embassy, True, author=embassy.opened_by, title="Embassy Opened", description=f"The embassy was opened by {embassy.opened_by}.")
                await logschannel.send(f"Report on the close of the embassy {embassy.id}.", embed=embed)
        if embassy.first_message is not None:
            try:
                buttons = ActionRow(
                    Button(
                        style=ButtonStyle.grey,
                        label="Close",
                        emoji="🔒",
                        custom_id="close_embassy_button",
                        disabled=False
                    ),
                    Button(
                        style=ButtonStyle.grey,
                        label="Claim",
                        emoji="🙋‍♂️",
                        custom_id="claim_embassy_button",
                        disabled=False
                    )
                )
                embassy.first_message = await embassy.channel.fetch_message(int(embassy.first_message.id))
                await embassy.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await embassy.save()
        return embassy
    
    async def close(embassy, author: typing.Optional[discord.Member]=None):
        config = await embassy.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=author, reason=f"Closing the embassy {embassy.id}.")
        logschannel = config["logschannel"]
        emoji_open = config["emoji_open"]
        emoji_close = config["emoji_close"]
        embassy.status = "close"
        embassy.closed_by = author
        embassy.closed_at = datetime.datetime.now()
        new_name = f"{embassy.channel.name}"
        new_name = new_name.replace(f"{emoji_open}-", "", 1)
        new_name = f"{emoji_close}-{new_name}"
        await embassy.channel.edit(name=new_name, category=config["category_close"], reason=reason)
        if embassy.logs_messages:
            embed = await embassy.bot.get_cog("EmbassyTool").get_embed_action(embassy, author=embassy.closed_by, action="Embassy Closed")
            await embassy.channel.send(embed=embed)
            if logschannel is not None:
                embed = await embassy.bot.get_cog("EmbassyTool").get_embed_important(embassy, True, author=embassy.closed_by, title="Embassy Closed", description=f"The embassy was closed by {embassy.closed_by}.")
                await logschannel.send(f"Report on the close of the embassy {embassy.id}.", embed=embed)
        if embassy.first_message is not None:
            try:
                buttons = ActionRow(
                    Button(
                        style=ButtonStyle.grey,
                        label="Close",
                        emoji="🔒",
                        custom_id="close_embassy_button",
                        disabled=True
                    ),
                    Button(
                        style=ButtonStyle.grey,
                        label="Claim",
                        emoji="🙋‍♂️",
                        custom_id="claim_embassy_button",
                        disabled=True
                    )
                )
                embassy.first_message = await embassy.channel.fetch_message(int(embassy.first_message.id))
                await embassy.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await embassy.save()
        return embassy

    async def rename(embassy, new_name: str, author: typing.Optional[discord.Member]=None):
        config = await embassy.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=author, reason=f"Renaming the embassy {embassy.id}. (`{embassy.channel.name}` to `{new_name}`)")
        emoji_open = config["emoji_open"]
        emoji_close = config["emoji_close"]
        embassy.renamed_by = author
        embassy.renamed_at = datetime.datetime.now()
        if embassy.status == "open":
            new_name = f"{emoji_open}-{new_name}"
        elif embassy.status == "close":
            new_name = f"{emoji_close}-{new_name}"
        else:
            new_name = f"{new_name}"
        await embassy.channel.edit(name=new_name, reason=reason)
        if embassy.logs_messages:
            embed = await embassy.bot.get_cog("EmbassyTool").get_embed_action(embassy, author=embassy.renamed_by, action="Embassy Renamed")
            await embassy.channel.send(embed=embed)
        await embassy.save()
        return embassy

    async def delete(embassy, author: typing.Optional[discord.Member]=None):
        config = await embassy.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        logschannel = config["logschannel"]
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=author, reason=f"Deleting the embassy {embassy.id}.")
        embassy.deleted_by = author
        embassy.deleted_at = datetime.datetime.now()
        if embassy.logs_messages:
            if logschannel is not None:
                embed = await embassy.bot.get_cog("EmbassyTool").get_embed_important(embassy, True, author=embassy.deleted_by, title="Embassy Deleted", description=f"The embassy was deleted by {embassy.deleted_by}.")
                transcript = await chat_exporter.export(embassy.channel, embassy.guild)
                if not transcript is None:
                    file = discord.File(io.BytesIO(transcript.encode()),
                                        filename=f"transcript-embassy-{embassy.id}.html")
                await logschannel.send(f"Report on the deletion of the embassy {embassy.id}.", embed=embed, file=file)
        await embassy.channel.delete(reason=reason)
        data = await embassy.bot.get_cog("EmbassyTool").data.guild(embassy.guild).embassys.all()
        del data[str(embassy.channel.id)]
        await embassy.bot.get_cog("EmbassyTool").data.guild(embassy.guild).embassys.set(data)
        return embassy

    async def claim_embassy(embassy, member: discord.Member, author: typing.Optional[discord.Member]=None):
        config = await embassy.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=author, reason=f"Claiming the embassy {embassy.id}.")
        if member.bot:
            await embassy.channel.send("A bot cannot claim a embassy.")
            return
        embassy.claim = member
        overwrites = embassy.channel.overwrites
        overwrites[member] = (
            discord.PermissionOverwrite(
                attach_files=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
            )
        )
        if config["support_role"] is not None:
            overwrites[config["support_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=False,
                    attach_files=True,
                )
            )
        await embassy.channel.edit(overwrites=overwrites, reason=reason)
        if embassy.first_message is not None:
            try:
                buttons = ActionRow(
                    Button(
                        style=ButtonStyle.grey,
                        label="Close",
                        emoji="🔒",
                        custom_id="close_embassy_button",
                        disabled=False
                    ),
                    Button(
                        style=ButtonStyle.grey,
                        label="Claim",
                        emoji="🙋‍♂️",
                        custom_id="claim_embassy_button",
                        disabled=True
                    )
                )
                embassy.first_message = await embassy.channel.fetch_message(int(embassy.first_message.id))
                await embassy.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await embassy.save()
        return embassy

    async def unclaim_embassy(embassy, member: discord.Member, author: typing.Optional[discord.Member]=None):
        config = await embassy.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=author, reason=f"Claiming the embassy {embassy.id}.")
        embassy.claim = None
        if config["support_role"] is not None:
            overwrites = embassy.channel.overwrites
            overwrites[config["support_role"]] = (
                discord.PermissionOverwrite(
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    attach_files=True,
                )
            )
            await embassy.channel.edit(overwrites=overwrites, reason=reason)
        await embassy.channel.set_permissions(member, overwrite=None, reason=reason)
        if embassy.first_message is not None:
            try:
                buttons = ActionRow(
                    Button(
                        style=ButtonStyle.grey,
                        label="Close",
                        emoji="🔒",
                        custom_id="close_embassy_button",
                        disabled=False if embassy.status == "open" else True
                    ),
                    Button(
                        style=ButtonStyle.grey,
                        label="Claim",
                        emoji="🙋‍♂️",
                        custom_id="claim_embassy_button",
                        disabled=False
                    )
                )
                embassy.first_message = await embassy.channel.fetch_message(int(embassy.first_message.id))
                await embassy.first_message.edit(components=[buttons])
            except discord.HTTPException:
                pass
        await embassy.save()
        return embassy

    async def change_owner(embassy, member: discord.Member, author: typing.Optional[discord.Member]=None):
        config = await embassy.bot.get_cog("EmbassyTool").get_config(embassy.guild)
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=author, reason=f"Changing owner of the embassy {embassy.id}.")
        if member.bot:
            await embassy.channel.send("You cannot transfer ownership of a embassy to a bot.")
            return
        if config["embassy_role"] is not None:
            if embassy.owner:
                try:
                    embassy.owner.remove_roles(config["embassy_role"], reason=reason)
                except discord.HTTPException:
                    pass
        embassy.members.append(embassy.owner)
        embassy.owner = member
        embassy.remove(embassy.owner)
        overwrites = embassy.channel.overwrites
        overwrites[member] = (
            discord.PermissionOverwrite(
                attach_files=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
            )
        )
        await embassy.channel.edit(overwrites=overwrites, reason=reason)
        if config["embassy_role"] is not None:
            if embassy.owner:
                try:
                    embassy.owner.add_roles(config["embassy_role"], reason=reason)
                except discord.HTTPException:
                    pass
        if embassy.logs_messages:
            embed = await embassy.bot.get_cog("EmbassyTool").get_embed_action(embassy, author=author, action="Owner Modified")
            await embassy.channel.send(embed=embed)
        await embassy.save()
        return embassy

    async def add_member(embassy, member: discord.Member, author: typing.Optional[discord.Member]=None):
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=author, reason=f"Adding a member to the embassy {embassy.id}.")
        if member.bot:
            await embassy.channel.send("You cannot add a bot to a embassy.")
            return
        if member in embassy.members:
            await embassy.channel.send("This member already has access to this embassy.")
            return
        if member == embassy.owner:
            await embassy.channel.send("This member is already the owner of this embassy.")
            return
        embassy.members.append(member)
        overwrites = embassy.channel.overwrites
        overwrites[member] = (
            discord.PermissionOverwrite(
                attach_files=True,
                read_messages=True,
                read_message_history=True,
                send_messages=True,
            )
        )
        await embassy.channel.edit(overwrites=overwrites, reason=reason)
        if embassy.logs_messages:
            embed = await embassy.bot.get_cog("EmbassyTool").get_embed_action(embassy, author=author, action=f"Member {member.mention} ({member.id}) Added")
            await embassy.channel.send(embed=embed)
        await embassy.save()
        return embassy

    async def remove_member(embassy, member: discord.Member, author: typing.Optional[discord.Member]=None):
        reason = await embassy.bot.get_cog("EmbassyTool").get_audit_reason(guild=embassy.guild, author=author, reason=f"Removing a member to the embassy {embassy.id}.")
        if member.bot:
            await embassy.channel.send("You cannot remove a bot to a embassy.")
            return
        if not member in embassy.members:
            await embassy.channel.send("This member is not in the list of those authorised to access the embassy.")
            return
        embassy.members.remove(member)
        await embassy.channel.set_permissions(member, overwrite=None, reason=reason)
        if embassy.logs_messages:
            embed = await embassy.bot.get_cog("EmbassyTool").get_embed_action(embassy, author=author, action=f"Member {member.mention} ({member.id}) Removed")
            await embassy.channel.send(embed=embed)
        await embassy.save()
        return embassy

import discord
from discord.ext import commands
from discord import app_commands
import io
import aiohttp
import asyncio

TOKEN = "MTM5Njc1OTc1NjA2NDE2MTkyNA.GOZJ9S.eWOLdDUgPtKwX9ex4KXBVWfVHPM79tkkxUEg24"
GUILD_ID = 1396756235285692436
STAFF_ROLE_ID = 1396760211066327050
WEBHOOK_URL = "https://discord.com/api/webhooks/1396785652426735697/jFucrGIcfKiqn15rxi5_LbSPKJEpPgwSBQaP8n8Myx0d2zVAJcSMlRUPoXX4Be3yS86q"

# Map ticket types to your category IDs
CATEGORY_MAP = {
    "exploiter report": 1396782108885909524,     # replace with your Support category ID
    "buy stuff": 1396782941132165131,      # replace with your Reports category ID
}

TICKET_OPTIONS = [
    {"label": "exploiter report", "description": "report an exploiter", "emoji": "🛠️"},
    {"label": "buy stuff", "description": "buy stuff?", "emoji": "💸"},
]

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

class CloseTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        member = interaction.user

        # Check staff role
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        if staff_role not in member.roles:
            await interaction.response.send_message("u arent whitelisted LOL", ephemeral=True)
            return

        closer_name = f"{member.name}#{member.discriminator}"
        await channel.send(f"🔒 **This ticket is being closed by `{closer_name}`...**")

        # Collect all messages for transcript
        messages = []
        async for msg in channel.history(limit=None, oldest_first=True):
            content = msg.content if msg.content else "[Embed/Attachment]"
            messages.append(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author.display_name}: {content}")

        transcript_text = "\n".join(messages) if messages else "No messages in this ticket."
        transcript_file = discord.File(
            io.BytesIO(transcript_text.encode()),
            filename=f"{channel.name}-transcript.txt"
        )

        # Find opener user from first few messages
        opener_user = None
        async for msg in channel.history(limit=5, oldest_first=True):
            if msg.mentions:
                opener_user = msg.mentions[0]
                break
        opener_name = opener_user.name + "#" + opener_user.discriminator if opener_user else "Unknown"

        # Send transcript to webhook
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
            await webhook.send(
                content=(
                    f" **Ticket Closed:** `{channel.name}`\n"
                    f" **Opened by:** {opener_name}\n"
                    f" **Closed by:** {closer_name}"
                ),
                file=transcript_file
            )

        await asyncio.sleep(3)  # Give users time to see closing message
        await channel.delete(reason="Ticket closed")

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton())

class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=opt["label"],
                description=opt["description"],
                emoji=opt.get("emoji")
            ) for opt in TICKET_OPTIONS
        ]
        super().__init__(
            placeholder="Choose a ticket type...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        guild = interaction.guild
        user = interaction.user

        # === COOLDOWN: Check if user already has a ticket open ===
        existing_ticket = None
        for channel in guild.text_channels:
            if channel.name.startswith(f"ticket-{user.name.lower()}"):
                existing_ticket = channel
                break

        if existing_ticket:
            await interaction.response.send_message(
                f"You already have an open ticket: {existing_ticket.mention}",
                ephemeral=True
            )
            return

        # Get the right category for ticket type
        category_id = CATEGORY_MAP.get(ticket_type)
        category = guild.get_channel(category_id) if category_id else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel_name = f"ticket-{user.name.lower()}-{ticket_type.lower()}"
        ticket_channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            reason="Ticket created",
            category=category
        )

        embed = discord.Embed(
            title="🎟️ Ticket Created",
            description="**Support will be here shortly, please wait. if its an exploiter report please provide a clip**",
            color=discord.Color.green()
        )
        embed.add_field(name="Ticket Type", value=f"**{ticket_type}**", inline=False)
        embed.set_footer(text=f"Opened by {user.name}", icon_url=user.display_avatar.url)

        close_view = CloseTicketView()
        await ticket_channel.send(content=f"{user.mention}", embed=embed, view=close_view)

        await interaction.response.send_message(
            f"Your ticket has been created @ {ticket_channel.mention}",
            ephemeral=True
        )

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

@bot.tree.command(name="setup", description="Set up the ticket panel")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title=" Dav hood's Ticket System",
        description="Select a dropdown for exploiter reports or to buy stuff.",
        color=discord.Color.blurple()
    )
    view = TicketView()
    await interaction.response.send_message("✅ Ticket panel created!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)

@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import datetime
from database import (
    init_db, save_ticket, update_ticket,
    mark_ticket_completed, delete_ticket,
    export_ticket_performance_to_csv
)

# ---------------------- CONFIGURATION ----------------------
load_dotenv()

CONFIG = {
    "TOKEN": os.getenv("DISCORD_TOKEN"),
    "TICKET_PARENT_CHANNEL_ID": 1362136021818409010,
    "PM_ROLE_IDS": [1337140702718595172],
    "TEAM_MENTION_MAP": {
        "Design Team": "<@&123456789012345678>",
        "Development Team": "<@&123456789012345679>",
        "Voice Team": "<@&123456789012345680>",
        "Content Team": "<@&123456789012345681>",
    }
}

# ---------------------- DISCORD SETUP ----------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
ticket_counter = 1

# ---------------------- UI COMPONENTS ----------------------
class UpdateTicketModal(discord.ui.Modal, title="Update Ticket Details"):
    def __init__(self, message):
        super().__init__()
        self.message = message
        self.add_item(discord.ui.TextInput(label="Assigned Team", placeholder="e.g. Design Team"))
        self.add_item(discord.ui.TextInput(label="Priority", placeholder="Low, Medium, High, Critical"))
        self.add_item(discord.ui.TextInput(label="Deadline (DD-MM-YYYY)", placeholder="e.g. 25-04-2025"))

    async def on_submit(self, interaction: discord.Interaction):
        member = await interaction.guild.fetch_member(interaction.user.id)
        if not any(role.id in CONFIG["PM_ROLE_IDS"] for role in member.roles):
            await interaction.response.send_message("❌ You are not authorized to update tickets.", ephemeral=True)
            return

        old_embed = self.message.embeds[0]
        new_embed = discord.Embed(title=old_embed.title, description=old_embed.description, color=old_embed.color)
        new_embed.set_footer(text=old_embed.footer.text)

        try:
            deadline = datetime.datetime.strptime(self.children[2].value, "%d-%m-%Y").strftime("%d %b %Y")
        except ValueError:
            await interaction.response.send_message("❌ Invalid deadline format. Use DD-MM-YYYY.", ephemeral=True)
            return

        assigned_team = self.children[0].value
        priority = self.children[1].value
        mention = CONFIG["TEAM_MENTION_MAP"].get(assigned_team, "")

        new_embed.add_field(name="Assigned Team", value=f"{assigned_team} {mention}", inline=False)
        new_embed.add_field(name="Priority", value=priority, inline=False)
        new_embed.add_field(name="Deadline", value=deadline, inline=False)

        await self.message.edit(embed=new_embed)
        await interaction.response.send_message(f"✅ Ticket updated and assigned to {assigned_team}!", ephemeral=True)
        await self.message.channel.send(f"📢 Ticket updated — {mention}", delete_after=10)

        update_ticket(str(self.message.channel.id), assigned_team, priority, deadline)

class UpdateTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="✏️ Update Ticket", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        member = await interaction.guild.fetch_member(interaction.user.id)
        if not any(role.id in CONFIG["PM_ROLE_IDS"] for role in member.roles):
            await interaction.response.send_message("❌ You are not authorized to update tickets.", ephemeral=True)
            return
        await interaction.response.send_modal(UpdateTicketModal(self.view.message))

class CompleteButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="✅ Mark as Completed", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        thread = interaction.channel
        embed = self.view.message.embeds[0]
        if not embed.title.startswith("✅ Completed"):
            embed.title = f"✅ Completed Ticket: {embed.title[2:] if embed.title.startswith('📩') else embed.title}"
        await self.view.message.edit(embed=embed)
        await interaction.response.send_message("✅ Ticket marked as completed!", ephemeral=True)

        try:
            await thread.send("📁 This thread will now be archived.", delete_after=10)
            await thread.edit(archived=True)
        except Exception as e:
            print(f"❌ Failed to archive thread: {e}")

        mark_ticket_completed(str(thread.id))

class DeleteTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🗑️ Delete Ticket", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        member = await interaction.guild.fetch_member(interaction.user.id)
        if not any(role.id in CONFIG["PM_ROLE_IDS"] for role in member.roles):
            await interaction.response.send_message("❌ You are not authorized to delete tickets.", ephemeral=True)
            return

        thread = interaction.channel
        delete_ticket(str(thread.id))
        await interaction.response.send_message("🗑️ Ticket deleted from system. Archiving thread...", ephemeral=True)
        await thread.send("🗑️ This ticket has been permanently removed.", delete_after=10)
        await thread.edit(archived=True, locked=True)

class PMActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.message = None
        self.add_item(UpdateTicketButton())
        self.add_item(CompleteButton())
        self.add_item(DeleteTicketButton())

# ---------------------- TICKET HANDLERS ----------------------
class TicketModal(discord.ui.Modal, title="Submit a Ticket"):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.TextInput(label="Ticket Title", placeholder="e.g. Design new landing page"))
        self.add_item(discord.ui.TextInput(label="Description", style=discord.TextStyle.long, placeholder="Describe the task", max_length=1000))

    async def on_submit(self, interaction: discord.Interaction):
        global ticket_counter
        title = self.children[0].value
        description = self.children[1].value
        thread_name = f"ticket-{ticket_counter:04d} | {title[:30]}"
        ticket_counter += 1

        parent_channel = await bot.fetch_channel(CONFIG["TICKET_PARENT_CHANNEL_ID"])
        thread = await parent_channel.create_thread(name=thread_name, type=discord.ChannelType.public_thread, reason="New ticket")

        embed = discord.Embed(title=f"📩 New Ticket: {title}", description=description, color=discord.Color.blurple())
        embed.set_footer(text=f"Submitted by {interaction.user.display_name}")
        await interaction.response.send_message("✅ Ticket created! Check the thread.", ephemeral=True)

        save_ticket({
            "title": title,
            "description": description,
            "assigned_team": "",
            "priority": "",
            "deadline": "",
            "submitted_by": interaction.user.display_name,
            "thread_id": str(thread.id)
        })

        view = PMActionView()
        msg = await thread.send(f"📬 Ticket submitted by {interaction.user.mention}", embed=embed, view=view)
        view.message = msg
        await post_ticket_button()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Open Ticket", style=discord.ButtonStyle.primary)
    async def open_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

async def post_ticket_button():
    channel = await bot.fetch_channel(CONFIG["TICKET_PARENT_CHANNEL_ID"])
    async for msg in channel.history(limit=50):
        if msg.author == bot.user and any(isinstance(component, TicketView) for component in msg.components):
            await msg.delete()
    await channel.send("🎫 Click below to submit a ticket:", view=TicketView())

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    init_db()
    await bot.wait_until_ready()
    await post_ticket_button()

# ---------------------- EXPORT COMMAND ----------------------
@bot.command(name="export")
async def export_csv(ctx):
    member = ctx.author
    if not any(role.id in CONFIG["PM_ROLE_IDS"] for role in member.roles):
        await ctx.send("❌ You are not authorized to export tickets.")
        return

    export_ticket_performance_to_csv()
    await ctx.send(file=discord.File("ticket_performance.csv"), content="📊 Ticket performance exported:")

bot.run(CONFIG["TOKEN"])

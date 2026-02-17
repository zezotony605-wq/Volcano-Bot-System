import discord
from discord.ext import commands
from discord import app_commands
import json
import os

from flask import Flask
from threading import Thread

app = Flask('')


@app.route('/')
def home():
    return "Bot is alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


TOKEN = "MTQ3MzAwNDQxNzUzMDcyNDQ3NQ.GJ_S4p.KKs37hRcGDw-uOIbhXmwOTFqnRH5xZoEjknAqU"

LEADER_ROLES = [1472025940791136442, 1470432181401813055]
REGISTER_ROLE = 1470435782442352701

REGISTRATION_CHANNEL_ID = 1470592623894069318  # حط ايدي قناة التسجيل هنا

MIN_TEAM = 3
MAX_TEAM = 25
MAX_TEAMS = 23

DATA_FILE = "teams1.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

registration_open = False

# ================== Data System ==================


def calculate_placement_points(position):
    try:
        position = int(position)
    except:
        return 0

    if position == 1:
        return 15
    elif position == 2:
        return 12
    elif position == 3:
        return 10
    elif position == 4:
        return 6
    elif position == 5:
        return 3
    else:
        return 0


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


data = load_data()

for team in data.values():
    # تأكد من وجود هيكل الرومات
    if "rooms" not in team:
        team["rooms"] = {"1": None, "2": None, "3": None}
    if "kills" not in team:
        team["kills"] = {"1": {}, "2": {}, "3": {}}
    if "total_points" not in team:
        team["total_points"] = 0

    # لو كانت الرومات القديمة مجرد int حوّلها dict
    for room in ["1", "2", "3"]:
        if isinstance(team["kills"].get(room), int):
            # هنا الأفضل تعيين كل لاعب بصفر، أو إذا مش عارف اللاعبين حط Unknown
            team["kills"][room] = {
                player: 0
                for player in team.get("players", ["Unknown"] * 4)
            }

# ================== Role Check ==================


def is_leader(member):
    return any(role.id in LEADER_ROLES for role in member.roles)


def can_register(member):
    return any(role.id == REGISTER_ROLE for role in member.roles)


# ================== Modal ==================


class RegisterModal(discord.ui.Modal, title="تسجيل فريق"):
    team_number = discord.ui.TextInput(label="رقم الفريق (3-25)")
    player1 = discord.ui.TextInput(label="اسم اللاعب 1")
    player2 = discord.ui.TextInput(label="اسم اللاعب 2")
    player3 = discord.ui.TextInput(label="اسم اللاعب 3")
    player4 = discord.ui.TextInput(label="اسم اللاعب 4")

    async def on_submit(self, interaction: discord.Interaction):
        global registration_open
        data = load_data()

        if not can_register(interaction.user):
            return await interaction.response.send_message(
                "❌ ليس لديك صلاحية التسجيل.", ephemeral=True)

        try:
            team_number = int(self.team_number.value)
        except:
            return await interaction.response.send_message("❌ رقم غير صحيح.",
                                                           ephemeral=True)

        if team_number < MIN_TEAM or team_number > MAX_TEAM:
            return await interaction.response.send_message(
                "❌ رقم الفريق يجب أن يكون بين 3 و 25.", ephemeral=True)

        if str(team_number) in data:
            return await interaction.response.send_message(
                "❌ رقم الفريق مستخدم بالفعل.", ephemeral=True)

        if any(team["owner"] == interaction.user.id for team in data.values()):
            return await interaction.response.send_message(
                "❌ لا يمكنك تسجيل أكثر من فريق.", ephemeral=True)

        if len(data) >= MAX_TEAMS:
            registration_open = False
            return await interaction.response.send_message(
                "❌ تم اكتمال العدد وإغلاق التسجيل.", ephemeral=True)

        data[str(team_number)] = {
            "owner":
            interaction.user.id,
            "players": [
                self.player1.value, self.player2.value, self.player3.value,
                self.player4.value
            ]
        }

        save_data(data)

        if len(data) >= MAX_TEAMS:
            registration_open = False

        await interaction.response.send_message(
            f"✅ تم تسجيل فريق رقم {team_number}", ephemeral=True)


class PointsSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="Calculate Points",
                                 description="احسب نقاط الرومات",
                                 emoji="📊"),
            discord.SelectOption(label="Add Points",
                                 description="إضافة نقاط لفريق",
                                 emoji="➕"),
            discord.SelectOption(label="Remove Points",
                                 description="إزالة نقاط من فريق",
                                 emoji="➖"),
            discord.SelectOption(label="Total Points",
                                 description="عرض نقاط الفريق",
                                 emoji="🏆"),
            discord.SelectOption(label="Highest Kills",
                                 description="أعلى 3 لاعبين بالكيلات",
                                 emoji="🔥"),
            discord.SelectOption(label="LeaderBoard",
                                 description="عرض ترتيب كل الفرق",
                                 emoji="📈"),
            discord.SelectOption(label="Reset Points",
                                 description="إعادة ضبط نقاط فريق",
                                 emoji="♻️"),
        ]
        super().__init__(placeholder="اختر خيار من القائمة...",
                         min_values=1,
                         max_values=1,
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        # 🔹 نعيد استخدام الكود الموجود عندك لكل زر
        if choice == "Calculate Points":
            if not (is_leader(interaction.user) or LEADER_ROLES(interaction)):
                return await interaction.response.send_message(
                    "❌ ليس لديك صلاحية.", ephemeral=True)
            await interaction.response.send_message("اختر الروم:",
                                                    view=RoomSelectView(),
                                                    ephemeral=True)

        elif choice == "Add Points":
            await interaction.response.send_modal(AddPointsModal())

        elif choice == "Remove Points":
            await interaction.response.send_modal(RemovePointsModal())

        elif choice == "Total Points":
            await interaction.response.send_modal(TotalPointsModal())

        elif choice == "Highest Kills":
            await highest_kills_logic(interaction)

        elif choice == "LeaderBoard":
            await show_leaderboard(interaction)

        elif choice == "Reset Points":
            if not is_leader(interaction.user):
                return await interaction.response.send_message(
                    "❌ ليس لديك صلاحية.", ephemeral=True)
            await interaction.response.send_modal(ResetPointsModal())


async def highest_kills_logic(interaction: discord.Interaction):
    try:
        data = load_data()  # دالة قراءة بيانات الفرق

        player_totals = {
        }  # {player_name: {"team": team_number, "kills": total_kills}}

        for team_number, team in data.items():
            players = team.get("players",
                               ["Player1", "Player2", "Player3", "Player4"])
            for room in ["1", "2", "3"]:
                kills_data = team.get("kills", {}).get(room, {})
                if isinstance(kills_data, int):
                    kills_data = {player: 0 for player in players}

                for player, kills in kills_data.items():
                    if player not in player_totals:
                        player_totals[player] = {
                            "team": team_number,
                            "kills": 0
                        }
                    player_totals[player]["kills"] += kills

        sorted_players = sorted(player_totals.items(),
                                key=lambda x: x[1]["kills"],
                                reverse=True)
        top3 = sorted_players[:3]

        if not top3:
            return await interaction.response.send_message("لا يوجد بيانات.",
                                                           ephemeral=True)

        embed = discord.Embed(title="🔥 Top 3 Highest Kills (All Rooms)",
                              color=0xff0000)
        for i, (player, info) in enumerate(top3, start=1):
            embed.add_field(
                name=f"#{i} - {player}",
                value=f"Team {info['team']}\nTotal Kills: {info['kills']}",
                inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ حصل خطأ: {e}", ephemeral=True)


async def show_leaderboard(interaction: discord.Interaction):
    data = load_data()  # دالة قراءة بيانات الفرق

    # ترتيب الفرق حسب total_points نزوليًا
    sorted_teams = sorted(data.items(),
                          key=lambda x: x[1].get("total_points", 0),
                          reverse=True)

    embed = discord.Embed(title="🏆 Tournament Leaderboard", color=0x00ff00)

    for position, (team_number, team) in enumerate(sorted_teams, start=1):
        total_kills = 0
        for room in ["1", "2", "3"]:
            room_kills = team.get("kills", {}).get(room, {})
            if isinstance(room_kills, int):
                room_kills = {}
            total_kills += sum(room_kills.values())

        embed.add_field(
            name=f"#{position} - Team {team_number}",
            value=
            f"Points: {team.get('total_points', 0)}\nKills: {total_kills}",
            inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


class PointsView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PointsSelect())  # نضيف الـ Dropdown بدل الأزرار


class RoomSelectView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Room 1", style=discord.ButtonStyle.blurple)
    async def room1(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        await interaction.response.send_modal(CalculateModal("1"))

    @discord.ui.button(label="Room 2", style=discord.ButtonStyle.blurple)
    async def room2(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        await interaction.response.send_modal(CalculateModal("2"))

    @discord.ui.button(label="Room 3", style=discord.ButtonStyle.blurple)
    async def room3(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        await interaction.response.send_modal(CalculateModal("3"))


class CalculateModal(discord.ui.Modal):

    def __init__(self, room_number):
        super().__init__(title=f"حساب نقاط روم {room_number}")
        self.room_number = room_number

        self.team_number = discord.ui.TextInput(label="رقم الفريق")
        self.position = discord.ui.TextInput(label="المركز")

        self.add_item(self.team_number)
        self.add_item(self.position)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        if self.team_number.value not in data:
            return await interaction.response.send_message(
                "❌ الفريق غير موجود.", ephemeral=True)

        try:
            position = int(self.position.value)
        except:
            return await interaction.response.send_message(
                "❌ المركز غير صحيح.", ephemeral=True)

        team = data[self.team_number.value]

        await interaction.response.send_message(
            "اضغط لإدخال الكيلات:",
            view=KillsButtonView(self.room_number, self.team_number.value,
                                 team["players"], position),
            ephemeral=True)


class KillsButtonView(discord.ui.View):

    def __init__(self, room_number, team_number, players, position):
        super().__init__(timeout=120)
        self.room_number = room_number
        self.team_number = team_number
        self.players = players
        self.position = position

    @discord.ui.button(label="Enter Kills", style=discord.ButtonStyle.green)
    async def enter_kills(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        await interaction.response.send_modal(
            KillModal(self.room_number, self.team_number, self.players,
                      self.position))


class KillModal(discord.ui.Modal):

    def __init__(self, room_number, team_number, players, position):
        super().__init__(title=f"Kills - Team {team_number}")

        self.room_number = room_number
        self.team_number = team_number
        self.players = players
        self.position = position

        self.k1 = discord.ui.TextInput(label=f"{players[0]} - Kills")
        self.k2 = discord.ui.TextInput(label=f"{players[1]} - Kills")
        self.k3 = discord.ui.TextInput(label=f"{players[2]} - Kills")
        self.k4 = discord.ui.TextInput(label=f"{players[3]} - Kills")

        self.add_item(self.k1)
        self.add_item(self.k2)
        self.add_item(self.k3)
        self.add_item(self.k4)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        team = data[self.team_number]

        # تأكد إن الهيكل موجود
        if "rooms" not in team:
            team["rooms"] = {"1": None, "2": None, "3": None}
            team["kills"] = {"1": {}, "2": {}, "3": {}}
            team["total_points"] = 0

        # 🔒 منع تكرار نفس الروم
        if team["rooms"][self.room_number] is not None:
            return await interaction.response.send_message(
                f"❌ تم احتساب روم {self.room_number} لهذا الفريق بالفعل.",
                ephemeral=True)

        # تحويل الكيلات لأرقام
        try:
            kills_list = [
                int(self.k1.value),
                int(self.k2.value),
                int(self.k3.value),
                int(self.k4.value)
            ]
        except:
            return await interaction.response.send_message(
                "❌ الكيلات لازم تكون أرقام.", ephemeral=True)

        placement_points = calculate_placement_points(int(self.position))
        # تأكد من هيكل placements
        if "placements" not in team:
            team["placements"] = {"1": None, "2": None, "3": None}

        team["placements"][self.room_number] = int(self.position)
        total_kills = sum(kills_list)
        total_points = placement_points + total_kills

        # تخزين بيانات الروم
        team["rooms"][self.room_number] = total_points
        team["kills"][self.room_number] = {
            self.players[0]: kills_list[0],
            self.players[1]: kills_list[1],
            self.players[2]: kills_list[2],
            self.players[3]: kills_list[3],
        }

        # تحديث التوتال بدون None
        team["total_points"] = sum(points for points in team["rooms"].values()
                                   if points is not None)

        save_data(data)

        result_text = "\n".join(f"{self.players[i]}: {kills_list[i]} kills"
                                for i in range(4))

        await interaction.response.send_message(
            f"✅ تم احتساب النقاط\n\n"
            f"📍 Placement: {self.position}\n"
            f"🏅 Placement Points: {placement_points}\n"
            f"🎯 Total Kills: {total_kills}\n"
            f"🏆 Room Points: {total_points}\n"
            f"🏆 Total Scrim Points: {team['total_points']}\n\n"
            f"{result_text}",
            ephemeral=True)


class AddPointsModal(discord.ui.Modal, title="Add Points"):
    team_number = discord.ui.TextInput(label="رقم الفريق")
    points = discord.ui.TextInput(label="عدد النقاط المراد إضافتها")

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        if self.team_number.value not in data:
            return await interaction.response.send_message(
                "❌ الفريق غير موجود.", ephemeral=True)

        try:
            pts = int(self.points.value)
        except:
            return await interaction.response.send_message("❌ أدخل رقم صحيح.",
                                                           ephemeral=True)

        data[self.team_number.value]["total_points"] += pts
        save_data(data)

        await interaction.response.send_message("✅ تم إضافة النقاط.",
                                                ephemeral=True)


class RemovePointsModal(discord.ui.Modal, title="Remove Points"):
    team_number = discord.ui.TextInput(label="رقم الفريق")
    points = discord.ui.TextInput(label="عدد النقاط المراد خصمها")

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        if self.team_number.value not in data:
            return await interaction.response.send_message(
                "❌ الفريق غير موجود.", ephemeral=True)

        try:
            pts = int(self.points.value)
        except:
            return await interaction.response.send_message("❌ أدخل رقم صحيح.",
                                                           ephemeral=True)

        data[self.team_number.value]["total_points"] -= pts
        if data[self.team_number.value]["total_points"] < 0:
            data[self.team_number.value]["total_points"] = 0

        save_data(data)

        await interaction.response.send_message("✅ تم خصم النقاط.",
                                                ephemeral=True)


def format_room_stats(team, room):
    points = team["rooms"].get(room)
    kills_data = team["kills"].get(room, {})

    # 🔒 لو الداتا القديمة مجرد int حوّلها dict تلقائي
    if isinstance(kills_data, int):
        # لو عندك أسماء اللاعبين مخزنة في team["players"]
        players = team.get("players",
                           ["Player1", "Player2", "Player3", "Player4"])
        # نوزع النقطه على Unknown كل لاعب بصفر (أو 0 لكل لاعب)
        kills_data = {player: 0 for player in players}
        team["kills"][
            room] = kills_data  # حدث الداتا نفسها عشان ما يرجعش نفس الخطأ تاني

    placement = team.get("placements", {}).get(room, "N/A")

    if points is None:
        return "لم يتم احتساب هذه الروم بعد."

    kills_text = "\n".join(f"{player}: {kills}"
                           for player, kills in kills_data.items())
    return f"Points: {points}\nPlacement: {placement}\n{kills_text}"


class TotalPointsModal(discord.ui.Modal, title="Team Statistics"):
    team_number = discord.ui.TextInput(label="رقم الفريق")

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        if self.team_number.value not in data:
            return await interaction.response.send_message(
                "❌ الفريق غير موجود.", ephemeral=True)

        team = data[self.team_number.value]

        # تهيئة هيكل الداتا
        if "rooms" not in team:
            team["rooms"] = {"1": None, "2": None, "3": None}
        if "kills" not in team:
            team["kills"] = {"1": {}, "2": {}, "3": {}}
        if "total_points" not in team:
            team["total_points"] = 0
        if "placements" not in team:
            team["placements"] = {"1": None, "2": None, "3": None}

        sorted_teams = sorted(data.items(),
                              key=lambda x: x[1].get("total_points", 0),
                              reverse=True)
        leaderboard_position = [
            i + 1 for i, t in enumerate(sorted_teams)
            if t[0] == self.team_number.value
        ][0]

        embed = discord.Embed(
            title=f"📊 Team {self.team_number.value} Statistics",
            color=0x00ff00)

        for room in ["1", "2", "3"]:
            embed.add_field(name=f"Room {room}",
                            value=format_room_stats(team, room),
                            inline=False)

        embed.add_field(
            name="Total",
            value=
            f"🏆 Total Points: {team['total_points']}\n📈 Leaderboard Position: {leaderboard_position}",
            inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


# ================== View ==================


class RegisterView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)  # لازم timeout = None

    @discord.ui.button(
        label="تسجيل فريق",
        style=discord.ButtonStyle.green,
        custom_id="persistent_register_button"  # لازم custom_id ثابت
    )
    async def register_button(self, interaction: discord.Interaction,
                              button: discord.ui.Button):
        await interaction.response.send_modal(RegisterModal())


# ================== TeamsView Commands ==================


class TeamsView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add Team",
                       style=discord.ButtonStyle.green,
                       custom_id="add_team_btn")
    async def add_team(self, interaction: discord.Interaction,
                       button: discord.ui.Button):
        if not (is_leader(interaction.user) or LEADER_ROLES(interaction)):
            return await interaction.response.send_message(
                "❌ ليس لديك صلاحية.", ephemeral=True)

        await interaction.response.send_modal(RegisterModal())

    @discord.ui.button(label="Remove Team",
                       style=discord.ButtonStyle.red,
                       custom_id="remove_team_btn")
    async def remove_team(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        if not (is_leader(interaction.user) or LEADER_ROLES(interaction)):
            return await interaction.response.send_message(
                "❌ ليس لديك صلاحية.", ephemeral=True)

        await interaction.response.send_modal(RemoveTeamModal())

    @discord.ui.button(label="Edit Team",
                       style=discord.ButtonStyle.blurple,
                       custom_id="edit_team_btn")
    async def edit_team(self, interaction: discord.Interaction,
                        button: discord.ui.Button):
        if not (is_leader(interaction.user) or LEADER_ROLES(interaction.user)):
            return await interaction.response.send_message(
                "❌ ليس لديك صلاحية.", ephemeral=True)

        await interaction.response.send_modal(EditTeamModal())


class RemoveTeamModal(discord.ui.Modal, title="Remove Team"):
    team_number = discord.ui.TextInput(label="رقم الفريق")

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        if self.team_number.value not in data:
            return await interaction.response.send_message(
                "❌ الفريق غير موجود.", ephemeral=True)

        del data[self.team_number.value]
        save_data(data)

        await interaction.response.send_message("✅ تم حذف الفريق.",
                                                ephemeral=True)


class EditTeamModal(discord.ui.Modal, title="Edit Team"):
    team_number = discord.ui.TextInput(label="رقم الفريق")
    player1 = discord.ui.TextInput(label="اسم اللاعب 1 الجديد")
    player2 = discord.ui.TextInput(label="اسم اللاعب 2 الجديد")
    player3 = discord.ui.TextInput(label="اسم اللاعب 3 الجديد")
    player4 = discord.ui.TextInput(label="اسم اللاعب 4 الجديد")

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        if self.team_number.value not in data:
            return await interaction.response.send_message(
                "❌ الفريق غير موجود.", ephemeral=True)

        data[self.team_number.value]["players"] = [
            self.player1.value, self.player2.value, self.player3.value,
            self.player4.value
        ]

        save_data(data)

        await interaction.response.send_message("✅ تم تعديل الفريق.",
                                                ephemeral=True)


class ResetPointsModal(discord.ui.Modal, title="إعادة ضبط نقاط الفريق"):
    team_number = discord.ui.TextInput(
        label="رقم الفريق",
        placeholder="أدخل رقم الفريق الذي تريد إعادة ضبط نقاطه",
        required=True,
        max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        team_id = self.team_number.value

        # تحقق من وجود الفريق
        if team_id not in data:
            return await interaction.response.send_message(
                "❌ الفريق غير موجود.", ephemeral=True)

        team = data[team_id]

        # إعادة تهيئة الرومات والكيلات والبوينتس
        team["rooms"] = {"1": None, "2": None, "3": None}
        team["kills"] = {"1": {}, "2": {}, "3": {}}
        team["placements"] = {"1": None, "2": None, "3": None}
        team["total_points"] = 0

        save_data(data)

        await interaction.response.send_message(
            f"✅ تم إعادة ضبط نقاط الفريق {team_id}. يمكنك الآن إعادة إضافة النقاط للرومات.",
            ephemeral=True)


# ================== Slash Commands ==================


@tree.command(name="open_registration", description="فتح التسجيل")
async def open_registration(interaction: discord.Interaction):
    global registration_open
    if not is_leader(interaction.user):
        return await interaction.response.send_message("❌ ليس لديك صلاحية.",
                                                       ephemeral=True)

    registration_open = True
    channel = bot.get_channel(REGISTRATION_CHANNEL_ID)
    image_url = "https://cdn.discordapp.com/attachments/904831915205464104/1473120680584417362/file_00000000944c722fadd2cee19c30659e.png?ex=69950e0b&is=6993bc8b&hm=a1e6a4d8374acebaf435330e3d9d5a38bbb60c6c6f051a3e66e445fd0be4de77&"
    # 👇 إعداد Embed جميل للتسجيل
    embed = discord.Embed(
        title="***🟢 تم فتح تسجيل التيمات في اسكرم الترين***",
        description=(
            "***📌 شروط التسجيل:***\n\n"
            "1️⃣ الفريق يتكون من **3 لاعبين على الأقل**.\n\n"
            "2️⃣ كل لاعب يجب أن يكتب **VLC** ثم اسم اللاعب في ببجي.\n\n"
            "3️⃣ الالتزام **برقم الفريق** المرسل لكل لاعب على الخاص.\n\n"
            "4️⃣ يمنع تكرار التسجيل لنفس الشخص أو الفريق.\n\n"
            "***✨ اضغط على الزر بالأسفل لتسجيل فريقك.***"),
        color=0x00ff00  # أخضر جميل
    )

    # 👇 ضع هنا رابط الصورة اللي تحب تظهر في الأعلى
    embed.set_image(url=image_url)

    # 👇 أرسل الرسالة مع الـ View الخاص بالتسجيل
    await channel.send(embed=embed, view=RegisterView())

    await interaction.response.send_message("✅ تم فتح التسجيل.",
                                            ephemeral=True)


@tree.command(name="points", description="نظام النقاط")
async def points(interaction: discord.Interaction):
    if not (is_leader(interaction.user) or LEADER_ROLES(interaction)):
        return await interaction.response.send_message("❌ ليس لديك صلاحية.",
                                                       ephemeral=True)

    embed = discord.Embed(
        title="📊 لوحة نظام النقاط - Volcano Training",
        description=
        "اختر أحد الخيارات من القائمة للتحكم في نقاط الفرق، عرض الإحصائيات، أو اللوحة النهائية.",
        color=0x00ffcc)

    embed.add_field(
        name="📊 Calculate Points",
        value="احسب نقاط فريق في روم معين مع مراعاة المراكز والكيلات.",
        inline=False)
    embed.add_field(name="➕ Add Points",
                    value="إضافة نقاط لأي فريق بشكل يدوي بعد التسجيل.",
                    inline=False)
    embed.add_field(name="➖ Remove Points",
                    value="إزالة نقاط من فريق معين بعد إدخال رقم الفريق.",
                    inline=False)
    embed.add_field(
        name="🏆 Total Points",
        value="عرض جميع نقاط فريق معين في الرومات الثلاث مع التفاصيل لكل لاعب.",
        inline=False)
    embed.add_field(
        name="🔥 Highest Kills",
        value="أعلى 3 لاعبين بالكيلات لجميع الرومات مع عرض رقم الفريق.",
        inline=False)
    embed.add_field(name="📈 LeaderBoard",
                    value="عرض ترتيب كل الفرق حسب مجموع النقاط وعدد الكيلات.",
                    inline=False)
    embed.add_field(
        name="♻️ Reset Points",
        value="إعادة ضبط نقاط فريق معين لتستطيع إعادة حساب الرومات له.",
        inline=False)
    embed.set_footer(
        text="💡 اختر الخيار المناسب من القائمة لتفعيل العملية المطلوبة.")

    await interaction.response.send_message(embed=embed,
                                            view=PointsView(),
                                            ephemeral=True)


@tree.command(name="close_registration", description="قفل التسجيل")
async def close_registration(interaction: discord.Interaction):
    global registration_open
    if not is_leader(interaction.user):
        return await interaction.response.send_message("❌ ليس لديك صلاحية.",
                                                       ephemeral=True)

    registration_open = False
    await interaction.response.send_message("🔒 تم قفل التسجيل.",
                                            ephemeral=True)


@tree.command(name="teams", description="عرض التيمات")
async def teams(interaction: discord.Interaction):
    if not (is_leader(interaction.user) or LEADER_ROLES(interaction)):
        return await interaction.response.send_message("❌ ليس لديك صلاحية.",
                                                       ephemeral=True)

    data = load_data()

    embed = discord.Embed(
        title="📋 الفرق المسجلة - Volcano Training",
        description="عرض جميع الفرق المسجلة مع أسماء اللاعبين وعددهم.",
        color=0x00ff99)

    if not data:
        embed.description = "لا يوجد فرق مسجلة حاليًا."
    else:
        # ترتيب الفرق حسب رقم التيم
        for number, info in sorted(data.items(), key=lambda x: int(x[0])):
            players_list = info.get("players", ["-"])
            players_text = "\n".join([f"🎮 {p}" for p in players_list])
            embed.add_field(
                name=f"Team {number} ({len(players_list)} لاعب/لاعبين)",
                value=players_text,
                inline=False)

    embed.set_footer(text="💡 تأكد أن كل فريق مسجل وفق قواعد التسجيل.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="reset_teams", description="مسح جميع الفرق")
async def reset_teams(interaction: discord.Interaction):
    if not is_leader(interaction.user):
        return await interaction.response.send_message("❌ ليس لديك صلاحية.",
                                                       ephemeral=True)

    save_data({})
    await interaction.response.send_message("♻️ تم إعادة تعيين جميع الفرق.")


# ================== Ready ==================


@bot.event
async def on_ready():
    await tree.sync()
    bot.add_view(RegisterView())
    print(f"Bot is ready as {bot.user}")


keep_alive()
bot.run(TOKEN)

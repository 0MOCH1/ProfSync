import discord
import os
import json

# --- 設定 ---
PAIRS_FILE = 'pairs.json' # 親子関係を保存するファイル名
# ----------------

# BOTのクライアントを作成
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
bot = discord.Bot(intents=intents)

# 親子ペアを格納する辞書 { "子のID": "親のID" }
try:
    with open(PAIRS_FILE, 'r') as f:
        child_to_parent_map = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    child_to_parent_map = {}

# --- ヘルパー関数 ---
def save_pairs():
    """親子ペアの情報をJSONファイルに保存する"""
    with open(PAIRS_FILE, 'w') as f:
        json.dump(child_to_parent_map, f, indent=4)

async def sync_nickname(guild, child_id, parent_id):
    """指定されたペアのニックネームを同期する"""
    try:
        parent_member = await guild.fetch_member(int(parent_id))
        child_member = await guild.fetch_member(int(child_id))
        
        # 親と子が両方サーバーに存在し、かつニックネームが親の名前と違う場合
        if parent_member and child_member and child_member.nick != parent_member.name:
            await child_member.edit(nick=parent_member.name)
            print(f"同期実行: 子 '{child_member.name}' のニックネームを親 '{parent_member.name}' に設定しました。")
    except discord.Forbidden:
        print(f"権限エラー: 子 '{child_id}' のニックネームを変更できません。")
    except discord.NotFound:
        # ユーザーがサーバーにいない場合は何もしない
        pass

# --- イベント処理 ---
@bot.event
async def on_ready():
    """BOT起動時の処理"""
    print(f'{bot.user}としてログインしました')
    print('--- 全サーバーのペアを初期同期します ---')
    for guild in bot.guilds:
        for child_id, parent_id in child_to_parent_map.items():
            await sync_nickname(guild, child_id, parent_id)
    print('--- 初期同期が完了しました ---')

@bot.event
async def on_member_update(before, after):
    """メンバーの更新（ニックネーム変更など）を検知"""
    # 更新されたメンバーが「子」か確認
    child_id = str(after.id)
    if child_id in child_to_parent_map:
        parent_id = child_to_parent_map[child_id]
        # 子が自分でニックネームを変えた場合などに、親の名前に戻す
        await sync_nickname(after.guild, child_id, parent_id)

@bot.event
async def on_user_update(before, after):
    """ユーザーの更新（グローバルな名前の変更）を検知"""
    # 更新されたユーザーが「親」か確認
    parent_id = str(after.id)
    children_ids = [child_id for child_id, p_id in child_to_parent_map.items() if p_id == parent_id]
    
    # 親の名前が変更されたら、その親を持つすべての子を全サーバーで同期する
    if children_ids and before.name != after.name:
        print(f"親 '{before.name}' が '{after.name}' に改名しました。子の同期を開始します。")
        for guild in bot.guilds:
            for child_id in children_ids:
                await sync_nickname(guild, child_id, parent_id)

# --- 管理者用コマンド ---

# 管理者権限を持つユーザーのみが使えるように設定
admin_permissions = discord.Permissions(administrator=True)

@bot.slash_command(name="set_pair", description="[管理者用] 親と子のペアを登録・更新します。", default_member_permissions=admin_permissions)
async def set_pair(ctx, parent: discord.Member, child: discord.Member):
    if parent.id == child.id:
        await ctx.respond("自分自身をペアに設定することはできません。", ephemeral=True)
        return

    child_to_parent_map[str(child.id)] = str(parent.id)
    save_pairs()
    
    await ctx.respond(f"ペアを登録しました。\n親: {parent.mention}\n子: {child.mention}\nただちに同期します。", ephemeral=True)
    # すぐに同期を実行
    await sync_nickname(ctx.guild, str(child.id), str(parent.id))

@bot.slash_command(name="remove_pair", description="[管理者用] 子の同期設定を解除します。", default_member_permissions=admin_permissions)
async def remove_pair(ctx, child: discord.Member):
    child_id = str(child.id)
    if child_id in child_to_parent_map:
        del child_to_parent_map[child_id]
        save_pairs()
        await ctx.respond(f"{child.mention} の同期設定を解除しました。", ephemeral=True)
    else:
        await ctx.respond(f"{child.mention} は同期設定されていません。", ephemeral=True)

@bot.slash_command(name="list_pairs", description="[管理者用] 登録されているペアの一覧を表示します。", default_member_permissions=admin_permissions)
async def list_pairs(ctx):
    if not child_to_parent_map:
        await ctx.respond("登録されているペアはありません。", ephemeral=True)
        return

    embed = discord.Embed(title="登録ペア一覧", color=discord.Color.blue())
    description = ""
    for child_id, parent_id in child_to_parent_map.items():
        description += f"**親**: <@{parent_id}> → **子**: <@{child_id}>\n"
    
    embed.description = description
    await ctx.respond(embed=embed, ephemeral=True)

# --- BOTの実行 ---
bot_token = os.environ.get("DISCORD_BOT_TOKEN")
if bot_token is None:
    print("エラー: 環境変数 'DISCORD_BOT_TOKEN' が設定されていません。")
else:
    bot.run(bot_token)
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from config import TOKEN, ADMIN_IDS
from database import Session, User, Item, Hero, Inventory, Marriage, GlobalTop, MarketListing
import sqlalchemy
from datetime import datetime
import random
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Admin decorator
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Anda tidak memiliki akses ke command ini!")
            return
        return await func(update, context)
    return wrapper

# Get or create user
def get_user(user_id, username=None):
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if not user:
        user = User(user_id=user_id, username=username)
        session.add(user)
        session.commit()
        # Update global top
        global_top = session.query(GlobalTop).filter_by(user_id=user_id).first()
        if not global_top:
            global_top = GlobalTop(user_id=user_id, total_points=0)
            session.add(global_top)
            session.commit()
    session.close()
    return user

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    user = get_user(user_id, username)
    
    keyboard = [
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("⚔️ Petualangan", callback_data='adventure'), InlineKeyboardButton("🏪 Toko", callback_data='shop')],
        [InlineKeyboardButton("🎒 Inventory", callback_data='inventory'), InlineKeyboardButton("📊 Top Global", callback_data='top_global')],
        [InlineKeyboardButton("💍 Nikah", callback_data='marriage'), InlineKeyboardButton("🏪 Market", callback_data='market')],
        [InlineKeyboardButton("💰 Daily Reward", callback_data='daily')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✨ Selamat datang di RPG Adventure Bot, {update.effective_user.first_name}!\n\n"
        f"🎮 Gunakan tombol di bawah untuk bermain:\n\n"
        f"📊 Level: {user.level}\n"
        f"💰 Gold: {user.gold}\n"
        f"💎 Diamond: {user.diamond}\n"
        f"❤️ Health: {user.health}/{user.max_health}\n\n"
        f"Selamat bermain! 🎉",
        reply_markup=reply_markup
    )

# Profile command
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    user_data = session.query(User).filter_by(user_id=query.from_user.id).first()
    
    weapon = session.query(Item).filter_by(id=user_data.weapon_id).first() if user_data.weapon_id else None
    armor = session.query(Item).filter_by(id=user_data.armor_id).first() if user_data.armor_id else None
    hero = session.query(Hero).filter_by(id=user_data.hero_id).first() if user_data.hero_id else None
    
    total_attack = user_data.attack + (weapon.attack_bonus if weapon else 0) + (hero.attack_bonus if hero else 0)
    total_defense = user_data.defense + (armor.defense_bonus if armor else 0) + (hero.defense_bonus if hero else 0)
    
    # Check marriage
    married_name = "Lajang"
    if user_data.married_to:
        spouse = session.query(User).filter_by(id=user_data.married_to).first()
        if spouse:
            married_name = f"Menikah dengan {spouse.username or f'User{spouse.user_id}'}"
    
    profile_text = f"""
👤 **PROFIL CHARACTER**

📛 **Nama:** {query.from_user.first_name}
📊 **Level:** {user_data.level}
⭐ **Exp:** {user_data.exp}/100
💰 **Gold:** {user_data.gold:,}
💎 **Diamond:** {user_data.diamond:,}
❤️ **Health:** {user_data.health}/{user_data.max_health}

⚔️ **Base Attack:** {user_data.attack}
🛡️ **Base Defense:** {user_data.defense}
✨ **Total Attack:** {total_attack}
✨ **Total Defense:** {total_defense}

🗡️ **Weapon:** {weapon.name if weapon else '❌ Tidak ada'}
🛡️ **Armor:** {armor.name if armor else '❌ Tidak ada'}
🦸 **Hero:** {hero.name if hero else '❌ Tidak ada'}

💍 **Status:** {married_name}
    """
    
    # Show photo if exists
    if hero and hero.photo_id:
        await query.message.reply_photo(hero.photo_id, caption=profile_text, parse_mode=ParseMode.MARKDOWN)
        await query.delete()
    else:
        await query.edit_message_text(profile_text, parse_mode=ParseMode.MARKDOWN)
    
    session.close()

# Adventure command
async def adventure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    user_data = session.query(User).filter_by(user_id=query.from_user.id).first()
    
    # Get equipped items
    weapon = session.query(Item).filter_by(id=user_data.weapon_id).first() if user_data.weapon_id else None
    hero = session.query(Hero).filter_by(id=user_data.hero_id).first() if user_data.hero_id else None
    
    total_attack = user_data.attack + (weapon.attack_bonus if weapon else 0) + (hero.attack_bonus if hero else 0)
    
    # Random encounter with level scaling
    level_factor = max(1, user_data.level / 5)
    monsters = [
        {"name": "🐺 Goblin", "min_damage": int(5 * level_factor), "max_damage": int(15 * level_factor), "reward": 50 * user_data.level, "exp": 20},
        {"name": "🧟 Orc", "min_damage": int(10 * level_factor), "max_damage": int(25 * level_factor), "reward": 100 * user_data.level, "exp": 40},
        {"name": "🐉 Dragon", "min_damage": int(20 * level_factor), "max_damage": int(40 * level_factor), "reward": 200 * user_data.level, "exp": 80},
        {"name": "🗡️ Dark Knight", "min_damage": int(15 * level_factor), "max_damage": int(35 * level_factor), "reward": 150 * user_data.level, "exp": 60},
        {"name": "🧙 Wizard", "min_damage": int(12 * level_factor), "max_damage": int(30 * level_factor), "reward": 120 * user_data.level, "exp": 50}
    ]
    
    monster = random.choice(monsters)
    damage_taken = random.randint(monster["min_damage"], monster["max_damage"])
    damage_given = random.randint(10, 30) + (total_attack // 2)
    
    # Defense reduction
    damage_taken = max(1, damage_taken - user_data.defense // 2)
    
    user_data.health -= damage_taken
    if user_data.health <= 0:
        user_data.health = user_data.max_health
        result_text = f"💀 **KAMU KALAH!** 💀\n\n⚔️ Melawan: {monster['name']}\n💔 Damage diterima: {damage_taken}\n\n❤️ Kesehatan dipulihkan ke {user_data.health}/{user_data.max_health}"
    else:
        exp_gain = monster["exp"] + random.randint(0, 20)
        gold_gain = monster["reward"] + random.randint(0, 50)
        user_data.exp += exp_gain
        user_data.gold += gold_gain
        
        level_up_text = ""
        # Level up
        while user_data.exp >= 100:
            user_data.level += 1
            user_data.exp -= 100
            user_data.max_health += 20
            user_data.health = user_data.max_health
            user_data.attack += 5
            user_data.defense += 3
            level_up_text += f"\n\n🎉 **LEVEL UP!** Sekarang level {user_data.level}! 🎉"
        
        # Update global top points
        global_top = session.query(GlobalTop).filter_by(user_id=query.from_user.id).first()
        if global_top:
            global_top.total_points += exp_gain + gold_gain // 10
        else:
            global_top = GlobalTop(user_id=query.from_user.id, total_points=exp_gain + gold_gain // 10)
            session.add(global_top)
        
        result_text = f"⚔️ **PERTEMPURAN** ⚔️\n\n"
        result_text += f"🎯 Melawan: {monster['name']}\n"
        result_text += f"🗡️ Damage diberikan: {damage_given}\n"
        result_text += f"💔 Damage diterima: {damage_taken}\n"
        result_text += f"✨ Exp gained: +{exp_gain}\n"
        result_text += f"💰 Gold gained: +{gold_gain}\n"
        result_text += f"❤️ Sisa HP: {user_data.health}/{user_data.max_health}"
        result_text += level_up_text
    
    session.commit()
    session.close()
    
    keyboard = [[InlineKeyboardButton("⚔️ Lanjut Bertarung", callback_data='adventure')],
                [InlineKeyboardButton("🏠 Kembali ke Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(result_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

# Shop command
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🗡️ Weapons", callback_data='shop_weapons')],
        [InlineKeyboardButton("🛡️ Armors", callback_data='shop_armors')],
        [InlineKeyboardButton("🦸 Heroes", callback_data='shop_heroes')],
        [InlineKeyboardButton("💊 Consumables", callback_data='shop_consumables')],
        [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏪 **WELCOME TO THE SHOP** 🏪\n\n"
        "Pilih kategori item yang ingin dibeli:\n\n"
        f"💰 Gold kamu: {get_user(query.from_user.id).gold}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def shop_weapons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    weapons = session.query(Item).filter_by(item_type='weapon', is_available=True).all()
    
    if not weapons:
        await query.edit_message_text("❌ Belum ada weapon di shop!")
        return
    
    keyboard = []
    for weapon in weapons:
        keyboard.append([InlineKeyboardButton(f"{weapon.name} - {weapon.price} Gold", callback_data=f'buy_weapon_{weapon.id}')])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='shop')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🗡️ **WEAPONS SHOP**\n\nPilih weapon yang ingin dibeli:", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    session.close()

async def shop_armors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    armors = session.query(Item).filter_by(item_type='armor', is_available=True).all()
    
    if not armors:
        await query.edit_message_text("❌ Belum ada armor di shop!")
        return
    
    keyboard = []
    for armor in armors:
        keyboard.append([InlineKeyboardButton(f"{armor.name} - {armor.price} Gold", callback_data=f'buy_armor_{armor.id}')])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='shop')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🛡️ **ARMORS SHOP**\n\nPilih armor yang ingin dibeli:", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    session.close()

async def shop_heroes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    heroes = session.query(Hero).filter_by(is_available=True).all()
    
    if not heroes:
        await query.edit_message_text("❌ Belum ada hero di shop!")
        return
    
    keyboard = []
    for hero in heroes:
        keyboard.append([InlineKeyboardButton(f"{hero.name} - {hero.price} Diamond", callback_data=f'buy_hero_{hero.id}')])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='shop')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🦸 **HEROES SHOP**\n\nPilih hero yang ingin dibeli:", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    session.close()

async def shop_consumables(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    consumables = session.query(Item).filter_by(item_type='consumable', is_available=True).all()
    
    if not consumables:
        await query.edit_message_text("❌ Belum ada consumable di shop!")
        return
    
    keyboard = []
    for item in consumables:
        keyboard.append([InlineKeyboardButton(f"{item.name} - {item.price} Gold", callback_data=f'buy_consumable_{item.id}')])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='shop')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("💊 **CONSUMABLES SHOP**\n\nPilih item yang ingin dibeli:", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    session.close()

async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split('_')
    item_type = data[1]
    item_id = int(data[2])
    
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    
    if item_type == 'weapon':
        item = session.query(Item).filter_by(id=item_id, item_type='weapon').first()
        if user.gold >= item.price:
            user.gold -= item.price
            # Check if already have
            inv = session.query(Inventory).filter_by(user_id=user.id, item_id=item.id).first()
            if inv:
                inv.quantity += 1
            else:
                inv = Inventory(user_id=user.id, item_id=item.id, quantity=1)
                session.add(inv)
            await query.answer(f"✅ Berhasil membeli {item.name}!")
        else:
            await query.answer("❌ Gold tidak cukup!")
            
    elif item_type == 'armor':
        item = session.query(Item).filter_by(id=item_id, item_type='armor').first()
        if user.gold >= item.price:
            user.gold -= item.price
            inv = session.query(Inventory).filter_by(user_id=user.id, item_id=item.id).first()
            if inv:
                inv.quantity += 1
            else:
                inv = Inventory(user_id=user.id, item_id=item.id, quantity=1)
                session.add(inv)
            await query.answer(f"✅ Berhasil membeli {item.name}!")
        else:
            await query.answer("❌ Gold tidak cukup!")
            
    elif item_type == 'hero':
        hero = session.query(Hero).filter_by(id=item_id).first()
        if user.diamond >= hero.price:
            user.diamond -= hero.price
            user.hero_id = hero.id
            await query.answer(f"✅ Berhasil membeli hero {hero.name}!")
        else:
            await query.answer("❌ Diamond tidak cukup!")
            
    elif item_type == 'consumable':
        item = session.query(Item).filter_by(id=item_id, item_type='consumable').first()
        if user.gold >= item.price:
            user.gold -= item.price
            inv = session.query(Inventory).filter_by(user_id=user.id, item_id=item.id).first()
            if inv:
                inv.quantity += 1
            else:
                inv = Inventory(user_id=user.id, item_id=item.id, quantity=1)
                session.add(inv)
            await query.answer(f"✅ Berhasil membeli {item.name}!")
        else:
            await query.answer("❌ Gold tidak cukup!")
    
    session.commit()
    session.close()
    
    # Refresh shop menu
    await shop(query)

# Inventory command
async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    inventory_items = session.query(Inventory).filter_by(user_id=user.id).all()
    
    if not inventory_items:
        await query.edit_message_text("🎒 **INVENTORY KOSONG!**\n\nBelum ada item yang kamu miliki.", parse_mode=ParseMode.MARKDOWN)
        session.close()
        return
    
    keyboard = []
    for inv_item in inventory_items:
        item = inv_item.item
        button_text = f"{item.name} x{inv_item.quantity}"
        if item.item_type == 'weapon':
            button_text += f" ⚔️+{item.attack_bonus}"
        elif item.item_type == 'armor':
            button_text += f" 🛡️+{item.defense_bonus}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'use_item_{item.id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    inventory_text = "🎒 **INVENTORY** 🎒\n\nKlik item untuk menggunakannya:\n\n"
    await query.edit_message_text(inventory_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    session.close()

async def use_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    item_id = int(query.data.split('_')[2])
    
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    item = session.query(Item).filter_by(id=item_id).first()
    inventory = session.query(Inventory).filter_by(user_id=user.id, item_id=item_id).first()
    
    if not inventory or inventory.quantity < 1:
        await query.answer("❌ Item tidak ada di inventory!")
        session.close()
        return
    
    if item.item_type == 'weapon':
        user.weapon_id = item.id
        await query.answer(f"✅ {item.name} dipasang sebagai weapon!")
    elif item.item_type == 'armor':
        user.armor_id = item.id
        await query.answer(f"✅ {item.name} dipasang sebagai armor!")
    elif item.item_type == 'consumable':
        if item.health_bonus > 0:
            user.health = min(user.max_health, user.health + item.health_bonus)
            inventory.quantity -= 1
            await query.answer(f"✅ Menggunakan {item.name}, +{item.health_bonus} HP!")
        if inventory.quantity <= 0:
            session.delete(inventory)
    else:
        await query.answer("❌ Item tidak dapat digunakan!")
    
    session.commit()
    session.close()
    
    await inventory(query)

# Top Global command
async def top_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    tops = session.query(GlobalTop).order_by(GlobalTop.total_points.desc()).limit(10).all()
    
    if not tops:
        await query.edit_message_text("📊 **TOP GLOBAL**\n\nBelum ada data top global!", parse_mode=ParseMode.MARKDOWN)
        session.close()
        return
    
    top_text = "🏆 **TOP GLOBAL PLAYERS** 🏆\n\n"
    for i, top in enumerate(tops, 1):
        user = session.query(User).filter_by(user_id=top.user_id).first()
        if user:
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
            top_text += f"{medal} {i}. {user.username or f'User{user.user_id}'} - **{top.total_points:,} pts**\n"
            if i == 1 and user.level:
                top_text += f"   Level: {user.level} | Gold: {user.gold:,}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(top_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    session.close()

# Marriage command
async def marriage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    
    if user.married_to:
        spouse = session.query(User).filter_by(id=user.married_to).first()
        keyboard = [
            [InlineKeyboardButton("💔 Cerai", callback_data='divorce_confirm')],
            [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"💍 **ANDA SUDAH MENIKAH** 💍\n\n"
            f"Pasangan: {spouse.username or f'User{spouse.user_id}'}\n"
            f"Tanggal: {spouse.created_at.strftime('%d %B %Y')}\n\n"
            f"Apakah ingin bercerai?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("💍 Cari Jodoh", callback_data='find_spouse')],
            [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "💍 **MARRIAGE SYSTEM** 💍\n\n"
            "Kamu belum menikah. Cari jodoh sekarang!\n\n"
            "Syarat:\n"
            "💰 5000 Gold\n"
            "💎 100 Diamond\n"
            "❤️ Level 10+",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    session.close()

async def find_spouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    
    if user.level < 10:
        await query.edit_message_text("❌ Minimal level 10 untuk menikah!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='marriage')]]))
        session.close()
        return
    
    # Find unmarried users
    unmarried = session.query(User).filter(User.married_to == None, User.id != user.id).all()
    
    if not unmarried:
        await query.edit_message_text("❌ Tidak ada pengguna yang tersedia untuk dinikahi!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='marriage')]]))
        session.close()
        return
    
    keyboard = []
    for candidate in unmarried[:10]:
        keyboard.append([InlineKeyboardButton(f"{candidate.username or f'User{candidate.user_id}'} (Lv.{candidate.level})", callback_data=f'propose_{candidate.id}')])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='marriage')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("💍 **Pilih pasangan yang ingin dilamar:**", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    session.close()

async def propose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    target_id = int(query.data.split('_')[1])
    
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    target = session.query(User).filter_by(id=target_id).first()
    
    if user.gold < 5000 or user.diamond < 100:
        await query.answer("❌ Gold/Diamond tidak cukup! (5000 Gold, 100 Diamond)")
        session.close()
        return
    
    keyboard = [
        [InlineKeyboardButton("✅ Terima", callback_data=f'accept_{user.id}')],
        [InlineKeyboardButton("❌ Tolak", callback_data='reject')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Store proposal in context
    context.user_data['proposal'] = {'from': user.id, 'to': target.user_id}
    
    await query.edit_message_text(
        f"💍 **LAMARAN PERNIKAHAN** 💍\n\n"
        f"{user.username or f'User{user.user_id}'} ingin menikah denganmu!\n\n"
        f"Apakah kamu menerima?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    session.close()

async def accept_marriage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    proposer_id = int(query.data.split('_')[1])
    
    session = Session()
    proposer = session.query(User).filter_by(id=proposer_id).first()
    accepter = session.query(User).filter_by(user_id=query.from_user.id).first()
    
    if proposer and accepter:
        if proposer.gold >= 5000 and proposer.diamond >= 100:
            proposer.gold -= 5000
            proposer.diamond -= 100
            proposer.married_to = accepter.id
            accepter.married_to = proposer.id
            
            # Create marriage record
            marriage = Marriage(user1_id=proposer.id, user2_id=accepter.id)
            session.add(marriage)
            session.commit()
            
            await query.edit_message_text(
                f"💍 **SELAMAT!** 💍\n\n"
                f"Anda telah menikah dengan {proposer.username or f'User{proposer.user_id}'}!\n\n"
                f"🎉 Semoga bahagia selalu! 🎉",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text("❌ Lamaran dibatalkan karena syarat tidak terpenuhi!")
    
    session.close()

# Market command
async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    listings = session.query(MarketListing).all()
    
    if listings:
        market_text = "🏪 **MARKETPLACE** 🏪\n\n"
        for listing in listings[:10]:
            seller = session.query(User).filter_by(id=listing.seller_id).first()
            item = listing.item
            market_text += f"📦 {item.name} x{listing.quantity} - {listing.price} Gold\n"
            market_text += f"   👤 Seller: {seller.username or f'User{seller.user_id}'}\n"
            market_text += f"   🆔 ID: {listing.id}\n\n"
    else:
        market_text = "🏪 **MARKETPLACE** 🏪\n\nBelum ada listing!"
    
    keyboard = [
        [InlineKeyboardButton("📦 List Item Jualan", callback_data='list_item_menu')],
        [InlineKeyboardButton("🛒 Beli Item", callback_data='buy_item_menu')],
        [InlineKeyboardButton("📋 Listing Saya", callback_data='my_listings')],
        [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(market_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    session.close()

async def list_item_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    inventory_items = session.query(Inventory).filter_by(user_id=user.id).all()
    
    if not inventory_items:
        await query.edit_message_text("❌ Tidak ada item di inventory!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='market')]]))
        session.close()
        return
    
    keyboard = []
    for inv in inventory_items:
        keyboard.append([InlineKeyboardButton(f"{inv.item.name} x{inv.quantity}", callback_data=f'sell_item_{inv.item.id}')])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='market')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("📦 **Pilih item yang ingin dijual:**", parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    session.close()

async def sell_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    item_id = int(query.data.split('_')[2])
    
    context.user_data['selling_item'] = item_id
    await query.edit_message_text("💰 **Masukkan harga jual (dalam Gold):**\n\nContoh: 5000", parse_mode=ParseMode.MARKDOWN)

# Daily reward
async def daily_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    
    # Check last daily claim
    if 'last_daily' in context.user_data:
        last_claim = context.user_data['last_daily']
        now = datetime.now()
        if (now - last_claim).days < 1:
            hours_left = 24 - (now - last_claim).seconds // 3600
            await query.answer(f"❌ Daily reward sudah diambil! Coba lagi dalam {hours_left} jam.")
            session.close()
            return
    
    # Give rewards
    reward_gold = 1000 + (user.level * 100)
    reward_diamond = 50 + (user.level // 2)
    reward_exp = 100
    
    user.gold += reward_gold
    user.diamond += reward_diamond
    user.exp += reward_exp
    
    context.user_data['last_daily'] = datetime.now()
    session.commit()
    
    await query.edit_message_text(
        f"🎁 **DAILY REWARD!** 🎁\n\n"
        f"💰 Gold: +{reward_gold:,}\n"
        f"💎 Diamond: +{reward_diamond}\n"
        f"✨ Exp: +{reward_exp}\n\n"
        f"Kembali lagi besok untuk reward harian!",
        parse_mode=ParseMode.MARKDOWN
    )
    session.close()

# Main menu handler
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    
    keyboard = [
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("⚔️ Petualangan", callback_data='adventure'), InlineKeyboardButton("🏪 Toko", callback_data='shop')],
        [InlineKeyboardButton("🎒 Inventory", callback_data='inventory'), InlineKeyboardButton("📊 Top Global", callback_data='top_global')],
        [InlineKeyboardButton("💍 Nikah", callback_data='marriage'), InlineKeyboardButton("🏪 Market", callback_data='market')],
        [InlineKeyboardButton("💰 Daily Reward", callback_data='daily')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎮 **MAIN MENU** 🎮\n\n"
        f"📊 Level: {user.level}\n"
        f"💰 Gold: {user.gold:,}\n"
        f"💎 Diamond: {user.diamond:,}\n"
        f"❤️ Health: {user.health}/{user.max_health}\n\n"
        f"Pilih aksi yang ingin dilakukan:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# Admin: Set photo for items/weapons/heroes
@admin_only
async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("❌ Reply ke gambar dengan command /setphoto [item/weapon/armor/consumable/hero] [id]")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Format: /setphoto [item/weapon/armor/consumable/hero] [id]\n\nContoh: /setphoto weapon 1")
        return
    
    item_type = args[0].lower()
    try:
        item_id = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ ID harus berupa angka!")
        return
    
    photo_id = update.message.reply_to_message.photo[-1].file_id
    
    session = Session()
    
    try:
        if item_type in ["item", "weapon", "armor",

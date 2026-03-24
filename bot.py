import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from config import TOKEN, ADMIN_IDS
from database import Session, User, Item, Hero, Inventory, Marriage, GlobalTop, MarketListing
import sqlalchemy
from datetime import datetime
import random

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
    session.close()
    return user

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    get_user(user_id, username)
    
    keyboard = [
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("⚔️ Petualangan", callback_data='adventure'), InlineKeyboardButton("🏪 Toko", callback_data='shop')],
        [InlineKeyboardButton("🎒 Inventory", callback_data='inventory'), InlineKeyboardButton("📊 Top Global", callback_data='top_global')],
        [InlineKeyboardButton("💍 Nikah", callback_data='marriage'), InlineKeyboardButton("🏪 Market", callback_data='market')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✨ Selamat datang di RPG Adventure Bot, {update.effective_user.first_name}!\n\n"
        f"🎮 Gunakan tombol di bawah untuk bermain:\n\n"
        f"📊 Level: 1\n"
        f"💰 Gold: 1000\n"
        f"💎 Diamond: 100\n"
        f"❤️ Health: 100/100\n\n"
        f"Selamat bermain! 🎉",
        reply_markup=reply_markup
    )

# Profile command
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    session = Session()
    user_data = session.query(User).filter_by(user_id=query.from_user.id).first()
    
    weapon = session.query(Item).filter_by(id=user_data.weapon_id).first() if user_data.weapon_id else None
    armor = session.query(Item).filter_by(id=user_data.armor_id).first() if user_data.armor_id else None
    hero = session.query(Hero).filter_by(id=user_data.hero_id).first() if user_data.hero_id else None
    
    total_attack = user_data.attack + (weapon.attack_bonus if weapon else 0) + (hero.attack_bonus if hero else 0)
    total_defense = user_data.defense + (armor.defense_bonus if armor else 0) + (hero.defense_bonus if hero else 0)
    
    profile_text = f"""
👤 **Profil {query.from_user.first_name}**

📊 **Level:** {user_data.level}
⭐ **Exp:** {user_data.exp}/100
💰 **Gold:** {user_data.gold}
💎 **Diamond:** {user_data.diamond}
❤️ **Health:** {user_data.health}/{user_data.max_health}

⚔️ **Attack:** {total_attack}
🛡️ **Defense:** {total_defense}

🗡️ **Weapon:** {weapon.name if weapon else 'Tidak ada'}
🛡️ **Armor:** {armor.name if armor else 'Tidak ada'}
🦸 **Hero:** {hero.name if hero else 'Tidak ada'}

💍 **Status:** {'Menikah' if user_data.married_to else 'Lajang'}
    """
    
    await query.edit_message_text(profile_text, parse_mode=ParseMode.MARKDOWN)

# Adventure command
async def adventure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    session = Session()
    user_data = session.query(User).filter_by(user_id=query.from_user.id).first()
    
    # Random encounter
    monsters = [
        {"name": "Goblin", "min_damage": 5, "max_damage": 15, "reward": 50},
        {"name": "Orc", "min_damage": 10, "max_damage": 25, "reward": 100},
        {"name": "Dragon", "min_damage": 20, "max_damage": 40, "reward": 200}
    ]
    
    monster = random.choice(monsters)
    damage_taken = random.randint(monster["min_damage"], monster["max_damage"])
    damage_given = random.randint(10, 30) + (user_data.attack // 2)
    
    user_data.health -= damage_taken
    if user_data.health <= 0:
        user_data.health = user_data.max_health
        result_text = f"💀 Kamu kalah melawan {monster['name']}! Kesehatan dipulihkan."
    else:
        exp_gain = random.randint(20, 50)
        gold_gain = monster["reward"]
        user_data.exp += exp_gain
        user_data.gold += gold_gain
        
        # Level up
        if user_data.exp >= 100:
            user_data.level += 1
            user_data.exp -= 100
            user_data.max_health += 20
            user_data.health = user_data.max_health
            user_data.attack += 5
            user_data.defense += 3
            level_up_text = f"\n\n🎉 **LEVEL UP!** Sekarang level {user_data.level}!"
        else:
            level_up_text = ""
        
        result_text = f"⚔️ **Pertempuran dengan {monster['name']}**\n\n"
        result_text += f"🗡️ Damage diberikan: {damage_given}\n"
        result_text += f"💔 Damage diterima: {damage_taken}\n"
        result_text += f"✨ Exp gained: +{exp_gain}\n"
        result_text += f"💰 Gold gained: +{gold_gain}\n"
        result_text += f"❤️ Sisa HP: {user_data.health}/{user_data.max_health}{level_up_text}"
    
    session.commit()
    session.close()
    
    await query.edit_message_text(result_text, parse_mode=ParseMode.MARKDOWN)

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
        "🏪 **Welcome to the Shop!**\n\n"
        "Pilih kategori item yang ingin dibeli:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# Inventory command
async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    inventory_items = session.query(Inventory).filter_by(user_id=user.id).all()
    
    if not inventory_items:
        await query.edit_message_text("🎒 Inventory kamu kosong!")
        return
    
    inventory_text = "🎒 **Inventory**\n\n"
    for inv_item in inventory_items:
        item = inv_item.item
        inventory_text += f"• {item.name} x{inv_item.quantity}\n"
        if item.item_type == "weapon":
            inventory_text += f"  ⚔️ Attack: +{item.attack_bonus}\n"
        elif item.item_type == "armor":
            inventory_text += f"  🛡️ Defense: +{item.defense_bonus}\n"
    
    await query.edit_message_text(inventory_text, parse_mode=ParseMode.MARKDOWN)

# Top Global command
async def top_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session = Session()
    tops = session.query(GlobalTop).order_by(GlobalTop.total_points.desc()).limit(10).all()
    
    if not tops:
        await query.edit_message_text("📊 Belum ada data top global!")
        return
    
    top_text = "🏆 **Top Global Players** 🏆\n\n"
    for i, top in enumerate(tops, 1):
        user = session.query(User).filter_by(user_id=top.user_id).first()
        if user:
            top_text += f"{i}. {user.username or f'User{user.user_id}'} - {top.total_points} pts\n"
    
    await query.edit_message_text(top_text, parse_mode=ParseMode.MARKDOWN)

# Marriage command
async def marriage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💍 Propose Marriage", callback_data='propose')],
        [InlineKeyboardButton("💔 Divorce", callback_data='divorce')],
        [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💍 **Marriage System**\n\n"
        "Pilih aksi yang ingin dilakukan:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# Market command
async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📦 List Item", callback_data='list_item')],
        [InlineKeyboardButton("🛒 Buy Item", callback_data='buy_item')],
        [InlineKeyboardButton("📋 My Listings", callback_data='my_listings')],
        [InlineKeyboardButton("🔙 Back", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏪 **Marketplace**\n\n"
        "Jual dan beli item dengan pemain lain:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# Admin: Set photo for items/weapons/heroes
@admin_only
async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("❌ Reply ke gambar dengan command /setphoto [item/weapon/hero] [id]")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Format: /setphoto [item/weapon/hero] [id]")
        return
    
    item_type = args[0].lower()
    item_id = int(args[1])
    photo_id = update.message.reply_to_message.photo[-1].file_id
    
    session = Session()
    
    try:
        if item_type in ["item", "weapon", "armor", "consumable"]:
            item = session.query(Item).filter_by(id=item_id).first()
            if item:
                item.photo_id = photo_id
                await update.message.reply_text(f"✅ Photo untuk item '{item.name}' berhasil di-set!")
            else:
                await update.message.reply_text("❌ Item tidak ditemukan!")
        
        elif item_type == "hero":
            hero = session.query(Hero).filter_by(id=item_id).first()
            if hero:
                hero.photo_id = photo_id
                await update.message.reply_text(f"✅ Photo untuk hero '{hero.name}' berhasil di-set!")
            else:
                await update.message.reply_text("❌ Hero tidak ditemukan!")
        
        else:
            await update.message.reply_text("❌ Tipe tidak valid! Gunakan: item, weapon, armor, consumable, atau hero")
        
        session.commit()
    
    except Exception as e:
        session.rollback()
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    finally:
        session.close()

# Admin: Add item to shop
@admin_only
async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 6:
        await update.message.reply_text("❌ Format: /additem [name] [type] [price] [attack] [defense] [health]")
        return
    
    name = args[0]
    item_type = args[1]
    price = int(args[2])
    attack = int(args[3])
    defense = int(args[4])
    health = int(args[5])
    
    session = Session()
    item = Item(
        name=name,
        item_type=item_type,
        price=price,
        attack_bonus=attack,
        defense_bonus=defense,
        health_bonus=health,
        description=f"Attack: +{attack}, Defense: +{defense}, Health: +{health}"
    )
    session.add(item)
    session.commit()
    session.close()
    
    await update.message.reply_text(f"✅ Item '{name}' berhasil ditambahkan ke shop!")

# Admin: Add hero
@admin_only
async def add_hero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 6:
        await update.message.reply_text("❌ Format: /addhero [name] [attack] [defense] [health] [price]")
        return
    
    name = args[0]
    attack = int(args[1])
    defense = int(args[2])
    health = int(args[3])
    price = int(args[4])
    
    session = Session()
    hero = Hero(
        name=name,
        attack_bonus=attack,
        defense_bonus=defense,
        health_bonus=health,
        price=price,
        description=f"Attack: +{attack}, Defense: +{defense}, Health: +{health}"
    )
    session.add(hero)
    session.commit()
    session.close()
    
    await update.message.reply_text(f"✅ Hero '{name}' berhasil ditambahkan!")

# Admin: Give item to user
@admin_only
async def give_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("❌ Format: /giveitem [user_id] [item_id] [quantity]")
        return
    
    user_id = int(args[0])
    item_id = int(args[1])
    quantity = int(args[2])
    
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    item = session.query(Item).filter_by(id=item_id).first()
    
    if not user or not item:
        await update.message.reply_text("❌ User atau item tidak ditemukan!")
        session.close()
        return
    
    inventory = session.query(Inventory).filter_by(user_id=user.id, item_id=item_id).first()
    if inventory:
        inventory.quantity += quantity
    else:
        inventory = Inventory(user_id=user.id, item_id=item_id, quantity=quantity)
        session.add(inventory)
    
    session.commit()
    session.close()
    
    await update.message.reply_text(f"✅ Berhasil memberikan {quantity}x {item.name} ke user {user_id}!")

# Main menu handler
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("⚔️ Petualangan", callback_data='adventure'), InlineKeyboardButton("🏪 Toko", callback_data='shop')],
        [InlineKeyboardButton("🎒 Inventory", callback_data='inventory'), InlineKeyboardButton("📊 Top Global", callback_data='top_global')],
        [InlineKeyboardButton("💍 Nikah", callback_data='marriage'), InlineKeyboardButton("🏪 Market", callback_data='market')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎮 **Main Menu**\n\n"
        f"Pilih aksi yang ingin dilakukan:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setphoto", set_photo))
    application.add_handler(CommandHandler("additem", add_item))
    application.add_handler(CommandHandler("addhero", add_hero))
    application.add_handler(CommandHandler("giveitem", give_item))
    
    # Callback queries
    application.add_handler(CallbackQueryHandler(profile, pattern='^profile$'))
    application.add_handler(CallbackQueryHandler(adventure, pattern='^adventure$'))
    application.add_handler(CallbackQueryHandler(shop, pattern='^shop$'))
    application.add_handler(CallbackQueryHandler(inventory, pattern='^inventory$'))
    application.add_handler(CallbackQueryHandler(top_global, pattern='^top_global$'))
    application.add_handler(CallbackQueryHandler(marriage, pattern='^marriage$'))
    application.add_handler(CallbackQueryHandler(market, pattern='^market$'))
    application.add_handler(CallbackQueryHandler(main_menu, pattern='^main_menu$'))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("Bot started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

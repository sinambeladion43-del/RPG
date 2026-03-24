# Telegram RPG Adventure Bot

Bot RPG Adventure dengan sistem leveling, pertempuran, market, dan pernikahan.

## Fitur
- Sistem leveling dan EXP
- Pertempuran dengan monster
- Shop system (weapon, armor, consumable, hero)
- Inventory system
- Market system (jual beli antar pemain)
- Marriage system
- Top global leaderboard
- Admin panel dengan fitur set photo

## Setup di Railway

1. Fork repository ini ke GitHub
2. Buat bot di @BotFather dan dapatkan token
3. Deploy ke Railway:
   - Klik "New Project" → "Deploy from GitHub repo"
   - Pilih repository ini
   - Tambahkan environment variables:
     - `BOT_TOKEN`: Token dari BotFather
     - `ADMIN_IDS`: ID Telegram admin (pisah dengan koma)
4. Railway akan otomatis menjalankan bot

## Admin Commands
- `/setphoto [item/weapon/hero] [id]` - Set photo dengan reply ke gambar
- `/additem [name] [type] [price] [attack] [defense] [health]` - Tambah item
- `/addhero [name] [attack] [defense] [health] [price]` - Tambah hero
- `/giveitem [user_id] [item_id] [quantity]` - Beri item ke user

## User Commands
- `/start` - Mulai bot
- Gunakan inline keyboard untuk navigasi

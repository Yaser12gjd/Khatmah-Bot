# هذا الجزء داخل دالة check_prayers
    if prayers and now in [prayers['Fajr'], prayers['Dhuhr'], prayers['Asr'], prayers['Maghrib'], prayers['Isha']]:
        channel = bot.get_channel(int(CHANNEL_ID))
        if channel:
            # صلاة الفجر ترسل 6 صفحات، والباقي 4 صفحات
            if now == prayers['Fajr']:
                pages_to_send = 6
            else:
                pages_to_send = 4
                
            files = []
            for i in range(pages_to_send):
                if current_page > 624: # التأكد من عدد صفحاتك الجديد 624
                    current_page = 1
                image_path = f"images/{current_page}.jpg"
                if os.path.exists(image_path):
                    files.append(discord.File(image_path))
                current_page += 1
            
            if files:
                await channel.send(content=f"📖 **وردكم القرآني لصلاتكم الحالية ({pages_to_send} صفحات)**", files=files)

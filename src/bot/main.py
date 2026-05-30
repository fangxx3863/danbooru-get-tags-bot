import logging
import re
from io import BytesIO
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from src.bot.config_manager import ConfigManager
from src.bot.onnx_tagger import ONNXTagger

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

_config = ConfigManager()
BOT_TOKEN = _config.get_bot_token()

# Custom User-Agent
USER_AGENT = 'fangxx3863Bot/1.0.0'


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    help_text = (
        "欢迎使用 Danbooru 标签获取机器人！\n\n"
        "可用命令：\n"
        "/start - 显示此帮助信息\n"
        "/help - 显示帮助信息\n"
        "/get <URL> - 获取 Danbooru 图片的标签\n"
        "/set_banlist <tag1,tag2,tag3> - 设置过滤标签列表（用逗号分隔）\n"
        "/get_banlist - 查看当前过滤标签列表\n\n"
        "可以直接发送 Danbooru URL 获取标签，也可以直接发送图片进行 AI 标签识别。"
    )
    await update.message.reply_text(help_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Danbooru 标签获取机器人使用说明：\n\n"
        "1. /get <URL> - 输入 Danbooru 图片链接获取标签\n"
        "   例如：/get https://danbooru.donmai.us/posts/10371861\n\n"
        "2. /set_banlist <tag1,tag2,tag3> - 设置需要过滤的标签\n"
        "   例如：/set_banlist 1girl,solo,blue hair\n\n"
        "3. /get_banlist - 查看当前设置的过滤标签\n\n"
        "4. 直接发送 Danbooru URL 同样可以获取标签\n\n"
        "5. 直接发送图片可以进行 AI 标签识别\n\n"
        "获取的标签会按以下分类显示：\n"
        "全部、一般、角色、版权、画师、元信息"
    )
    await update.message.reply_text(help_text)


async def set_banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set the banlist from a comma-separated string."""
    if not context.args:
        await update.message.reply_text('请提供以逗号分隔的标签列表。')
        return

    user_id = update.effective_user.id
    banlist_input = ' '.join(context.args)
    banlist = [tag.strip() for tag in banlist_input.split(',') if tag.strip()]
    _config.set_user_banlist(user_id, banlist)

    banlist_str = ','.join(banlist)
    formatted_banlist = f"**>`{escape_telegram_reserved_characters(banlist_str)}`||\n"
    await update.message.reply_text(f"当前过滤TAGS列表：\n{formatted_banlist}", parse_mode="MarkdownV2")


async def get_banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the current banlist."""
    user_id = update.effective_user.id
    banlist = _config.get_user_banlist_string(user_id)

    formatted_banlist = f"**>`{escape_telegram_reserved_characters(banlist)}`||\n"
    await update.message.reply_text(f"当前过滤TAGS列表：\n{formatted_banlist}", parse_mode="MarkdownV2")


def escape_telegram_reserved_characters(text: str) -> str:
    """Escape Telegram reserved characters to prevent formatting errors."""
    if not isinstance(text, str):
        return str(text)

    # List of characters that need to be escaped in Telegram markdown
    reserved_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    escaped_text = text
    for char in reserved_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')

    return escaped_text


def is_danbooru_url(text: str) -> bool:
    """Check if the text contains a Danbooru post URL."""
    return bool(re.search(r'https?://danbooru\.donmai\.us/posts/\d+', text))


def extract_danbooru_post_id(url: str):
    """Extract post ID from a Danbooru URL."""
    post_id_match = re.search(r'/posts/(\d+)', url)
    return post_id_match.group(1) if post_id_match else None


def filter_and_escape_tags(tag_list: list, banlist: list) -> str:
    """Apply underscore replacement, parenthesis escaping, and banlist filtering.
    Takes a list of tag strings, returns a comma-separated string."""
    banned_lower = set(b.lower() for b in banlist)
    result = []
    for tag in tag_list:
        tag = tag.replace("_", " ")
        tag = tag.replace("(", r"\(").replace(")", r"\)")
        if tag.lower() not in banned_lower:
            result.append(tag)
    return ", ".join(result)


async def process_url(update: Update, url: str, user_id: int):
    """Core logic to fetch and reply tags from a Danbooru URL."""
    # Extract post ID
    post_id = extract_danbooru_post_id(url)
    if not post_id:
        await update.message.reply_text('无法从 URL 中提取帖子 ID。请确保是有效的 Danbooru 帖子 URL。')
        return

    # Reconstruct the proper URL
    base_url = 'https://danbooru.donmai.us'
    json_url = f'{base_url}/posts/{post_id}.json'

    import requests
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(json_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract tag strings
        tag_string_general = data.get('tag_string_general', '')
        tag_string_character = data.get('tag_string_character', '')
        tag_string_copyright = data.get('tag_string_copyright', '')
        tag_string_artist = data.get('tag_string_artist', '')
        tag_string_meta = data.get('tag_string_meta', '')

        # Get banlist for this user
        banlist = _config.get_user_banlist(user_id)

        # Process tags: replace underscores with spaces, escape parentheses, filter banlist
        tag_string_general_filter = filter_and_escape_tags(tag_string_general.split(), banlist)
        tag_string_character_filter = filter_and_escape_tags(tag_string_character.split(), banlist)
        tag_string_copyright_filter = filter_and_escape_tags(tag_string_copyright.split(), banlist)
        tag_string_artist_filter = filter_and_escape_tags(tag_string_artist.split(), banlist)
        tag_string_meta_filter = filter_and_escape_tags(tag_string_meta.split(), banlist)

        # Build "全部" list: collect non-empty categories and join without extra commas
        all_parts = []
        if tag_string_artist_filter:
            all_parts.append(tag_string_artist_filter)
        if tag_string_copyright_filter:
            all_parts.append(tag_string_copyright_filter)
        if tag_string_character_filter:
            all_parts.append(tag_string_character_filter)
        if tag_string_general_filter:
            all_parts.append(tag_string_general_filter)
        tag_string_all_filter = ', '.join(all_parts)

        # Format and send the response
        response_message = (
            f"全部\n**>`{escape_telegram_reserved_characters(tag_string_all_filter)}`||\n"
            f"一般\n**>`{escape_telegram_reserved_characters(tag_string_general_filter)}`||\n"
            f"角色\n**>`{escape_telegram_reserved_characters(tag_string_character_filter)}`||\n"
            f"版权\n**>`{escape_telegram_reserved_characters(tag_string_copyright_filter)}`||\n"
            f"画师\n**>`{escape_telegram_reserved_characters(tag_string_artist_filter)}`||\n"
            f"元信息\n**>`{escape_telegram_reserved_characters(tag_string_meta_filter)}`||\n"
        )

        await update.message.reply_text(response_message, parse_mode="MarkdownV2")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Danbooru: {e}")
        await update.message.reply_text(f'从 Danbooru 获取数据时出错: {e}')
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await update.message.reply_text(f'发生错误: {e}')


async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch tags from Danbooru URL."""
    if not context.args:
        await update.message.reply_text('请提供 Danbooru URL。用法: /get <url>')
        return

    url = ' '.join(context.args)  # Join all arguments in case the URL has spaces

    # Validate URL format
    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text('请提供有效的 URL。')
        return

    if not is_danbooru_url(url):
        await update.message.reply_text('请提供有效的 Danbooru 帖子 URL。')
        return

    await process_url(update, url, update.effective_user.id)


async def handle_direct_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages that contain a Danbooru URL directly (without command)."""
    text = update.message.text
    if is_danbooru_url(text):
        await process_url(update, text, update.effective_user.id)
    else:
        pass


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle a user sending a photo: run ONNX inference and return predicted tags."""
    user_id = update.effective_user.id
    banlist = _config.get_user_banlist(user_id)
    photo = update.message.photo[-1]
    status_msg = await update.message.reply_text("正在分析图片，请稍候...")

    try:
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = BytesIO()
        await file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)
        pil_image = Image.open(photo_bytes)

        tagger = ONNXTagger()
        display_tags = tagger.tag(pil_image)

        def _tags_for(cat):
            tag_probs = display_tags.get(cat, [])
            tag_names = [t for t, _ in tag_probs]
            return filter_and_escape_tags(tag_names, banlist)

        gen = _tags_for("一般")
        char = _tags_for("角色")
        copyr = _tags_for("版权")
        art = _tags_for("画师")
        meta = _tags_for("元信息")

        all_parts = [p for p in [art, copyr, char, gen] if p]
        all_tags = ", ".join(all_parts)

        response = (
            f"全部\n**>`{escape_telegram_reserved_characters(all_tags)}`||\n"
            f"一般\n**>`{escape_telegram_reserved_characters(gen)}`||\n"
            f"角色\n**>`{escape_telegram_reserved_characters(char)}`||\n"
            f"版权\n**>`{escape_telegram_reserved_characters(copyr)}`||\n"
            f"画师\n**>`{escape_telegram_reserved_characters(art)}`||\n"
            f"元信息\n**>`{escape_telegram_reserved_characters(meta)}`||\n"
        )

        if len(response) > 4000:
            parts = {
                "一般": gen.split(", ") if gen else [],
                "角色": char.split(", ") if char else [],
                "版权": copyr.split(", ") if copyr else [],
                "画师": art.split(", ") if art else [],
                "元信息": meta.split(", ") if meta else [],
            }
            while len(response) > 4000:
                longest = max(parts, key=lambda k: len(parts[k]))
                if not parts[longest]:
                    break
                parts[longest].pop()
                gen = ", ".join(parts["一般"])
                char = ", ".join(parts["角色"])
                copyr = ", ".join(parts["版权"])
                art = ", ".join(parts["画师"])
                meta = ", ".join(parts["元信息"])
                all_parts_list = [p for p in [art, copyr, char, gen] if p]
                all_tags = ", ".join(all_parts_list)
                response = (
                    f"全部\n**>`{escape_telegram_reserved_characters(all_tags)}`||\n"
                    f"一般\n**>`{escape_telegram_reserved_characters(gen)}`||\n"
                    f"角色\n**>`{escape_telegram_reserved_characters(char)}`||\n"
                    f"版权\n**>`{escape_telegram_reserved_characters(copyr)}`||\n"
                    f"画师\n**>`{escape_telegram_reserved_characters(art)}`||\n"
                    f"元信息\n**>`{escape_telegram_reserved_characters(meta)}`||\n"
                )

        await status_msg.edit_text(response, parse_mode="MarkdownV2")
    except Exception as e:
        logger.error("Photo processing error: %s", e)
        await status_msg.edit_text(f"图片分析失败: {e}")


def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("set_banlist", set_banlist_command))
    application.add_handler(CommandHandler("get_banlist", get_banlist_command))
    application.add_handler(CommandHandler("get", get_command))

    # Register handler for direct URL messages (non-command text)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_direct_url
        )
    )

    # Register handler for photo messages
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo
        )
    )

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()



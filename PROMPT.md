使用Python写一个程序，调用python-telegram-bot库，

给出一个全局变量BOT_TOKEN，先从系统环境变量获取这个BOT_TOKEN，如果没有则使用全局变量定义的

如果当前目录下不存在config.ini则创建一个默认的

注册一个/set_banlist命令，接收一个由英文逗号","为分隔的字符串，收完存进config.ini里

注册一个/get_banlist命令，打印config.ini里的banlist字符串，打印格式为
当前过滤TAGS列表：
f"**>`{escape_telegram_reserved_characters(banlist)}`||\n"

注意实现escape_telegram_reserved_characters，确保正确转义防止TG发送出错



接着注册一个/get命令，接收一个url参数例如/get https://danbooru.donmai.us/posts/10371861

接着在url末尾加上.json变为https://danbooru.donmai.us/posts/10371861.json，GET这个url获取json内容

你将得到以下字段

{

  "id": 10371861,

  "created_at": "2025-12-03T04:01:27.157-05:00",

  "uploader_id": 776828,

  "score": 0,

  "source": "https://twitter.com/machuuu68/status/1653003404179013638",

  "md5": "70bfef975030cf7661daf67895345844",

  "last_comment_bumped_at": null,

  "rating": "g",

  "image_width": 2480,

  "image_height": 3000,

  "tag_string": "1girl ? absurdres blue_hair blue_pajamas blue_pants blue_shirt bocchi_the_rock! collared_shirt cup disposable_coffee_cup disposable_cup english_commentary food hair_ornament hairclip highres holding holding_cup machuuu68 medium_hair pajamas pants pizza pizza_slice shirt simple_background yamada_ryo yellow_eyes",

  "fav_count": 0,

  "file_ext": "jpg",

  "last_noted_at": null,

  "parent_id": null,

  "has_children": false,

  "approver_id": null,

  "tag_count_general": 23,

  "tag_count_artist": 1,

  "tag_count_character": 1,

  "tag_count_copyright": 1,

  "file_size": 430082,

  "up_score": 0,

  "down_score": 0,

  "is_pending": true,

  "is_flagged": false,

  "is_deleted": false,

  "tag_count": 29,

  "updated_at": "2025-12-03T04:01:38.786-05:00",

  "is_banned": false,

  "pixiv_id": null,

  "last_commented_at": null,

  "has_active_children": false,

  "bit_flags": 0,

  "tag_count_meta": 3,

  "has_large": true,

  "has_visible_children": false,

  "media_asset": {

    "id": 38289602,

    "created_at": "2025-12-03T03:59:55.418-05:00",

    "updated_at": "2025-12-03T03:59:57.092-05:00",

    "md5": "70bfef975030cf7661daf67895345844",

    "file_ext": "jpg",

    "file_size": 430082,

    "image_width": 2480,

    "image_height": 3000,

    "duration": null,

    "status": "active",

    "file_key": "A1IyEpxFT",

    "is_public": true,

    "pixel_hash": "9fadf4ea4085aa067ec5d3eab48f87a1",

    "variants": [

      {

        "type": "180x180",

        "url": "https://cdn.donmai.us/180x180/70/bf/70bfef975030cf7661daf67895345844.jpg",

        "width": 149,

        "height": 180,

        "file_ext": "jpg"

      },

      {

        "type": "360x360",

        "url": "https://cdn.donmai.us/360x360/70/bf/70bfef975030cf7661daf67895345844.jpg",

        "width": 298,

        "height": 360,

        "file_ext": "jpg"

      },

      {

        "type": "720x720",

        "url": "https://cdn.donmai.us/720x720/70/bf/70bfef975030cf7661daf67895345844.webp",

        "width": 595,

        "height": 720,

        "file_ext": "webp"

      },

      {

        "type": "sample",

        "url": "https://cdn.donmai.us/sample/70/bf/sample-70bfef975030cf7661daf67895345844.jpg",

        "width": 850,

        "height": 1028,

        "file_ext": "jpg"

      },

      {

        "type": "original",

        "url": "https://cdn.donmai.us/original/70/bf/70bfef975030cf7661daf67895345844.jpg",

        "width": 2480,

        "height": 3000,

        "file_ext": "jpg"

      }

    ]

  },

  "tag_string_general": "1girl ? blue_hair blue_pajamas blue_pants blue_shirt collared_shirt cup disposable_coffee_cup disposable_cup food hair_ornament hairclip holding holding_cup medium_hair pajamas pants pizza pizza_slice shirt simple_background yellow_eyes",

  "tag_string_character": "yamada_ryo",

  "tag_string_copyright": "bocchi_the_rock!",

  "tag_string_artist": "machuuu68",

  "tag_string_meta": "absurdres english_commentary highres",

  "file_url": "https://cdn.donmai.us/original/70/bf/70bfef975030cf7661daf67895345844.jpg",

  "large_file_url": "https://cdn.donmai.us/sample/70/bf/sample-70bfef975030cf7661daf67895345844.jpg",

  "preview_file_url": "https://cdn.donmai.us/180x180/70/bf/70bfef975030cf7661daf67895345844.jpg"

}



提取出tag_string，tag_string_general，tag_string_character，tag_string_copyright，tag_string_artist，tag_string_meta这几个字段，使用空格split开，接着对每个tag做以下操作，

1. 把下划线_转为空格

2. 把括号()转义\( \)

3. 把banlist内的tag剔除（注意在split后需要把首尾空格去除，防止搜索出错）

接着按以下格式发送给用户，tags用逗号分隔

全部
f"**>`{escape_telegram_reserved_characters(tag_string_filter)}`||\n"
一般
f"**>`{escape_telegram_reserved_characters(tag_string_general_filter)}`||\n"
角色
f"**>`{escape_telegram_reserved_characters(tag_string_character_filter)}`||\n"
版权
f"**>`{escape_telegram_reserved_characters(tag_string_copyright_filter)}`||\n"
画师
f"**>`{escape_telegram_reserved_characters(tag_string_artist_filter)}`||\n"
元信息
f"**>`{escape_telegram_reserved_characters(tag_string_meta_filter)}`||\n"


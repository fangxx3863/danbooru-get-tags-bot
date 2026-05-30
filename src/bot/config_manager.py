import os
import logging
from configparser import ConfigParser

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.ini"

DEFAULT_BANLIST_TAGS = [
    "censor", "censored", "bar censor", "mosaic censoring",
    "web address", "patreon username", "twitter username", "username",
    "signature", "text", "speech bubble", "artist name", "body writing",
    "logo", "censored text", "dated", "watermark", "request inset",
    "english text", "group name", "patreon logo", "blank censor",
    "twitter x logo", "heart censor", "sample watermark", "thought bubble",
    "watermark grid", "censored nipples", "korean text", "scribble censor",
    "blur sensor", "art program in frame", r"procreate \(software\)",
    "fat", "fat man", "ugly bastard"
]
DEFAULT_BANLIST_STR = ",".join(DEFAULT_BANLIST_TAGS)


def _load_dotenv():
    dotenv_path = ".env"
    if not os.path.exists(dotenv_path):
        return
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


class ConfigManager:
    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        _load_dotenv()
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        if not os.path.exists(self.config_file):
            config = ConfigParser()
            config["SETTINGS"] = {"bot_token": ""}
            config["DEFAULT_BANLIST"] = {"default_banlist": DEFAULT_BANLIST_STR}
            with open(self.config_file, "w", encoding="utf-8") as f:
                config.write(f)
            logger.info("Created default %s", self.config_file)
            return

        config = ConfigParser()
        config.read(self.config_file, encoding="utf-8")
        if "DEFAULT_BANLIST" not in config and config.has_option("SETTINGS", "banlist"):
            old_banlist = config.get("SETTINGS", "banlist", fallback="")
            config["DEFAULT_BANLIST"] = {"default_banlist": old_banlist}
            config.remove_option("SETTINGS", "banlist")
            if "bot_token" not in config.options("SETTINGS"):
                config["SETTINGS"]["bot_token"] = ""
            with open(self.config_file, "w", encoding="utf-8") as f:
                config.write(f)
            logger.info("Migrated %s from old format to per-user format", self.config_file)

    def _read(self) -> ConfigParser:
        config = ConfigParser()
        config.read(self.config_file, encoding="utf-8")
        return config

    def get_bot_token(self) -> str:
        token = os.getenv("BOT_TOKEN", "").strip()
        if token:
            return token
        config = self._read()
        token = config.get("SETTINGS", "bot_token", fallback="").strip()
        if token:
            return token
        raise RuntimeError(
            "BOT_TOKEN not set. Set the environment variable BOT_TOKEN "
            "or add bot_token under [SETTINGS] in config.ini"
        )

    def get_default_banlist(self) -> list:
        config = self._read()
        banlist_str = config.get("DEFAULT_BANLIST", "default_banlist", fallback=DEFAULT_BANLIST_STR)
        return [t.strip() for t in banlist_str.split(",") if t.strip()]

    def get_user_banlist(self, user_id: int) -> list:
        config = self._read()
        section = f"USER_{user_id}"
        if section not in config:
            default = self.get_default_banlist()
            config[section] = {"banlist": ",".join(default)}
            with open(self.config_file, "w", encoding="utf-8") as f:
                config.write(f)
            logger.info("Initialized banlist for user %d from default", user_id)
            return default
        banlist_str = config.get(section, "banlist", fallback="")
        return [t.strip() for t in banlist_str.split(",") if t.strip()]

    def set_user_banlist(self, user_id: int, tags: list) -> None:
        config = self._read()
        section = f"USER_{user_id}"
        if section not in config:
            config[section] = {}
        config[section]["banlist"] = ",".join(tags)
        with open(self.config_file, "w", encoding="utf-8") as f:
            config.write(f)

    def get_user_banlist_string(self, user_id: int) -> str:
        config = self._read()
        section = f"USER_{user_id}"
        if section not in config:
            default = self.get_user_banlist(user_id)
            return ",".join(default)
        return config.get(section, "banlist", fallback="")

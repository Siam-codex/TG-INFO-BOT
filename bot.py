# ================================================================
# SIAM CODEX - Free Fire Info Telegram Bot
# Commands: /info, /get, /level, /region, /banner, /outfit
# ================================================================

import asyncio, os, io, sys, time, json, logging
import httpx
from PIL import Image, ImageDraw, ImageFont

# ── Telegram ──
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from telegram.constants import ParseMode, ChatAction

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))

# ================================================================
# CONFIG
# ================================================================
BOT_TOKEN  = "8923925114:AAEjbkiapvfSmvcG1r5yT_J6rSbJRNrWqUI"
API_BASE   = "https://kawsarxinfo.devs.surf/info"

# ── Premium custom emoji — HTML parse mode only ──
def tge(emoji_id, fallback):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

PE = {
    "fire":    tge("5368324170671202286",  "⚡"),
    "star":    tge("5368324170671202286",  "⭐"),
    "crown":   tge("5472308579923914000",  "👑"),
    "diamond": tge("5775423885478923387",  "💎"),
    "shield":  tge("5472055112702629499",  "🛡️"),
    "sword":   tge("5447644880824219747",  "⚔️"),
    "trophy":  tge("5434209861466478800",  "🏆"),
    "rank":    tge("5415765476692778931",  "🎯"),
    "pet":     tge("5413879192267805083",  "🐾"),
    "guild":   tge("5413025044740743620",  "🏰"),
    "outfit":  tge("5472355112476261621",  "👗"),
    "skill":   tge("5368324170671202286",  "⚡"),
    "weapon":  tge("5415879590930421157",  "🔫"),
    "credit":  tge("5413109965695067099",  "🏅"),
    "social":  tge("5471985284632490967",  "💬"),
    "flag":    tge("5413879192267805083",  "🌍"),
    "level":   tge("5413025044740743620",  "🎮"),
    "exp":     tge("5775423885478923387",  "✨"),
    "likes":   tge("5447644880824219747",  "❤️"),
    "pin":     tge("5415765476692778931",  "📌"),
    "banner":  tge("5471985284632490967",  "🎨"),
    "avatar":  tge("5472308579923914000",  "🖼"),
    "id":      tge("5415765476692778931",  "🆔"),
    "date":    tge("5413109965695067099",  "📅"),
    "login":   tge("5413025044740743620",  "🕐"),
    "version": tge("5368324170671202286",  "📦"),
    "season":  tge("5472355112476261621",  "🗓"),
    "type":    tge("5413879192267805083",  "🔖"),
    "name":    tge("5415879590930421157",  "🏷"),
    "region":  tge("5471985284632490967",  "🌍"),
    "bot":     tge("5447644880824219747",  "🤖"),
    "check":   tge("5775423885478923387",  "✅"),
    "error":   tge("5472055112702629499",  "❌"),
    "wait":    tge("5434209861466478800",  "⏳"),
    "warn":    tge("5413109965695067099",  "⚠️"),
    "info":    tge("5415765476692778931",  "🔍"),
    "bp":      tge("5472308579923914000",  "🎖"),
    "show":    tge("5413025044740743620",  "🔰"),
    "member":  tge("5471985284632490967",  "👥"),
    "owner":   tge("5447644880824219747",  "👤"),
    "sig":     tge("5368324170671202286",  "✍️"),
    "lang":    tge("5472355112476261621",  "🗣"),
    "score":   tge("5413879192267805083",  "📊"),
    "state":   tge("5415879590930421157",  "📋"),
    "map":     tge("5434209861466478800",  "🗺️"),
}

ICON_CDN_URL = "https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG"

FONT_FILE     = os.path.join(current_dir, "arial_unicode_bold.otf")
FONT_CHEROKEE = os.path.join(current_dir, "NotoSansCherokee.ttf")
OUTFIT_BG     = os.path.join(current_dir, "outfit_bg.png")

OUTFIT_RING_SLOTS = [
    (182, 169, 86), (433, 305, 75), (989, 302, 90), (1220, 169, 75),
    (173, 626, 81), (1223, 628, 92), (449, 865, 89), (250, 980, 88),
    (1013, 850, 87),
]
RING_PADDING = 16
AVATAR_ZOOM, BANNER_START_X, BANNER_START_Y = 1.26, 0.25, 0.29
BANNER_END_X, BANNER_END_Y = 0.81, 0.65

# ================================================================
# ITEM DB — loaded at startup from data.json
# Falls back to ff-item.netlify.app for unknown IDs at runtime
# ================================================================
ITEM_DB: dict[str, dict] = {}

def load_item_db():
    """Load data.json into ITEM_DB keyed by str(itemID)."""
    global ITEM_DB
    db_path = os.path.join(current_dir, "data.json")
    if not os.path.exists(db_path):
        logger.warning("data.json not found — item name lookups will use netlify fallback only")
        return
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        ITEM_DB = {str(item["itemID"]): item for item in items if "itemID" in item}
        logger.info(f"ITEM_DB loaded: {len(ITEM_DB)} items")
    except Exception as e:
        logger.error(f"Failed to load data.json: {e}")

# Netlify item cache — avoid re-fetching the same ID twice
_netlify_cache: dict[str, dict] = {}

def _re(emoji_id, fallback):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

RARE_EMOJI = {
    "ORANGE": _re("5778423952314778513", "🟠"),
    "PURPLE": _re("5778725175251523833", "🟣"),
    "BLUE":   _re("5778704455678402518", "🔵"),
    "GREEN":  _re("5778669706040082621", "🟢"),
    "WHITE":  _re("5778610009598517505", "⚪"),
    "NONE":   _re("5445284452725823488", "⬜"),
}

RARE_LABEL = {
    "ORANGE": "Orange",
    "PURPLE": "Purple",
    "BLUE":   "Blue",
    "GREEN":  "Green",
    "WHITE":  "White",
    "NONE":   "",
}

async def _fetch_netlify_info(item_id: str) -> dict:
    """Fetch full item info from ff-item.netlify.app for IDs missing from ITEM_DB."""
    if item_id in _netlify_cache:
        return _netlify_cache[item_id]
    result = {}
    try:
        url = f"https://ff-item.netlify.app/.netlify/functions/item?id={item_id}"
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get(url)
            if r.status_code == 200:
                data = r.json()
                name = data.get("name") or data.get("itemName") or ""
                if name and name.strip():
                    result = {
                        "name":        name.strip(),
                        "type":        data.get("type", ""),
                        "Rare":        data.get("Rare", data.get("rare", "")),
                        "description": data.get("description", ""),
                        "tag":         data.get("tag", ""),
                        "itemID":      item_id,
                    }
                    _netlify_cache[item_id] = result
    except Exception as e:
        logger.debug(f"Netlify fetch error for {item_id}: {e}")
    return result

def item_info_sync(item_id) -> dict:
    """Synchronous full-info lookup from ITEM_DB. Returns empty dict if not found."""
    sid = str(item_id)
    if sid in ITEM_DB:
        return ITEM_DB[sid]
    return {}

async def item_info(item_id) -> dict:
    """Async full-info lookup — ITEM_DB first, netlify fallback, empty dict last resort."""
    sid = str(item_id)
    if not sid or sid in ("0", "None", "null", ""):
        return {}
    if sid in ITEM_DB:
        return ITEM_DB[sid]
    return await _fetch_netlify_info(sid)

def item_name_sync(item_id) -> str:
    """Synchronous name lookup — returns name from ITEM_DB or empty string."""
    info = item_info_sync(item_id)
    return info.get("name", "")

async def item_name(item_id) -> str:
    """Async name lookup — full info pipeline, name only."""
    info = await item_info(item_id)
    if info:
        return info.get("name", str(item_id))
    return str(item_id) if item_id and str(item_id) not in ("0", "None", "null", "") else "Not Found"

def item_card(info: dict, item_id=None) -> str:
    """
    Renders a full item card from an info dict.
    Format:  Name [RareEmoji Type] • Tag • Description
    Falls back gracefully for missing fields.
    """
    if not info:
        return str(item_id) if item_id else "Not Found"

    name  = info.get("name", "")          or str(item_id or "?")
    itype = info.get("type", "")          or ""
    rare  = str(info.get("Rare", ""))     .upper()
    desc  = info.get("description", "")  or ""
    tag   = info.get("tag", "")          or ""
    iid   = str(info.get("itemID", item_id or ""))

    rare_icon = RARE_EMOJI.get(rare, "")
    parts = [f"<b>{name}</b>"]
    meta = []
    if rare_icon:
        meta.append(rare_icon)
    if rare and rare not in ("NONE", ""):
        meta.append(rare.capitalize())
    if itype:
        meta.append(itype)
    if meta:
        parts.append(f"[{' · '.join(meta)}]")
    if iid:
        parts.append(f"<code>#{iid}</code>")
    if tag:
        parts.append(f"({tag})")
    if desc:
        # Trim long descriptions to keep captions readable
        d = desc if len(desc) <= 80 else desc[:77] + "..."
        parts.append(f"— {d}")
    return " ".join(parts)

async def item_card_async(item_id) -> str:
    """Full async pipeline: fetch info → render card."""
    sid = str(item_id)
    if not sid or sid in ("0", "None", "null", ""):
        return "Not Found"
    info = await item_info(item_id)
    return item_card(info, item_id=sid)

# ================================================================
# API FETCH
# ================================================================
async def fetch_player_raw(uid: str) -> dict | None:
    url = f"{API_BASE}?uid={uid}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.get(url)
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        logger.error(f"API fetch error: {e}")
    return None

# ================================================================
# ICONS
# ================================================================
async def fetch_icon(item_id):
    if not item_id or str(item_id) in ("0", "None", "null", ""):
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as c:
            r = await c.get(f"{ICON_CDN_URL}/{item_id}.png")
            if r.status_code == 200:
                return r.content
    except:
        pass
    return None

def to_img(b, size=(100, 100)):
    if b:
        try:
            return Image.open(io.BytesIO(b)).convert("RGBA")
        except:
            pass
    return Image.new("RGBA", size, (0, 0, 0, 0))

def load_font(size, path=None):
    p = path or FONT_FILE
    try:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    except:
        pass
    return ImageFont.load_default()

def is_cherokee(ch):
    return 0x13A0 <= ord(ch) <= 0x13FF or 0xAB70 <= ord(ch) <= 0xABBF

# ================================================================
# BANNER IMAGE
# ================================================================
def _build_banner(name, level, guild, av_b, bn_b, pin_b):
    av  = to_img(av_b); bn = to_img(bn_b); pin = to_img(pin_b)
    TH  = 400; zs = int(TH * AVATAR_ZOOM)
    av  = av.resize((zs, zs), Image.LANCZOS)
    c = zs // 2; h = TH // 2
    av  = av.crop((c - h, c - h, c + h, c + h))
    bn  = bn.rotate(3, expand=True); bw, bh = bn.size
    bn  = bn.crop((bw * BANNER_START_X, bh * BANNER_START_Y,
                   bw * BANNER_END_X,   bh * BANNER_END_Y))
    bw, bh = bn.size
    bn  = bn.resize((int(TH * (bw / bh) * 2), TH), Image.LANCZOS)
    final = Image.new("RGBA", (av.width + bn.width, TH))
    final.paste(av, (0, 0)); final.paste(bn, (av.width, 0))
    draw = ImageDraw.Draw(final)
    fb = load_font(125); fbc = load_font(125, FONT_CHEROKEE)
    fs = load_font(95);  fsc = load_font(95, FONT_CHEROKEE); fl = load_font(50)

    def dt(x, y, text, fm, fa, st):
        text = text or ""; cx = x
        for ch in text:
            f = fa if is_cherokee(ch) else fm
            for dx in range(-st, st + 1):
                for dy in range(-st, st + 1):
                    draw.text((cx + dx, y + dy), ch, font=f, fill="black")
            draw.text((cx, y), ch, font=f, fill="white"); cx += f.getlength(ch)

    dt(av.width + 65, 40, name or "Unknown", fb, fbc, 4)
    dt(av.width + 65, 220, guild or "", fs, fsc, 3)
    try:
        if pin.size != (100, 100):
            pin = pin.resize((130, 130))
        final.paste(pin, (0, TH - 130), pin)
    except:
        pass
    lvl = f"Lvl.{level or 0}"; w, ht = draw.textbbox((0, 0), lvl, font=fl)[2:]
    draw.rectangle([final.width - w - 60, TH - ht - 50, final.width, TH], fill="black")
    draw.text((final.width - w - 30, TH - ht - 40), lvl, font=fl, fill="white")
    out = io.BytesIO(); final.save(out, "PNG"); out.seek(0); return out

async def make_banner(raw):
    ai    = raw.get("AccountInfo", {})
    guild = raw.get("GuildInfo", {})
    av_b, bn_b, pin_b = await asyncio.gather(
        fetch_icon(ai.get("AccountAvatarId")),
        fetch_icon(ai.get("AccountBannerId")),
        fetch_icon(None)
    )
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _build_banner,
        ai.get("AccountName"), ai.get("AccountLevel"),
        guild.get("GuildName"), av_b, bn_b, pin_b)

# ================================================================
# OUTFIT IMAGE
# ================================================================
def _make_circ(img_bytes, size):
    icon = to_img(img_bytes).resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(icon, (0, 0), mask)
    return out

async def make_outfit(raw):
    profile  = raw.get("AccountProfileInfo", {})
    clothes  = list(profile.get("EquippedOutfit", []) or [])
    pet_skin = (raw.get("petInfo", {}) or {}).get("skinId")
    if pet_skin:
        clothes.append(pet_skin)
    item_ids   = clothes[:len(OUTFIT_RING_SLOTS)]
    icon_bytes = await asyncio.gather(*[fetch_icon(i) for i in item_ids])
    bg = Image.open(OUTFIT_BG).convert("RGBA") if os.path.exists(OUTFIT_BG) \
         else Image.new("RGBA", (1400, 1123), (10, 8, 30, 255))
    for (cx, cy, r), ib in zip(OUTFIT_RING_SLOTS, icon_bytes):
        if not ib:
            continue
        size = max(40, int(2 * (r - RING_PADDING)))
        icon = _make_circ(ib, size)
        bg.paste(icon, (cx - size // 2, cy - size // 2), icon)
    out = io.BytesIO(); bg.save(out, "PNG"); out.seek(0); return out

# ================================================================
# FORMAT DATA
# ================================================================
def ts(v):
    from datetime import datetime, timezone, timedelta
    try:
        n = int(v)
        if n > 1000000000:
            ist = timezone(timedelta(hours=5, minutes=30))
            dt  = datetime.fromtimestamp(n, tz=ist)
            return dt.strftime("%d %B %Y at %I:%M:%S %p (IST)")
    except:
        pass
    return str(v) if v else "Not Found"

def val(x, default="Not Found"):
    if x is None or x == "" or x == 0 or x == "0" or str(x) == "None":
        return default
    return str(x)

def br_rank_name(pts):
    try:
        p = int(pts)
        if p <= 0:    return f"Bronze I ({p})"
        if p < 200:   return f"Bronze I ({p})"
        if p < 400:   return f"Bronze II ({p})"
        if p < 600:   return f"Bronze III ({p})"
        if p < 733:   return f"Silver I ({p})"
        if p < 866:   return f"Silver II ({p})"
        if p < 1000:  return f"Silver III ({p})"
        if p < 1167:  return f"Gold I ({p})"
        if p < 1334:  return f"Gold II ({p})"
        if p < 1500:  return f"Gold III ({p})"
        if p < 1667:  return f"Platinum I ({p})"
        if p < 1834:  return f"Platinum II ({p})"
        if p < 2000:  return f"Platinum III ({p})"
        if p < 2334:  return f"Diamond I ({p})"
        if p < 2667:  return f"Diamond II ({p})"
        if p < 3000:  return f"Diamond III ({p})"
        if p < 6000:  return f"Heroic ({p})"
        return f"Grandmaster ({p})"
    except:
        return val(pts)

def cs_rank_name(pts):
    try:
        p = int(pts)
        if p <= 0:    return "Bronze I (0 Star)"
        if p < 10:    return f"Bronze I ({p} Star{'s' if p > 1 else ''})"
        if p < 25:    return f"Silver I ({p - 10 + 1} Star)"
        if p < 50:    return f"Gold I ({p - 25 + 1} Star)"
        if p < 100:   return f"Platinum I ({p - 50 + 1} Star)"
        if p < 200:   return f"Diamond I ({p - 100 + 1} Star)"
        if p < 400:   return f"Heroic ({p - 200 + 1} Star)"
        return f"Grandmaster ({p})"
    except:
        return val(pts)

def bp_type(v):
    try:
        t = int(v)
        return {1: "Basic", 2: "Premium", 3: "Elite"}.get(t, f"Type {t}")
    except:
        return val(v)

def fmt(raw):
    ai      = raw.get("AccountInfo", {}) or {}
    profile = raw.get("AccountProfileInfo", {}) or {}
    guild   = raw.get("GuildInfo", {}) or {}
    pet     = raw.get("petInfo", {}) or {}
    credit  = raw.get("creditScoreInfo", {}) or {}
    social  = raw.get("socialinfo", {}) or {}

    skills_raw = list(profile.get("EquippedSkills", []) or [])
    skill_list = []
    seen_sk = set()
    for s in skills_raw:
        key = str(s)
        if key not in seen_sk:
            seen_sk.add(key)
            skill_list.append(key)

    weapon_raw  = ai.get("EquippedWeapon", []) or []
    weapon_list = [str(w) for w in weapon_raw]
    clothes     = list(profile.get("EquippedOutfit", []) or [])

    return {
        "uid":          str(ai.get("accountId", ai.get("accountId", "N/A")) or "N/A"),
        "name":         ai.get("AccountName", "Unknown"),
        "level":        ai.get("AccountLevel", 0),
        "exp":          ai.get("AccountEXP", 0),
        "region":       ai.get("AccountRegion", "?"),
        "liked":        ai.get("AccountLikes", 0),
        "acc_type":     ai.get("AccountType", ""),
        "title":        ai.get("Title", ""),
        "create_at":    ai.get("AccountCreateTime", ""),
        "last_login":   ai.get("AccountLastLogin", ""),
        "release_ver":  ai.get("ReleaseVersion", ""),
        "avatar_id":    ai.get("AccountAvatarId", ""),
        "banner_id":    ai.get("AccountBannerId", ""),
        "pin_id":       ai.get("AccountBPID", ""),
        "bp_badges":    ai.get("AccountBPBadges", ""),
        "br_rank":      ai.get("BrRankPoint", ""),
        "cs_rank":      ai.get("CsRankPoint", ""),
        "show_br":      ai.get("ShowBrRank", ""),
        "show_cs":      ai.get("ShowCsRank", ""),
        "rank_show":    social.get("rankShow", ""),
        "signature":    social.get("signature", ""),
        "language":     social.get("language", ""),
        "credit":       credit.get("creditScore", ""),
        "pet_id":       pet.get("id", ""),
        "pet_lv":       pet.get("level", 0),
        "pet_exp":      pet.get("exp", 0),
        "pet_is_used":  pet.get("isSelected", False),
        "guild_name":   guild.get("GuildName", ""),
        "guild_id":     str(guild.get("GuildID", "")),
        "guild_lv":     guild.get("GuildLevel", ""),
        "guild_mem":    guild.get("GuildMember", ""),
        "guild_cap":    guild.get("GuildCapacity", ""),
        "guild_own":    str(guild.get("GuildOwner", "")),
        "outfit":       clothes,
        "skills":       skill_list,
        "weapons":      weapon_list,
    }

# ── Rank/language helpers that don't need async ─────────────────
RANK_SHOW_MAP = {
    "RankShow_CS": "CsRanked",
    "RankShow_BR": "BrRanked",
    "RankShow_None": "Hidden",
}

LANGUAGE_NAMES = {
    "Language_EN": "English",
    "Language_BD": "Bengali",
    "Language_IN": "Hindi",
    "Language_ID": "Indonesian",
    "Language_TH": "Thai",
    "Language_VN": "Vietnamese",
    "Language_AR": "Arabic",
    "Language_BR": "Portuguese",
    "Language_PH": "Filipino",
    "Language_MY": "Malay",
    "Language_TW": "Traditional Chinese",
    "Language_CN": "Simplified Chinese",
    "Language_RU": "Russian",
    "Language_TR": "Turkish",
    "Language_PT": "Portuguese",
    "Language_ES": "Spanish",
    "Language_SA": "Arabic",
}

def language_name(lang):
    return LANGUAGE_NAMES.get(str(lang), str(lang) if lang else "Not Found")

def rank_show_name(rs):
    return RANK_SHOW_MAP.get(str(rs), str(rs) if rs else "Hidden")

# ================================================================
# FETCH LEADER
# ================================================================
async def fetch_leader_raw(leader_uid: str) -> dict | None:
    if not leader_uid or leader_uid in ("", "0", "None"):
        return None
    try:
        url = f"{API_BASE}?uid={leader_uid}"
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(url)
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        logger.warning(f"Leader fetch error uid={leader_uid}: {e}")
    return None

# ================================================================
# CAPTION BUILDER — fully async, HTML parse mode, ITEM_DB lookups
# ================================================================
async def build_full_caption(d, leader_raw=None):
    e = PE

    flags = {
        "BD": "🇧🇩", "IND": "🇮🇳", "ME": "🇸🇦", "ID": "🇮🇩",
        "TH": "🇹🇭", "BR": "🇧🇷", "VN": "🇻🇳", "SG": "🇸🇬",
        "MY": "🇲🇾", "PK": "🇵🇰", "NA": "🇺🇸", "TW": "🇹🇼",
    }
    flag = flags.get(str(d["region"]).upper(), "🌍")

    def row(icon, label, value):
        return f"  {icon} <b>{label}:</b> <code>{value}</code>"

    def section(header_icon, header_text, rows):
        inner = "\n".join(rows)
        return (
            f"<blockquote>"
            f"{header_icon} <b>{header_text}</b>\n"
            f"┌─────────────────────────\n"
            f"{inner}\n"
            f"└─────────────────────────"
            f"</blockquote>"
        )

    # ── Character/skill names ──────────────────────────────────
    CHAR_NAMES = {
        "1": "None", "2": "None", "3": "None", "4": "None", "5": "None",
        "8": "Thiva", "9": "None", "10": "None", "11": "None", "12": "None",
        "16": "Maxim", "100": "Kelly", "101": "Nikita", "102": "Miguel",
        "105": "Andrew", "106": "Ford", "107": "Laura", "108": "Moco",
        "109": "Olivia", "110": "Paloma", "111": "Antonio", "112": "Caroline",
        "113": "Hayato", "114": "Alvaro", "116": "Steffie", "117": "A124",
        "118": "Kla", "119": "Maxim", "120": "Rafael", "121": "Notora",
        "122": "Jota", "123": "Shani", "124": "Maro", "125": "Leon",
        "126": "Jai", "127": "Luqueta", "128": "Wolfrahh", "129": "Clu",
        "130": "Awakened Hayato", "131": "Kapella", "132": "Kiran",
        "133": "DJ Alok", "134": "Chrono", "136": "Skyler",
        "137": "Awakened Kelly", "138": "Awakened Andrew",
        "139": "Dasha", "140": "Xayne", "141": "Misha", "142": "Shirou",
        "143": "Awakened A124", "144": "Nairi", "145": "Dimitri",
        "146": "Ascella", "147": "Thiva", "148": "Awakened Jota", "149": "Iris",
        "200": "Wukong", "201": "K", "202": "Jai", "203": "Lena",
        "204": "Awakened Nikita", "205": "Santino", "206": "Snowelle",
        "207": "Tatsuya", "208": "Suzy", "209": "Asha", "210": "Orion",
        "211": "Lila", "212": "Sonia", "213": "Zoe", "214": "Dandelion",
        "706": "Wukong", "1206": "Clu", "1804": "Rafael",
        "4602": "DJ Alok", "7206": "Wukong",
    }

    skill_display = "Not Found"
    if d["skills"]:
        raw_skills = d["skills"]
        SLOT_TYPE = {0: "Active", 1: "Passive", 2: "Passive", 3: "Passive"}
        slot_parts = []
        group = 0
        i = 0
        while i < len(raw_skills) and group < 4:
            char_id = str(raw_skills[i])
            cname = CHAR_NAMES.get(char_id)
            if cname and cname != "None":
                stype = SLOT_TYPE.get(group, "Passive")
                slot_parts.append(f"{cname} ({stype})")
            group += 1
            i += 4
        if not slot_parts:
            seen = []
            for sid in raw_skills:
                n = CHAR_NAMES.get(str(sid))
                if n and n != "None" and n not in seen:
                    seen.append(n)
            skill_display = ", ".join(seen) if seen else " | ".join(str(s) for s in raw_skills[:4])
        else:
            skill_display = ", ".join(slot_parts)

    # ── Async item card lookups (parallel) — full ID+name+type+rarity+desc ──
    async def _maybe_card(x):
        return await item_card_async(x) if x else "Not Found"

    (
        avatar_display,
        banner_display,
        pin_display,
        title_display,
        pet_display,
    ) = await asyncio.gather(
        _maybe_card(d["avatar_id"]),
        _maybe_card(d["banner_id"]),
        _maybe_card(d.get("pin_id", "")),
        _maybe_card(d.get("title", "")),
        _maybe_card(d.get("pet_id", "")),
    )
    pet_type_display = pet_display

    # ── Weapon cards (async, up to 2) ────────────────────────
    if d["weapons"]:
        wcards = await asyncio.gather(*[item_card_async(w) for w in d["weapons"][:2]])
        weapon_display = "\n".join(f"  {PE['weapon']} {c}" for c in wcards)
    else:
        weapon_display = "Not Found"

    # ── Language / rank ──────────────────────────────────────
    lang_display      = language_name(d["language"])
    show_rank_display = rank_show_name(d.get("rank_show", ""))
    honor_display     = val(d["credit"], "100")
    show_br           = str(d["show_br"]).capitalize() if d["show_br"] != "" else "True"
    show_cs           = str(d["show_cs"]).capitalize() if d["show_cs"] != "" else "True"

    # ══ BUILD PARTS ══
    parts = []

    # HEADER
    parts.append(
        f"<blockquote>"
        f"{e['fire']} <b>SIAM CODEX</b> {e['fire']}\n"
        f"{e['diamond']} <b>Free Fire Player Info</b> {e['diamond']}"
        f"</blockquote>"
    )

    # BASIC INFORMATION
    basic_rows = [
        row(e["star"],   "Prime Level",      val(d.get("prime_level", "1"), "1")),
        row(e["name"],   "Name",             d["name"]),
        row(e["id"],     "UID",              d["uid"]),
        row(e["level"],  "Level",            f"{val(d['level'])} (Exp: {int(d['exp']):,})" if d["exp"] else val(d["level"])),
        row(flag,        "Region",           val(d["region"])),
        row(e["likes"],  "Likes",            f"{int(d['liked']):,}" if d["liked"] else "0"),
        row(e["credit"], "Honor Score",      honor_display),
        row(e["check"],  "Celebrity Status", "False"),
        f"  {e['crown']} <b>Title Name:</b>\n    {title_display.replace(chr(10), chr(10)+'    ')}",
        row(e["sig"],    "Signature",        val(d["signature"], "Not Found")),
    ]
    parts.append(section(e["owner"], "Basic Information:", basic_rows))

    # ACTIVITY INFORMATION
    activity_rows = [
        row("📡",         "Most Recent OB",    val(d["release_ver"], "Not Found")),
        row(e["bp"],      "Booyah Pass",       bp_type(d["acc_type"])),
        row(e["credit"],  "Current Bp Badges", val(d["bp_badges"], "0")),
        row(e["trophy"],  "Br Rank",           br_rank_name(d["br_rank"])),
        row(e["sword"],   "Cs Rank",           cs_rank_name(d["cs_rank"])),
        row("⚧️",         "Gender",            "Confidential"),
        row(e["show"],    "Show Rank",         show_rank_display),
        row(e["check"],   "Show Br Rank",      show_br),
        row(e["check"],   "Show Cs Rank",      show_cs),
        row(e["date"],    "Created At",        ts(d["create_at"])),
        row(e["login"],   "Last Login",        ts(d["last_login"])),
    ]
    parts.append(section(e["rank"], "Activity Information:", activity_rows))

    # OVERVIEW INFORMATION — item cards rendered as multi-line blocks
    def _card_block(lbl_icon, lbl, card_str):
        """Wrap a pre-rendered item card under a section label."""
        return f"  {lbl_icon} <b>{lbl}:</b>\n    {card_str.replace(chr(10), chr(10)+'    ')}"

    overview_rows = [
        _card_block(e["avatar"], "Avatar",  avatar_display),
        _card_block(e["banner"], "Banner",  banner_display),
        _card_block(e["pin"],    "Pin",     pin_display),
        row("🕰️",       "Active Time",          "Flexible"),
        row("📆",       "Active Days",          "Flexible"),
        row(e["map"],   "Mode Prefer",          "No Preference"),
        row(e["skill"], "Equipped Skills",      skill_display),
        row(e["lang"],  "Language",             lang_display),
        row("🃏",       "Equipped Battle Card", "Not Equipped"),
        f"  {e['weapon']} <b>Equipped Guns:</b>\n{weapon_display}",
        row("🎬",       "Equipped Animation",   "Not Found"),
        row("🔄",       "Transform Animation",  "Not Found"),
        row(e["outfit"],"Outfits",              "Graphically Presented Below"),
    ]
    parts.append(section(e["info"], "Overview Information:", overview_rows))

    # PET DETAILS
    if d["pet_id"] and d["pet_is_used"]:
        pet_rows = [
            row(e["check"],  "Equipped?",  "Yes"),
            f"  🐣 <b>Pet Info:</b>\n    {pet_display.replace(chr(10), chr(10)+'    ')}",
            row(e["exp"],    "Pet Exp",    val(d["pet_exp"], "0")),
            row(e["level"],  "Pet Level",  val(d["pet_lv"],  "0")),
        ]
    else:
        pet_rows = [
            row("❌",        "Equipped?",  "No"),
            row("🐣",        "Pet Info",   "Not Found"),
            row(e["exp"],    "Pet Exp",    "Not Found"),
            row(e["level"],  "Pet Level",  "Not Found"),
        ]
    parts.append(section(e["pet"], "Pet Details:", pet_rows))

    # GUILD INFORMATION
    if d["guild_name"]:
        leader_uid = d["guild_own"]
        if leader_raw:
            lai     = leader_raw.get("AccountInfo", {}) or {}
            lcredit = (leader_raw.get("creditScoreInfo", {}) or {})
            lsocial = (leader_raw.get("socialinfo", {}) or {})
            leader_name      = lai.get("AccountName", "Not Found")
            leader_level     = lai.get("AccountLevel", "")
            leader_exp       = lai.get("AccountEXP", "")
            leader_region    = lai.get("AccountRegion", "Not Found")
            leader_bp        = bp_type(lai.get("AccountType", ""))
            leader_created   = ts(lai.get("AccountCreateTime", ""))
            leader_login     = ts(lai.get("AccountLastLogin", ""))
            leader_ob        = val(lai.get("ReleaseVersion", ""), "Not Found")
            leader_title_id  = lai.get("Title", "")
            leader_title     = await item_card_async(leader_title_id) if leader_title_id else "Not Found"
            leader_bp_badges = val(lai.get("AccountBPBadges", ""), "Not Found")
            leader_br        = br_rank_name(lai.get("BrRankPoint", ""))
            leader_cs        = cs_rank_name(lai.get("CsRankPoint", ""))
            leader_level_str = f"{leader_level} (Exp: {int(leader_exp):,})" if leader_exp else str(leader_level)
            leader_flag      = flags.get(str(leader_region).upper(), "🌍")
        else:
            leader_name = leader_level_str = leader_region = "Not Found"
            leader_bp = leader_created = leader_login = "Not Found"
            leader_ob = leader_title = leader_bp_badges = "Not Found"
            leader_br = leader_cs = "Not Found"
            leader_flag = "🌍"

        guild_rows = [
            row(e["guild"],   "Guild Name",    d["guild_name"]),
            row(e["id"],      "Guild ID",      val(d["guild_id"])),
            row(e["star"],    "Guild Level",   val(d["guild_lv"])),
            row(e["member"],  "Live Members",  f"{val(d['guild_mem'])}/{val(d['guild_cap'])}"),
            f"  {e['crown']} <b>Leader Information:</b>",
            row("    " + e["owner"],  "Leader Name",             leader_name),
            row("    " + e["id"],     "Leader UID",              leader_uid),
            row("    " + e["level"],  "Leader Level",            leader_level_str),
            row("    " + leader_flag, "Leader Region",           leader_region),
            row("    " + e["bp"],     "Leader Booyah Pass",      leader_bp),
            row("    " + e["date"],   "Leader Created At",       leader_created),
            row("    " + e["login"],  "Leader Last Login",       leader_login),
            row("    📡",             "Leader Most Recent OB",   leader_ob),
            f"    {e['crown']} <b>Leader Title:</b>\n      {leader_title.replace(chr(10), chr(10)+'      ')}",
            row("    " + e["credit"], "Leader Current Bp Badges",leader_bp_badges),
            row("    " + e["trophy"], "Leader Br Rank",          leader_br),
            row("    " + e["sword"],  "Leader Cs Rank",          leader_cs),
        ]
    else:
        guild_rows = [
            row("➖", "Guild Name",    "Not Found"),
            row("➖", "Guild ID",      "Not Found"),
            row("➖", "Guild Level",   "Not Found"),
            row("➖", "Live Members",  "Not Found"),
            f"  {e['crown']} <b>Leader Information:</b>",
        ] + [row("    ➖", lbl, "Not Found") for lbl in [
            "Leader Name", "Leader UID", "Leader Level", "Leader Region",
            "Leader Booyah Pass", "Leader Created At", "Leader Last Login",
            "Leader Most Recent OB", "Leader Title Name",
            "Leader Current Bp Badges", "Leader Br Rank", "Leader Cs Rank",
        ]]
    parts.append(section(e["shield"], "Guild Information:", guild_rows))

    # PUBLIC CRAFTLAND MAPS
    parts.append(
        "<blockquote>"
        "🗺️ <b>Public Craftland Maps</b>\n"
        "┌─────────────────────────\n"
        "  Not Found\n"
        "└─────────────────────────"
        "</blockquote>"
    )

    # FOOTER
    parts.append(
        f"<blockquote>"
        f"{e['fire']} <b>@SIAM_CODEX</b> {e['diamond']} <b>SIAM CODEX</b> {e['fire']}"
        f"</blockquote>"
    )

    return "\n\n".join(parts)

# ================================================================
# SENDING HELPERS
# ================================================================
async def send_typing(update, context):
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.UPLOAD_PHOTO
    )

async def send_error(update, msg):
    await update.message.reply_text(
        f"{PE['error']} <b>Error:</b> <code>{msg}</code>",
        parse_mode=ParseMode.HTML
    )

def parse_uid(args, text, command):
    if args:
        return args[0].strip()
    parts = text.strip().split()
    if len(parts) >= 2:
        return parts[1].strip()
    return None

# ================================================================
# COMMAND HANDLERS
# ================================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    e = PE
    txt = (
        f"{e['fire']} <b>SIAM CODEX — Free Fire Info Bot</b> {e['fire']}\n\n"
        f"{e['diamond']} <b>Commands:</b>\n\n"
        f"{e['info']} <code>/info &lt;UID&gt;</code> — Full player info\n"
        f"{e['info']} <code>/get &lt;UID&gt;</code> — Same as /info\n"
        f"{e['avatar']} <code>/banner &lt;UID&gt;</code> — Profile banner image\n"
        f"{e['outfit']} <code>/outfit &lt;UID&gt;</code> — Equipped outfit image\n"
        f"{e['level']} <code>/level &lt;UID&gt;</code> — Player name &amp; level\n"
        f"{e['region']} <code>/region &lt;UID&gt;</code> — Player name &amp; region\n\n"
        f"{e['check']} <b>Example:</b> <code>/info 2916914087</code>\n\n"
        f"{e['diamond']} <b>By:</b> @SIAM_CODEX"
    )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

# ── /info or /get ──────────────────────────────────────────────
async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = parse_uid(context.args, update.message.text,
                    update.message.text.split()[0])
    if not uid or not uid.isdigit():
        await update.message.reply_text(
            f"{PE['warn']} <b>Usage:</b> <code>/info 2916914087</code>",
            parse_mode=ParseMode.HTML
        )
        return

    await send_typing(update, context)
    wait_msg = await update.message.reply_text(
        f"{PE['wait']} Fetching player data... Please wait.",
        parse_mode=ParseMode.HTML
    )

    try:
        raw = await fetch_player_raw(uid)
        if not raw:
            await wait_msg.delete()
            await send_error(update, "Player not found or UID invalid.")
            return

        d = fmt(raw)

        leader_raw = None
        leader_uid = d.get("guild_own", "")
        if leader_uid and leader_uid not in ("", "0", "None"):
            leader_raw = await fetch_leader_raw(leader_uid)

        banner_io, outfit_io = await asyncio.gather(
            make_banner(raw),
            make_outfit(raw)
        )
        caption = await build_full_caption(d, leader_raw=leader_raw)

        # UID fallback
        uid_display = d["uid"]
        if uid_display in ("N/A","","None"):
            _ai0 = raw.get("AccountInfo",{}) or {}
            for _k in ("accountId","accountId","Uid","uid","playerUID","account_id"):
                _v = str(_ai0.get(_k) or "")
                if _v and _v not in ("0","None","null",""):
                    uid_display = _v; break

        # Full item info blocks for banner photo caption
        av_info_i, bn_info_i = await asyncio.gather(
            item_info(d["avatar_id"]),
            item_info(d["banner_id"]),
        )

        def _iblock(lbl_icon, lbl, info, raw_id):
            nm  = info.get("name",  str(raw_id)) if info else str(raw_id)
            it  = info.get("type",  "")           if info else ""
            ra  = str(info.get("Rare","")).upper() if info else ""
            de  = info.get("description","")       if info else ""
            tg  = info.get("tag","")               if info else ""
            ii  = str(info.get("itemID", raw_id)  if info else raw_id)
            ri  = RARE_EMOJI.get(ra,"")
            rl  = RARE_LABEL.get(ra, ra.capitalize() if ra else "")
            lns = [f"{lbl_icon} <b>{lbl}</b>"]
            lns.append(f"  🏷 <b>Name:</b> <code>{nm}</code>")
            lns.append(f"  🆔 <b>Item ID:</b> <code>#{ii}</code>")
            if it: lns.append(f"  🔖 <b>Type:</b> <code>{it}</code>")
            if rl: lns.append(f"  {ri} <b>Rarity:</b> <code>{rl}</code>")
            if tg: lns.append(f"  🗓 <b>Tag:</b> <code>{tg}</code>")
            if de:
                d2 = de if len(de)<=120 else de[:117]+"..."
                lns.append(f"  📝 <b>Desc:</b> {d2}")
            return "\n".join(lns)

        av_blk = _iblock(PE["avatar"], "Avatar",  av_info_i, d["avatar_id"])
        bn_blk = _iblock(PE["banner"], "Banner", bn_info_i, d["banner_id"])

        # Full item info blocks for outfit photo caption
        outfit_ids_i = d["outfit"][:9]
        if outfit_ids_i:
            outfit_infos_i = await asyncio.gather(*[item_info(i) for i in outfit_ids_i])
            slot_blocks_i = []
            for _s, (_oid, _oinf) in enumerate(zip(outfit_ids_i, outfit_infos_i), 1):
                _nm  = _oinf.get("name",  str(_oid)) if _oinf else str(_oid)
                _it  = _oinf.get("type",  "")         if _oinf else ""
                _ra  = str(_oinf.get("Rare","")).upper() if _oinf else ""
                _de  = _oinf.get("description","")    if _oinf else ""
                _tg  = _oinf.get("tag","")             if _oinf else ""
                _ii  = str(_oinf.get("itemID",_oid)  if _oinf else _oid)
                _ri  = RARE_EMOJI.get(_ra,"")
                _rl  = RARE_LABEL.get(_ra, _ra.capitalize() if _ra else "")
                _blk = [f"{PE['outfit']} <b>Slot {_s}</b>"]
                _blk.append(f"  🏷 <b>Name:</b> <code>{_nm}</code>")
                _blk.append(f"  🆔 <b>Item ID:</b> <code>#{_ii}</code>")
                if _it: _blk.append(f"  🔖 <b>Type:</b> <code>{_it}</code>")
                if _rl: _blk.append(f"  {_ri} <b>Rarity:</b> <code>{_rl}</code>")
                if _tg: _blk.append(f"  🗓 <b>Tag:</b> <code>{_tg}</code>")
                if _de:
                    _d2 = _de if len(_de)<=100 else _de[:97]+"..."
                    _blk.append(f"  📝 <b>Desc:</b> {_d2}")
                slot_blocks_i.append("\n".join(_blk))
            outfit_section_i = "\n─────────────\n".join(slot_blocks_i)
        else:
            outfit_section_i = f"  {PE['outfit']} None"

        await update.message.reply_photo(
            photo=banner_io.getvalue(),
            caption=(
                f"<blockquote>{PE['avatar']} <b>Banner Card</b> {PE['fire']}\n"
                f"┌─────────────────────────\n"
                f"{PE['owner']} <b>Name:</b> <code>{d['name']}</code>\n"
                f"{PE['id']} <b>UID:</b> <code>{uid_display}</code>\n"
                f"{PE['level']} <b>Level:</b> <code>{d['level']}</code>\n"
                f"{PE['region']} <b>Region:</b> <code>{d['region']}</code>\n"
                f"─────────────────────────\n"
                f"{av_blk}\n"
                f"─────────────────────────\n"
                f"{bn_blk}\n"
                f"└─────────────────────────\n"
                f"{PE['diamond']} <b>TG: @SIAM_CODEX</b></blockquote>"
            ),
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_photo(
            photo=outfit_io.getvalue(),
            caption=(
                f"<blockquote>{PE['outfit']} <b>Outfit Card</b> {PE['fire']}\n"
                f"┌─────────────────────────\n"
                f"{PE['owner']} <b>Name:</b> <code>{d['name']}</code>\n"
                f"{PE['id']} <b>UID:</b> <code>{uid_display}</code>\n"
                f"─────────────────────────\n"
                f"{outfit_section_i}\n"
                f"└─────────────────────────\n"
                f"{PE['diamond']} <b>TG: @SIAM_CODEX</b></blockquote>"
            ),
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_text(caption, parse_mode=ParseMode.HTML)
        await wait_msg.delete()

    except Exception as e:
        logger.error(f"cmd_info error: {e}")
        await wait_msg.delete()
        await send_error(update, str(e))

# ── /banner ────────────────────────────────────────────────────
async def cmd_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = parse_uid(context.args, update.message.text,
                    update.message.text.split()[0])
    if not uid or not uid.isdigit():
        await update.message.reply_text(
            f"{PE['warn']} <b>Usage:</b> <code>/banner 2916914087</code>",
            parse_mode=ParseMode.HTML
        )
        return

    await send_typing(update, context)
    wait_msg = await update.message.reply_text(
        f"{PE['wait']} Generating banner...",
        parse_mode=ParseMode.HTML
    )

    try:
        raw = await fetch_player_raw(uid)
        if not raw:
            await wait_msg.delete()
            await send_error(update, "Player not found.")
            return

        d = fmt(raw)
        banner_io = await make_banner(raw)

        # Full item info for avatar + banner
        av_info, bn_info = await asyncio.gather(
            item_info(d["avatar_id"]),
            item_info(d["banner_id"]),
        )

        def _field_block(label_icon, label, info, raw_id):
            """Render one item as multi-line block."""
            name  = info.get("name", raw_id)  if info else raw_id
            itype = info.get("type", "")       if info else ""
            rare  = str(info.get("Rare","")).upper() if info else ""
            desc  = info.get("description","") if info else ""
            tag   = info.get("tag","")         if info else ""
            iid   = str(info.get("itemID", raw_id) if info else raw_id)
            rare_icon  = RARE_EMOJI.get(rare, "")
            rare_label = RARE_LABEL.get(rare, rare.capitalize() if rare else "")
            lines = [f"{label_icon} <b>{label}</b>"]
            lines.append(f"  🏷 <b>Name:</b> <code>{name}</code>")
            lines.append(f"  🆔 <b>Item ID:</b> <code>#{iid}</code>")
            if itype:  lines.append(f"  🔖 <b>Type:</b> <code>{itype}</code>")
            if rare_label: lines.append(f"  {rare_icon} <b>Rarity:</b> <code>{rare_label}</code>")
            if tag:    lines.append(f"  🗓 <b>Tag:</b> <code>{tag}</code>")
            if desc:
                d2 = desc if len(desc) <= 120 else desc[:117] + "..."
                lines.append(f"  📝 <b>Desc:</b> {d2}")
            return "\n".join(lines)

        av_block = _field_block(PE["avatar"], "Avatar", av_info, str(d["avatar_id"]))
        bn_block = _field_block(PE["banner"], "Banner", bn_info, str(d["banner_id"]))

        uid_show = d["uid"]
        if uid_show in ("N/A", "", "None"):
            _ai = raw.get("AccountInfo", {}) or {}
            for _k in ("accountId","accountId","Uid","uid","playerUID","account_id"):
                _v = str(_ai.get(_k) or "")
                if _v and _v not in ("0","None","null",""):
                    uid_show = _v; break

        await update.message.reply_photo(
            photo=banner_io.getvalue(),
            caption=(
                f"{PE['avatar']} <b>Player Banner</b> {PE['fire']}\n"
                f"┌─────────────────────────\n"
                f"{PE['owner']} <b>Name:</b> <code>{d['name']}</code>\n"
                f"{PE['id']} <b>UID:</b> <code>{uid_show}</code>\n"
                f"{PE['level']} <b>Level:</b> <code>{d['level']}</code>\n"
                f"{PE['region']} <b>Region:</b> <code>{d['region']}</code>\n"
                f"─────────────────────────\n"
                f"{av_block}\n"
                f"─────────────────────────\n"
                f"{bn_block}\n"
                f"└─────────────────────────\n"
                f"{PE['diamond']} <b>TG: @SIAM_CODEX</b>"
            ),
            parse_mode=ParseMode.HTML
        )
        await wait_msg.delete()

    except Exception as e:
        logger.error(f"cmd_banner error: {e}")
        await wait_msg.delete()
        await send_error(update, str(e))

# ── /outfit ────────────────────────────────────────────────────
async def cmd_outfit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = parse_uid(context.args, update.message.text,
                    update.message.text.split()[0])
    if not uid or not uid.isdigit():
        await update.message.reply_text(
            f"{PE['warn']} <b>Usage:</b> <code>/outfit 2916914087</code>",
            parse_mode=ParseMode.HTML
        )
        return

    await send_typing(update, context)
    wait_msg = await update.message.reply_text(
        f"{PE['wait']} Loading outfit...",
        parse_mode=ParseMode.HTML
    )

    try:
        raw = await fetch_player_raw(uid)
        if not raw:
            await wait_msg.delete()
            await send_error(update, "Player not found.")
            return

        d = fmt(raw)
        outfit_io = await make_outfit(raw)

        # Resolve outfit item cards — full info per slot
        outfit_ids = d["outfit"][:9]
        outfit_uid = d["uid"]
        if outfit_uid in ("N/A","","None"):
            _ai2 = raw.get("AccountInfo",{}) or {}
            for _k in ("accountId","accountId","Uid","uid","playerUID","account_id"):
                _v = str(_ai2.get(_k) or "")
                if _v and _v not in ("0","None","null",""):
                    outfit_uid = _v; break

        if outfit_ids:
            outfit_infos = await asyncio.gather(*[item_info(i) for i in outfit_ids])
            slot_blocks = []
            for idx2, (oid, oinfo) in enumerate(zip(outfit_ids, outfit_infos), 1):
                oname  = oinfo.get("name",  str(oid))  if oinfo else str(oid)
                otype  = oinfo.get("type",  "")         if oinfo else ""
                orare  = str(oinfo.get("Rare","")).upper() if oinfo else ""
                odesc  = oinfo.get("description","")    if oinfo else ""
                otag   = oinfo.get("tag","")             if oinfo else ""
                oiid   = str(oinfo.get("itemID", oid)   if oinfo else oid)
                orare_icon  = RARE_EMOJI.get(orare,"")
                orare_label = RARE_LABEL.get(orare, orare.capitalize() if orare else "")
                block = [f"{PE['outfit']} <b>Slot {idx2}</b>"]
                block.append(f"  🏷 <b>Name:</b> <code>{oname}</code>")
                block.append(f"  🆔 <b>Item ID:</b> <code>#{oiid}</code>")
                if otype:       block.append(f"  🔖 <b>Type:</b> <code>{otype}</code>")
                if orare_label: block.append(f"  {orare_icon} <b>Rarity:</b> <code>{orare_label}</code>")
                if otag:        block.append(f"  🗓 <b>Tag:</b> <code>{otag}</code>")
                if odesc:
                    od2 = odesc if len(odesc)<=100 else odesc[:97]+"..."
                    block.append(f"  📝 <b>Desc:</b> {od2}")
                slot_blocks.append("\n".join(block))
            outfit_section = "\n─────────────\n".join(slot_blocks)
        else:
            outfit_section = f"  {PE['outfit']} None"

        await update.message.reply_photo(
            photo=outfit_io.getvalue(),
            caption=(
                f"<blockquote>{PE['outfit']} <b>Equipped Outfit</b> {PE['fire']}\n"
                f"┌─────────────────────────\n"
                f"{PE['owner']} <b>Name:</b> <code>{d['name']}</code>\n"
                f"{PE['id']} <b>UID:</b> <code>{outfit_uid}</code>\n"
                f"{PE['level']} <b>Level:</b> <code>{d['level']}</code>\n"
                f"{PE['region']} <b>Region:</b> <code>{d['region']}</code>\n"
                f"─────────────────────────\n"
                f"{outfit_section}\n"
                f"└─────────────────────────\n"
                f"{PE['diamond']} <b>TG: @SIAM_CODEX</b></blockquote>"
            ),
            parse_mode=ParseMode.HTML
        )
        await wait_msg.delete()

    except Exception as e:
        logger.error(f"cmd_outfit error: {e}")
        await wait_msg.delete()
        await send_error(update, str(e))

# ── /level ─────────────────────────────────────────────────────
async def cmd_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = parse_uid(context.args, update.message.text,
                    update.message.text.split()[0])
    if not uid or not uid.isdigit():
        await update.message.reply_text(
            f"{PE['warn']} <b>Usage:</b> <code>/level 2916914087</code>",
            parse_mode=ParseMode.HTML
        )
        return

    await send_typing(update, context)
    wait_msg = await update.message.reply_text(
        f"{PE['wait']} Fetching level info...",
        parse_mode=ParseMode.HTML
    )

    try:
        raw = await fetch_player_raw(uid)
        if not raw:
            await wait_msg.delete()
            await send_error(update, "Player not found.")
            return

        d = fmt(raw)
        title_display = await item_card_async(d["title"]) if d.get("title") else "Not Found"

        await update.message.reply_text(
            f"{PE['level']} <b>Level Info</b> {PE['fire']}\n"
            f"┌─────────────────────────\n"
            f"{PE['owner']} <b>Name:</b> <code>{d['name']}</code>\n"
            f"{PE['id']} <b>UID:</b> <code>{d['uid']}</code>\n"
            f"{PE['level']} <b>Level:</b> <code>{d['level']}</code>\n"
            f"{PE['exp']} <b>EXP:</b> <code>{int(d['exp']):,}</code>\n"
            f"{PE['trophy']} <b>Br Rank:</b> <code>{br_rank_name(d['br_rank'])}</code>\n"
            f"{PE['sword']} <b>Cs Rank:</b> <code>{cs_rank_name(d['cs_rank'])}</code>\n"
            f"{PE['crown']} <b>Title:</b> {title_display}\n"
            f"└─────────────────────────\n"
            f"{PE['diamond']} <b>TG: @SIAM_CODEX</b>",
            parse_mode=ParseMode.HTML
        )
        await wait_msg.delete()

    except Exception as e:
        logger.error(f"cmd_level error: {e}")
        await wait_msg.delete()
        await send_error(update, str(e))

# ── /region ────────────────────────────────────────────────────
async def cmd_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = parse_uid(context.args, update.message.text,
                    update.message.text.split()[0])
    if not uid or not uid.isdigit():
        await update.message.reply_text(
            f"{PE['warn']} <b>Usage:</b> <code>/region 2916914087</code>",
            parse_mode=ParseMode.HTML
        )
        return

    await send_typing(update, context)
    wait_msg = await update.message.reply_text(
        f"{PE['wait']} Fetching region info...",
        parse_mode=ParseMode.HTML
    )

    try:
        raw = await fetch_player_raw(uid)
        if not raw:
            await wait_msg.delete()
            await send_error(update, "Player not found.")
            return

        d = fmt(raw)
        region_flags = {
            "BD": "🇧🇩", "IND": "🇮🇳", "ME": "🇸🇦",
            "ID": "🇮🇩", "TH": "🇹🇭", "BR": "🇧🇷",
            "VN": "🇻🇳", "SG": "🇸🇬", "MY": "🇲🇾",
            "PK": "🇵🇰", "NA": "🇺🇸", "TW": "🇹🇼",
        }
        flag = region_flags.get(d["region"], "🌍")

        await update.message.reply_text(
            f"{PE['region']} <b>Region Info</b> {PE['fire']}\n"
            f"┌─────────────────────────\n"
            f"{PE['owner']} <b>Name:</b> <code>{d['name']}</code>\n"
            f"{PE['id']} <b>UID:</b> <code>{d['uid']}</code>\n"
            f"{flag} <b>Region:</b> <code>{d['region']}</code>\n"
            f"{PE['level']} <b>Level:</b> <code>{d['level']}</code>\n"
            f"{PE['exp']} <b>EXP:</b> <code>{int(d['exp']):,}</code>\n"
            f"{PE['likes']} <b>Likes:</b> <code>{int(d['liked']):,}</code>\n"
            f"└─────────────────────────\n"
            f"{PE['diamond']} <b>TG: @SIAM_CODEX</b>",
            parse_mode=ParseMode.HTML
        )
        await wait_msg.delete()

    except Exception as e:
        logger.error(f"cmd_region error: {e}")
        await wait_msg.delete()
        await send_error(update, str(e))

# ── Plain UID ──────────────────────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.isdigit() and len(text) >= 8:
        context.args = [text]
        await cmd_info(update, context)

# ================================================================
# MAIN
# ================================================================
def main():
    # Load item DB before polling starts
    load_item_db()

    print(f"{PE['fire']} Starting SIAM CODEX Info Bot...")
    print("📋 Commands: /info /get /banner /outfit /level /region")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("info",   cmd_info))
    app.add_handler(CommandHandler("get",    cmd_info))
    app.add_handler(CommandHandler("banner", cmd_banner))
    app.add_handler(CommandHandler("outfit", cmd_outfit))
    app.add_handler(CommandHandler("level",  cmd_level))
    app.add_handler(CommandHandler("region", cmd_region))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print(f"{PE['check']} Bot is running! Press Ctrl+C to stop.\n")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
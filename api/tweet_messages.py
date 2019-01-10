import random
import emoji

messages = {
    'entry': [
        "",
        "いくよー",
        "むむっ",
        "とうっっ",
        "はー！",
        "おりゃっ"
    ],
    'take_profit': [
        "",
        "わーい",
        "やたー",
        "いぇい",
        "ほほう",
        "ふふーん",
        "へいへいー",
        "ﾌﾝﾌﾝ"
    ],
    'losscut': [
        "",
        "むーん",
        "ぽよー",
        "にゃー",
        "きゃー",
        "はわー",
        "ぐへっ"
    ]
}

kaomojis = {
    'positive': [
        "(。·ω·。)",
        "(*˘︶˘*).。.:*♡",
        "₍₍ ( ๑॔˃̶◡ ˂̶๑॓)◞♡",
        "（*'∀'人）♥*+",
        "(*•̀ᴗ•́*)و ̑̑",
        "(*´╰╯`๓)♬",
        "(*´ω｀*)",
        "(*∩ω∩)",
        "(＊◕ᴗ◕＊)",
        "(≧▽≦)",
        "(≧ω≦)",
        "(⋈◍＞◡＜◍)。✧♡",
        "(▰╹◡╹▰)",
        "(❁´ω`❁)",
        "(✖╹◡╹✖)◞",
        "(✿´꒳`)ﾉ°+.*",
        "(๑ ́ᄇ`๑)",
        "(๑ˇεˇ๑)•*¨*•.¸¸♪",
        "(๑ゝω╹๑)",
        "(๑ơ ₃ ơ)♥",
        "(o^∀^o)",
        "(っ*´∀｀*)っ",
        "*ଘ(੭*◕ฺω◕ฺ)੭*ੈ",
        "＼＼\(۶•̀ᴗ•́)۶//／／",
        "❤(。☌ᴗ☌｡)",
        "꒰◍ᐡᐤᐡ◍꒱",
        "꒰๑•௰•๑꒱",
        "ヽ(。·ω·。)ﾉ",
        "٩( ๑╹ ꇴ╹)۶",
        "٩꒰｡•◡•。꒱۶'",
        "ଘ(੭ˊ꒳​ˋ)੭✧",
        "ฅ(♡ơ ₃ơ)ฅ"
    ],
    'negative': [
        "('﹏*๑)",
        "(。ì _ í。)",
        "_(┐「ε:)_",
        "(´-ω-`)",
        "(๑•́ ₃ •̀๑)",
        "( ᵒ̴̶̷̥́ _ᵒ̴̶̷̣̥̀ )",
        "(๑ó⌓ò๑)",
        "(ﾉ*'ω'*)ﾉ彡┻━┻",
        "‧⁺◟( ᵒ̴̶̷̥́ ·̫ ᵒ̴̶̷̣̥̀ )",
        "ฅ(๑*д*๑)ฅ!!",
        "(´×ω×`)",
        "(´·×·`)",
        "(ó﹏ò。)",
        "(´+ω+｀)",
        "(๑ò︵ò๑)",
        "(๑ŏ _ ŏ๑)",
        "( ˃̣̣̥ω˂̣̣̥ )"
    ],
    'neutral': [
        "(๑•﹏•)",
        "(*·～·*)",
        "( ๑´•ω•)۶”",
        "(∂ω∂)",
        "(´ฅω•ฅ｀)",
        "(๑·㉨·๑)",
        "─=≡Σ((( つ•̀ω•́)つ",
        "⊂( *·ω· )⊃",
        "c(·ω·`c⌒っ",
        "·*·:≡( ε:)",
        "(#˘ω˘#)",
        "(˘ω˘ ≡ ˘ω˘)",
        "(。-ω-)zzz",
        "( ˘ω˘ )つ",
        "(๑ơ ₃ ơ)♥"
    ]
}

emojis = {
    'positive': [
        ':exclamation:',
        ':sparkles:',
        ':blush:',
        ':relaxed:',
        ':sunglasses:',
        ':smirk:',
        ':boom:',
        ':muscle:',
        ':sunny:',
        ':v:',
        ':clap:',
        ':star:',
        ':yum:',
        ':grin:',
        ':satisfied:',
        ':star2:',
        ':raised_hands:',
        ':sparkling_heart:',
        ':triumph:',
        ':heart_eyes:',
        ':kissing:',
        ':kissing_heart:',
        ':kissing_closed_eyes:'
    ],
    'negative': [
        ':sweat_smile:',
        ':cry:',
        ':astonished:',
        ':tired_face:',
        ':fire:',
        ':sweat_drops:',
        ':mask:',
        ':confounded:',
        ':disappointed:',
        ':sweat:',
        ':pensive:',
        ':scream:',
        ':angry:',
        ':umbrella:',
        ':broken_heart:',
        ':frowning:',
        ':persevere:',
        ':dizzy_face:'
    ],
    'neutral': [
        ':zzz:',
        ':runner:',
        ':dancers:',
        ':raising_hand:',
        ':bow:',
        ':hand:',
        ':dash:',
        ':dizzy:',
        ':sleeping:',
        ':grimacing:',
        ':sleepy:',
        ':facepunch:',
        ':smirk_cat:',
        ':rabbit:',
        ':hamster:',
        ':mouse:',
        ':dog:',
        ':zap:',
        ':boom:',
        ':exclamation:',
        ':wave:',
        ':eyes:'
    ]
}

scal = {
    'win': [
        '勝った〜',
        'ふえた',
        'とれた'
    ],
    'lose': [
        'まけた',
        'とけた',
        'なくなった'
    ]
}
def get_kaomoji(feeling):
    return random.choice(kaomojis[feeling])

def get_message(action):
    return random.choice(messages[action])

def get_emoji(feeling):
    emoji_str = random.choice(emojis[feeling])
    return emoji.emojize(emoji_str, use_aliases=True)

def get_scal_tweet(side):
    line1 = 'スキャルピングしてたら'
    return line1, random.choice(scal[side])

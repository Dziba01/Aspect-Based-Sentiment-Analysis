"""
Offline fallback sentiment scorer for Shona + Ndebele.
Used ONLY when Google Translate is unavailable (rate-limited / offline).
"""

POSITIVE = [
    # ---- Shona ----
    'zvikuru', 'zvakanaka', 'rakanaka', 'yakanaka', 'akanaka', 'vakanaka',
    'kunaka', 'mushe', 'ndinotenda', 'ndatenda', 'tinotenda', 'tinokutenda',
    'kutenda', 'kufara', 'ndinofara', 'tinofara', 'nakidzwa', 'ndakanakidzwa',
    'kugamuchirwa', 'kugamuchira', 'rudo', 'hanya', 'kunzwisisa', 'kubatsira',
    'chinonaka', 'zvinonaka', 'inonaka', 'rinonaka', 'kunonaka',
    # ---- Ndebele ----
    'ngiyabonga', 'siyabonga', 'ngiyakuthanda', 'siyakuthanda', 'ngiyajabula',
    'sijabula', 'jabulisa', 'umnandi', 'kumnandi', 'mnandi', 'kuhle', 'enhle',
    'okuhle', 'ezinhle', 'abahle', 'omuhle', 'ngiyancoma', 'siyancoma',
    'kakhulu', 'inkonzo enhle', 'abasebenzi abahle', 'bayakwamukela',
    'engayithola', 'ngayithola',
]

NEGATIVE = [
    # ---- Shona ----
    'zvakashata', 'zvakaipa', 'akashata', 'akaipa', 'vakashata', 'vakaipa',
    'rakaipa', 'rakashata', 'yakaipa', 'yakashata', 'kwakaipa', 'kwakashata',
    'kushata', 'huipi', 'kubi', 'kabi', 'hazvina kunaka', 'haina kunaka',
    'harina kunaka', 'haana kunaka', 'handifari', 'handina kufara',
    'ndakaodzwa', 'odzwa moyo', 'kusafara', 'kurwadziwa',
    'ndakarwadziwa', 'kurwara', 'ndinorwara',
    'chinoshata', 'zvinoshata', 'inoshata', 'rinoshata',
    # ---- Ndebele ----
    'imbi', 'zimbi', 'kubi', 'kabi', 'akukuhle', 'akukahle', 'akulungile',
    'akulunganga', 'angijabule', 'angijabulanga', 'angikuthandi',
    'angikuthandanga', 'angigculisekanga', 'akumnandi', 'akumnandanga',
    'inkonzo imbi', 'inkonzo embi', 'ngidangele', 'ngicasukile', 'ngidiniwe',
    'angitholanga', 'akukho', 'angiphumelelanga',
]


def score(text: str):
    if not text:
        return 'neutral', 0.0

    t = text.lower()
    pos = sum(1 for w in POSITIVE if w in t)
    neg = sum(1 for w in NEGATIVE if w in t)

    if pos == 0 and neg == 0:
        return 'neutral', 0.0

    confidence = min(0.4 + 0.15 * (pos + neg), 0.85)

    if pos > neg:
        return 'positive', round(confidence, 2)
    if neg > pos:
        return 'negative', round(confidence, 2)
    return 'neutral', round(confidence * 0.5, 2)
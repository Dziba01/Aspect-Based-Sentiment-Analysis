import re


class LanguageDetector:
    """Detect Shona / Ndebele / English.

    Strategy: default to Shona/Ndebele unless the text clearly looks English.
    Because the sentiment model is English, we want to translate aggressively.
    """

    # Very common English words (must match a decent fraction to call English)
    ENGLISH_WORDS = {
        'the', 'and', 'was', 'were', 'is', 'are', 'am', 'be', 'been',
        'a', 'an', 'of', 'to', 'in', 'on', 'at', 'for', 'with', 'by',
        'this', 'that', 'these', 'those', 'it', 'its', 'as', 'or', 'but',
        'not', 'no', 'yes', 'very', 'so', 'too', 'also', 'just', 'only',
        'my', 'your', 'his', 'her', 'our', 'their', 'we', 'they', 'you',
        'i', 'he', 'she', 'them', 'us', 'me', 'him',
        'good', 'bad', 'great', 'poor', 'excellent', 'terrible', 'nice',
        'food', 'room', 'staff', 'service', 'clean', 'dirty', 'hotel',
        'stay', 'night', 'breakfast', 'dinner', 'lunch', 'bed', 'bathroom',
        'helpful', 'friendly', 'rude', 'comfortable', 'amazing', 'awful',
        'loved', 'hated', 'recommend', 'disappointed', 'enjoyed',
    }

    # Strong language fingerprints (substrings that almost never occur in English)
    SHONA_FINGERPRINTS = [
        'zvikuru', 'zvaka', 'zvino', 'zviri', 'ndaka', 'ndino', 'ndinoda',
        'ndinotenda', 'kutenda', 'rakanaka', 'yakanaka', 'akanaka',
        'vakanaka', 'zvakanaka', 'panzvimbo', 'kubva', 'pandakapinda',
        'pandakabuda', 'kushata', 'kushandiswa', 'chikafu', 'kudya',
        'mushe', 'mhoro', 'maswera', 'makadini', 'nekuti', 'asi', 'uye',
        'imba', 'dumba', 'nzvimbo', 'vashandi', 'basa', 'imbwa',
    ]

    NDEBELE_FINGERPRINTS = [
        'ngiyabonga', 'ngiyakuthanda', 'ngiyajabula', 'ngifuna', 'ngenza',
        'kakhulu', 'enhle', 'enhle', 'kuhle', 'kuhle', 'abantu',
        'abantu', 'basebenzi', 'abassebenzi', 'engayithola', 'ngithe',
        'ngenza', 'kule', 'endaweni', 'udaba', 'izinto', 'ubuhle',
        'ngayivakashela', 'ngayithola', 'bazamile', 'bazamile',
        'ngibonga', 'ngibona', 'ngiyabona', 'besaba', 'manje',
        'lokhu', 'leyo', 'leyi', 'lolo', 'kubo', 'kubo',
    ]

    # Word prefixes that strongly indicate Bantu languages
    SHONA_PREFIXES = ('ndi', 'uri', 'ari', 'tiri', 'muri', 'vari',
                      'zvaka', 'zvino', 'ndaka', 'uno', 'ano', 'tino')

    NDEBELE_PREFIXES = ('ngi', 'uyi', 'uye', 'si', 'ni', 'ba',
                        'ku', 'kwa', 'nga', 'ngi', 'zi', 'lu')

    @classmethod
    def _score(cls, text_lower: str, fingerprints):
        score = 0
        for fp in fingerprints:
            if fp in text_lower:
                score += 2  # substring hit is strong
        return score

    @classmethod
    def detect(cls, text: str) -> str:
        if not text or not text.strip():
            return 'english'

        t = text.lower()
        words = re.findall(r"[a-zA-Z']+", t)

        # --- 1. Strong fingerprints (highest weight) ---
        shona_score = cls._score(t, cls.SHONA_FINGERPRINTS)
        ndebele_score = cls._score(t, cls.NDEBELE_FINGERPRINTS)

        # --- 2. Prefix hits ---
        for w in words:
            for p in cls.SHONA_PREFIXES:
                if w.startswith(p) and len(w) > len(p) + 1:
                    shona_score += 1
                    break
            for p in cls.NDEBELE_PREFIXES:
                if w.startswith(p) and len(w) > len(p) + 1:
                    ndebele_score += 0.6
                    break

        # --- 3. English signal ---
        eng_hits = sum(1 for w in words if w in cls.ENGLISH_WORDS)
        eng_ratio = eng_hits / max(len(words), 1)

        # --- 4. Decision ---
        # Any strong fingerprint immediately wins
        if ndebele_score >= 2 and ndebele_score > shona_score:
            return 'ndebele'
        if shona_score >= 2:
            return 'shona'

        # Require a solid English ratio to call it English
        if eng_ratio >= 0.4 and eng_hits >= 3:
            return 'english'

        # Default: if there is any African-language signal at all, prefer translation
        if shona_score > 0 and shona_score >= ndebele_score:
            return 'shona'
        if ndebele_score > 0:
            return 'ndebele'

        # Pure fallback
        return 'english'
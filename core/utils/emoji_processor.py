import emoji
import re
from typing import Dict, List, Tuple

class EmojiProcessor:
    """Process emojis in text for sentiment analysis - COMPLETE"""
    
    # ============================================
    # COMPLETE EMOJI SENTIMENT MAPPING
    # ============================================
    EMOJI_SENTIMENT = {
        # ===== POSITIVE EMOJIS =====
        # Smileys & Faces
        '😀': 'positive', '😁': 'positive', '😂': 'positive', '🤣': 'positive',
        '😃': 'positive', '😄': 'positive', '😅': 'positive', '😆': 'positive',
        '😉': 'positive', '😊': 'positive', '😇': 'positive', '😍': 'positive',
        '😘': 'positive', '😗': 'positive', '😋': 'positive', '😎': 'positive',
        '🥰': 'positive', '😻': 'positive', '🥳': 'positive', '🤩': 'positive',
        '😺': 'positive', '😸': 'positive', '😹': 'positive', '😽': 'positive',
        
        # ===== HEARTS - ALL COLORS (FIXED) =====
        '❤️': 'positive', '❤': 'positive', '🧡': 'positive', '💛': 'positive',
        '💚': 'positive', '💙': 'positive', '💜': 'positive', '🤍': 'positive',
        '🤎': 'positive', '🖤': 'positive', '💗': 'positive', '💖': 'positive',
        '💕': 'positive', '💞': 'positive', '💓': 'positive', '💝': 'positive',
        '💟': 'positive', '♥️': 'positive', '♥': 'positive',
        
        # Stars & Sparkles
        '⭐': 'positive', '🌟': 'positive', '✨': 'positive', '💫': 'positive',
        '🎉': 'positive', '🎊': 'positive', '🎈': 'positive', '🎁': 'positive',
        '🏆': 'positive', '🥇': 'positive', '🥈': 'positive', '🥉': 'positive',
        
        # Thumbs & Hands
        '👍': 'positive', '👏': 'positive', '🙌': 'positive', '🤗': 'positive',
        '🤝': 'positive', '✌️': 'positive', '✌': 'positive', '👌': 'positive',
        '💪': 'positive', '🙏': 'positive',
        
        # Animals & Nature
        '🌈': 'positive', '🌸': 'positive', '🌺': 'positive', '🌻': 'positive',
        '🌹': 'positive', '🌷': 'positive', '🌿': 'positive', '🍀': 'positive',
        '🐶': 'positive', '🐱': 'positive', '🦋': 'positive', '🐝': 'positive',
        
        # Food
        '🍕': 'positive', '🍔': 'positive', '🍟': 'positive', '🌮': 'positive',
        '🍣': 'positive', '🍰': 'positive', '🧁': 'positive', '🍫': 'positive',
        '🍩': 'positive', '🍪': 'positive',
        
        # Misc Positive
        '🔥': 'positive', '💯': 'positive', '🎯': 'positive', '✅': 'positive',
        '✔️': 'positive', '✔': 'positive', '☑️': 'positive', '☑': 'positive',
        
        # ===== NEUTRAL EMOJIS =====
        '😐': 'neutral', '😶': 'neutral', '😑': 'neutral',
        '😕': 'negative', '😬': 'neutral', '🤔': 'negative', '😯': 'neutral',
        '🙄': 'neutral', '😒': 'negative', '😪': 'neutral', '😴': 'neutral',
        '🤷': 'neutral', '🤷‍♂️': 'neutral', '🤷‍♀️': 'neutral', '😌': 'neutral',
        '🤐': 'neutral', '😶‍🌫️': 'neutral', '😮': 'neutral', '😲': 'neutral',
        
        # ===== NEGATIVE EMOJIS =====
        # Angry/Frustrated
        '😡': 'negative', '😠': 'negative', '🤬': 'negative', '😤': 'negative',
        '💢': 'negative', '💣': 'negative',
        
        # Sad/Crying
        '😢': 'negative', '😥': 'negative', '😓': 'negative', '😩': 'negative',
        '😫': 'negative', '😔': 'negative', '😭': 'negative', '😱': 'negative',
        '😨': 'negative', '😰': 'negative', '😣': 'negative', '😖': 'negative',
        '😞': 'negative', '😟': 'negative', '🥺': 'negative', '😿': 'negative',
        '😾': 'negative', '😏': 'negative',
        
        # Disgust
        '🤮': 'negative', '🤢': 'negative', '🤧': 'negative',
        
        # Thumbs Down
        '👎': 'negative', '👊': 'positive',
        
        # Broken Heart & Death
        '💔': 'negative', '💀': 'negative', '☠️': 'negative', '☠': 'negative',
        '💩': 'negative', '🖕': 'negative',
    }
    
    @classmethod
    def extract_emojis(cls, text: str) -> List[str]:
        """Extract all emojis from text"""
        if not text:
            return []
        return [c for c in text if c in cls.EMOJI_SENTIMENT]
    
    @classmethod
    def get_sentiment_from_emojis(cls, text: str) -> Tuple[str, Dict[str, int]]:
        """Analyze sentiment from emojis in text"""
        emojis = cls.extract_emojis(text)
        
        if not emojis:
            return 'neutral', {'positive': 0, 'neutral': 0, 'negative': 0}
        
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
        
        for emoji_char in emojis:
            sentiment = cls.EMOJI_SENTIMENT.get(emoji_char, 'neutral')
            sentiment_counts[sentiment] += 1
        
        # Determine dominant sentiment
        if sentiment_counts['positive'] > sentiment_counts['negative']:
            dominant = 'positive'
        elif sentiment_counts['negative'] > sentiment_counts['positive']:
            dominant = 'negative'
        else:
            dominant = 'neutral'
        
        return dominant, sentiment_counts
    
    @classmethod
    def replace_emojis_with_text(cls, text: str) -> str:
        """Replace emojis with textual representation for sentiment analysis"""
        if not text:
            return text
        
        emojis = cls.extract_emojis(text)
        for emoji_char in emojis:
            sentiment = cls.EMOJI_SENTIMENT.get(emoji_char, 'neutral')
            replacement = f" [EMOJI_{sentiment.upper()}] "
            text = text.replace(emoji_char, replacement)
        return text
    
    @classmethod
    def get_emoji_sentiment_score(cls, text: str) -> float:
        """Get a sentiment score from emojis (-1 to 1)"""
        _, counts = cls.get_sentiment_from_emojis(text)
        total = sum(counts.values())
        if total == 0:
            return 0.0
        
        score = (counts['positive'] - counts['negative']) / total
        return round(score, 2)
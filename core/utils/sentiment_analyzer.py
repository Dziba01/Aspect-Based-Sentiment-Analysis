import joblib
import re
from pathlib import Path
from django.conf import settings


class SentimentAnalyzer:

    ASPECTS = [
        'food', 'accommodation', 'staff_hospitality',
        'welcome_experience', 'cleanliness', 'value_for_money', 'safety'
    ]

    ASPECT_KEYWORDS = {
        'food': ['food', 'breakfast', 'dinner', 'lunch', 'meal', 'restaurant',
                 'dining', 'cuisine', 'taste', 'delicious', 'menu', 'chef',
                 'hungry', 'eat', 'ate', 'drink', 'coffee', 'tea', 'snack',
                 'tasty', 'yummy'],
        'accommodation': ['room', 'bed', 'bathroom', 'shower', 'wifi', 'aircon',
                          'pool', 'comfortable', 'spacious', 'noisy',
                          'sleep', 'slept', 'pillow', 'mattress', 'view',
                          'balcony', 'tv'],
        'staff_hospitality': ['staff', 'service', 'waiter', 'reception',
                              'friendly', 'helpful', 'rude', 'welcoming',
                              'attentive', 'manager'],
        'welcome_experience': ['check-in', 'arrival', 'greeting', 'reception',
                               'welcome', 'first impression', 'wait',
                               'checkin', 'arrive', 'arrived', 'lobby'],
        'cleanliness': ['clean', 'dirty', 'spotless', 'stained', 'mould', 'dust',
                        'hygiene', 'fresh', 'sanitary', 'tidy', 'messy',
                        'linen', 'towel'],
        'value_for_money': ['value', 'price', 'cost', 'expensive', 'cheap',
                            'worth', 'budget', 'reasonable', 'overpriced',
                            'money', 'paid', 'affordable', 'pricey'],
        'safety': ['safe', 'security', 'unsafe', 'dangerous', 'theft',
                   'secure', 'guard', 'lock', 'safety', 'locked', 'safe box'],
    }

    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.label_encoder = None
        self.is_loaded = False
        self._load_models()

    def _get_model_paths(self):
        try:
            base_dir = Path(settings.BASE_DIR)
        except Exception:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent

        models_dir = base_dir / 'models'
        return {
            'model': models_dir / 'sentiment_model.pkl',
            'vectorizer': models_dir / 'tfidf_vectorizer.pkl',
            'label_encoder': models_dir / 'label_encoder.pkl',
            'models_dir': models_dir,
        }

    def _load_models(self):
        paths = self._get_model_paths()
        models_dir = paths['models_dir']

        if not models_dir.exists():
            try:
                models_dir.mkdir(parents=True, exist_ok=True)
                print(f"📁 Created models directory at {models_dir}")
            except Exception as e:
                print(f"⚠️ Could not create models directory: {e}")
                return

        try:
            if paths['model'].exists():
                self.model = joblib.load(paths['model'])
                print("✅ Loaded sentiment model")
            else:
                print("⚠️ Model file not found")

            if paths['vectorizer'].exists():
                self.vectorizer = joblib.load(paths['vectorizer'])
                print("✅ Loaded TF-IDF vectorizer")
            else:
                print("⚠️ Vectorizer file not found")

            if paths['label_encoder'].exists():
                self.label_encoder = joblib.load(paths['label_encoder'])
                print("✅ Loaded label encoder")
            else:
                print("⚠️ Label encoder file not found")

            if all([self.model, self.vectorizer, self.label_encoder]):
                self.is_loaded = True
                print("🎯 Sentiment analyzer fully loaded!")
            else:
                print("⚠️ Some models missing. Using fallback.")
        except Exception as e:
            print(f"❌ Error loading models: {e}")

    def preprocess_text(self, text):
        if not text:
            return ""
        text = text.lower()
        from .emoji_processor import EmojiProcessor
        text = EmojiProcessor.replace_emojis_with_text(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def analyze_text(self, text):
        """Analyze sentiment of a single text (English, Shona or Ndebele)."""
        if not text or len(text.strip()) < 1:
            return {'sentiment': 'neutral', 'confidence': 0.0, 'language': 'unknown'}

        from .emoji_processor import EmojiProcessor
        from .language_detector import LanguageDetector
        from .translator import TranslatorService
        from .bantu_fallback import score as bantu_score

        # 1. Emoji-only shortcut
        text_without_emojis = re.sub(r'[^\w\s]', '', text)
        if len(text_without_emojis.strip()) == 0:
            emo, _ = EmojiProcessor.get_sentiment_from_emojis(text)
            return {'sentiment': emo, 'confidence': 0.85, 'language': 'emoji'}

        # 2. Detect language
        language = LanguageDetector.detect(text)

        # 3. Translate Shona / Ndebele -> English
        working_text = text
        translated_ok = False
        if language in ('shona', 'ndebele'):
            working_text = TranslatorService.to_english(text, source=language)
            translated_ok = working_text.strip().lower() != text.strip().lower()
            print(f"🌍 [{language}] original: {text[:80]}")
            print(f"🌍 [{language}] english : {working_text[:80]}")

        # 4. Emoji signal (always based on ORIGINAL text)
        emoji_sentiment, _ = EmojiProcessor.get_sentiment_from_emojis(text)
        emoji_score = EmojiProcessor.get_emoji_sentiment_score(text)

        # 5. Translation failed -> offline fallback for Shona/Ndebele
        if language in ('shona', 'ndebele') and not translated_ok:
            fb_sentiment, fb_conf = bantu_score(text)
            print(f"⚠️ Translation unavailable. Offline fallback → {fb_sentiment} ({fb_conf})")

            if fb_sentiment != 'neutral':
                return {
                    'sentiment': fb_sentiment,
                    'confidence': fb_conf,
                    'language': language,
                    'source': 'offline_fallback',
                }

            if abs(emoji_score) > 0.05:
                return {
                    'sentiment': 'positive' if emoji_score > 0 else 'negative',
                    'confidence': round(abs(emoji_score), 3),
                    'language': language,
                    'source': 'emoji',
                }

            return {'sentiment': 'neutral', 'confidence': 0.0, 'language': language}

        # 6. English pipeline on (possibly translated) text
        processed = self.preprocess_text(working_text)

        model_sentiment = 'neutral'
        model_confidence = 0.0

        if self.is_loaded and self.model and self.vectorizer:
            try:
                vec = self.vectorizer.transform([processed])
                pred = self.model.predict(vec)[0]
                probs = self.model.predict_proba(vec)[0]
                model_confidence = float(max(probs))
                if self.label_encoder:
                    model_sentiment = self.label_encoder.inverse_transform([pred])[0]
                else:
                    model_sentiment = {0: 'negative', 1: 'neutral', 2: 'positive'}.get(pred, 'neutral')
            except Exception as e:
                print(f"⚠️ Model prediction error: {e}")

        # 7. Fuse model + emoji
        scores = {'positive': 0.0, 'neutral': 0.0, 'negative': 0.0}
        if model_sentiment != 'neutral' and model_confidence > 0.3:
            scores[model_sentiment] += model_confidence
        if abs(emoji_score) > 0.05:
            if emoji_score > 0:
                scores['positive'] += 0.8 * abs(emoji_score)
            else:
                scores['negative'] += 0.8 * abs(emoji_score)

        max_score = max(scores.values())
        if max_score == 0:
            return {'sentiment': 'neutral', 'confidence': 0.0, 'language': language}

        if scores['positive'] == max_score and scores['positive'] > 0:
            final = 'positive'
        elif scores['negative'] == max_score and scores['negative'] > 0:
            final = 'negative'
        else:
            final = 'neutral'

        return {
            'sentiment': final,
            'confidence': round(max_score, 3),
            'language': language,
            'model_used': self.is_loaded,
            'translated_text': working_text if language in ('shona', 'ndebele') else None,
        }

    def analyze_review(self, text, rating=None):
        """Analyze a full review (overall + aspects)."""
        overall = self.analyze_text(text)

        # Aspect detection runs on the translated English text when available,
        # otherwise on the original.
        working_text = overall.get('translated_text') or text
        mentioned_aspects = self.detect_aspects(working_text)

        aspect_sentiments = {}
        for aspect in self.ASPECTS:
            if aspect in mentioned_aspects:
                aspect_sentiments[aspect] = self.get_aspect_sentiment(working_text, aspect)
            else:
                aspect_sentiments[aspect] = {
                    'sentiment': 'neutral',
                    'confidence': 0.0,
                    'mentioned': False,
                    'keywords_found': [],
                }
        aspect_sentiments['_other'] = len(mentioned_aspects) == 0

        return {
            'review_text': text,
            'overall_sentiment': overall,
            'aspect_sentiments': aspect_sentiments,
            'rating': rating,
            'mentioned_aspects': mentioned_aspects,
            'language': overall.get('language', 'unknown'),
        }

    def detect_aspects(self, text):
        text_lower = text.lower()
        mentioned = []
        for aspect, keywords in self.ASPECT_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    mentioned.append(aspect)
                    break

        seen = set()
        unique = []
        for a in mentioned:
            if a not in seen:
                seen.add(a)
                unique.append(a)
        return unique

    def get_aspect_sentiment(self, text, aspect):
        text_lower = text.lower()
        keywords = self.ASPECT_KEYWORDS.get(aspect, [])
        mentioned = [kw for kw in keywords if kw in text_lower]

        if not mentioned:
            return {
                'sentiment': 'neutral',
                'confidence': 0.0,
                'mentioned': False,
                'keywords_found': [],
            }

        sentences = re.split(r'[.!?]+', text)
        relevant = [s.strip() for s in sentences if any(kw in s.lower() for kw in keywords)]
        combined = ' '.join(relevant) if relevant else text
        result = self.analyze_text(combined)

        return {
            'sentiment': result['sentiment'],
            'confidence': result['confidence'],
            'mentioned': True,
            'keywords_found': mentioned[:5],
        }

    def process_rating_to_sentiment(self, rating):
        if rating >= 4.0:
            return 'positive'
        if rating >= 2.5:
            return 'neutral'
        return 'negative'

    def get_model_status(self):
        return {
            'is_loaded': self.is_loaded,
            'has_model': self.model is not None,
            'has_vectorizer': self.vectorizer is not None,
            'has_label_encoder': self.label_encoder is not None,
            'model_type': 'Logistic Regression' if self.model else 'None',
        }


# Initialize global instance
sentiment_analyzer = SentimentAnalyzer()
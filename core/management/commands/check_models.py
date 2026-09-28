from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import joblib

class Command(BaseCommand):
    help = 'Check the status of sentiment analysis models'

    def handle(self, *args, **options):
        self.stdout.write('🔍 Checking sentiment analysis models...')
        
        models_dir = Path(settings.BASE_DIR) / 'models'
        
        if not models_dir.exists():
            self.stdout.write(self.style.ERROR(f'❌ Models directory not found: {models_dir}'))
            return
        
        model_files = {
            'sentiment_model.pkl': 'Logistic Regression Model',
            'tfidf_vectorizer.pkl': 'TF-IDF Vectorizer',
            'label_encoder.pkl': 'Label Encoder',
            'best_model_info.pkl': 'Best Model Info'
        }
        
        status = {}
        
        self.stdout.write(f'\n📂 Models directory: {models_dir.absolute()}')
        self.stdout.write('-' * 50)
        
        for filename, description in model_files.items():
            file_path = models_dir / filename
            exists = file_path.exists()
            status[filename] = exists
            
            if exists:
                size = file_path.stat().st_size
                size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
                self.stdout.write(f'✅ {filename}: {description} ({size_str})')
            else:
                self.stdout.write(f'❌ {filename}: {description} (NOT FOUND)')
        
        self.stdout.write('-' * 50)
        
        # Try to load models and test
        if status['sentiment_model.pkl'] and status['tfidf_vectorizer.pkl']:
            self.stdout.write('\n🔄 Testing model loading...')
            try:
                model = joblib.load(models_dir / 'sentiment_model.pkl')
                vectorizer = joblib.load(models_dir / 'tfidf_vectorizer.pkl')
                
                self.stdout.write(self.style.SUCCESS('✅ Models loaded successfully!'))
                
                # Test prediction
                test_text = "The service was excellent and the food was delicious."
                try:
                    import re
                    processed = re.sub(r'[^a-zA-Z\s]', ' ', test_text.lower())
                    vectorized = vectorizer.transform([processed])
                    prediction = model.predict(vectorized)[0]
                    self.stdout.write(f'🧪 Test prediction: "{test_text[:30]}..." → {prediction}')
                except Exception as e:
                    self.stdout.write(f'⚠️ Test prediction failed: {e}')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error loading models: {e}'))
        
        # Check from sentiment_analyzer
        from core.utils.sentiment_analyzer import sentiment_analyzer
        status = sentiment_analyzer.get_model_status()
        
        self.stdout.write(f'\n📊 Sentiment Analyzer Status:')
        self.stdout.write(f'   - Fully Loaded: {status["is_loaded"]}')
        self.stdout.write(f'   - Has Model: {status["has_model"]}')
        self.stdout.write(f'   - Has Vectorizer: {status["has_vectorizer"]}')
        self.stdout.write(f'   - Has Label Encoder: {status["has_label_encoder"]}')
        
        if not status['is_loaded']:
            self.stdout.write(self.style.WARNING('\n⚠️ Models are not fully loaded. Run:'))
            self.stdout.write('   python manage.py setup_models')
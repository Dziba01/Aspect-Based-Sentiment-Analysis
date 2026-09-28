from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
import shutil
import os
import joblib
from core.utils.sentiment_analyzer import sentiment_analyzer

class Command(BaseCommand):
    help = 'Setup sentiment analysis models from notebook output'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-dir',
            type=str,
            help='Directory containing the model files from notebook',
            default='.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force overwrite existing models'
        )

    def handle(self, *args, **options):
        self.stdout.write('🔧 Setting up sentiment analysis models...')
        
        source_dir = Path(options['source_dir'])
        models_dir = Path(settings.BASE_DIR) / 'models'
        
        # Create models directory
        models_dir.mkdir(exist_ok=True)
        
        # Define expected files from notebook
        source_files = {
            'logistic_regression.pkl': 'sentiment_model.pkl',
            'tfidf_vectorizer.pkl': 'tfidf_vectorizer.pkl',
            'label_encoder.pkl': 'label_encoder.pkl',
            'best_model_info.pkl': 'best_model_info.pkl'
        }
        
        copied_count = 0
        missing_count = 0
        
        self.stdout.write(f'📂 Looking for models in: {source_dir.absolute()}')
        
        # Try to find and copy models
        for source_name, target_name in source_files.items():
            source_path = source_dir / source_name
            
            # Also check if it's in a subdirectory
            if not source_path.exists():
                # Check in models subdirectory
                alt_path = source_dir / 'models' / source_name
                if alt_path.exists():
                    source_path = alt_path
            
            if source_path.exists():
                target_path = models_dir / target_name
                
                if target_path.exists() and not options['force']:
                    self.stdout.write(f'⏭️ Skipping {target_name} (already exists, use --force to overwrite)')
                    continue
                
                shutil.copy2(source_path, target_path)
                copied_count += 1
                self.stdout.write(f'✅ Copied {source_name} → models/{target_name}')
            else:
                missing_count += 1
                self.stdout.write(f'⚠️ Source file not found: {source_name}')
        
        # Check if files were copied
        if copied_count > 0:
            self.stdout.write(self.style.SUCCESS(f'✅ Copied {copied_count} model files'))
            
            # Try to load the models
            self.stdout.write('\n🔄 Attempting to load models...')
            status = sentiment_analyzer.get_model_status()
            
            if status['is_loaded']:
                self.stdout.write(self.style.SUCCESS('✅ Models loaded successfully!'))
            else:
                self.stdout.write(self.style.WARNING('⚠️ Models copied but could not be loaded.'))
                self.stdout.write('   Please check the file paths and formats.')
        else:
            self.stdout.write(self.style.ERROR('❌ No model files were copied.'))
            self.stdout.write('   Make sure you have run the sentiment_model.ipynb notebook first.')
        
        self.stdout.write(f'\n📋 Summary:')
        self.stdout.write(f'   - Copied: {copied_count} files')
        self.stdout.write(f'   - Missing: {missing_count} files')
        self.stdout.write(f'   - Models directory: {models_dir.absolute()}')
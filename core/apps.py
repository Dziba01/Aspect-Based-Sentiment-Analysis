from django.apps import AppConfig
import os
import logging

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Sentiment Analysis System'
    
    def ready(self):
        # Import signals
        import core.signals
        
        # Initialize sentiment analyzer when app starts
        try:
            from .utils.sentiment_analyzer import sentiment_analyzer
            status = sentiment_analyzer.get_model_status()
            
            if status['is_loaded']:
                print('✅ Sentiment analyzer initialized with trained models')
                logger.info('Sentiment analyzer initialized with trained models')
            else:
                print('⚠️ Sentiment analyzer running in fallback mode (models not loaded)')
                print(f'   Models directory: {sentiment_analyzer._get_model_paths()["models_dir"]}')
                logger.warning('Sentiment analyzer running in fallback mode')
                
        except Exception as e:
            print(f'⚠️ Error initializing sentiment analyzer: {e}')
            logger.error(f'Error initializing sentiment analyzer: {e}')
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Review, Hotel
from .utils.sentiment_analyzer import sentiment_analyzer

@receiver(pre_save, sender=Review)
def process_review_sentiment(sender, instance, **kwargs):
    """Auto-process sentiment when a review is saved"""
    if instance.review_text and not instance.is_processed:
        # Analyze the review
        analysis = sentiment_analyzer.analyze_review(
            instance.review_text, 
            instance.rating
        )
        
        # Set overall sentiment
        instance.sentiment_overall = analysis['overall_sentiment']['sentiment']
        instance.confidence_score = analysis['overall_sentiment']['confidence']
        
        # Set aspect sentiments
        for aspect, result in analysis['aspect_sentiments'].items():
            field_name = f'sentiment_{aspect}'
            setattr(instance, field_name, result['sentiment'])
        
        instance.is_processed = True

@receiver(post_save, sender=Hotel)
def generate_hotel_qr_code(sender, instance, created, **kwargs):
    """Generate QR code when a new hotel is created"""
    if created and not instance.qr_code:
        from django.core.files.base import ContentFile
        from django.urls import reverse
        import qrcode
        from io import BytesIO
        
        base_url = 'http://localhost:8000'
        feedback_url = f"{base_url}/feedback/{instance.slug}/"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(feedback_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        instance.qr_code.save(
            f"qr_{instance.slug}.png",
            ContentFile(buffer.getvalue()),
            save=False
        )
        instance.qr_code_url = feedback_url
        instance.save()
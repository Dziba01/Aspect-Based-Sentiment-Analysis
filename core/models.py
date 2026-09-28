from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Region(models.Model):
    """Regions in Zimbabwe for tourism categorization"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Hotel(models.Model):
    """Hotel/Lodge model for Zimbabwean tourism establishments"""
    
    HOTEL_TYPES = [
        ('HOTEL', 'Hotel'),
        ('LODGE', 'Lodge'),
        ('RESORT', 'Resort'),
        ('B&B', 'Bed & Breakfast'),
        ('GUESTHOUSE', 'Guesthouse'),
        ('CAMP', 'Camp'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    hotel_type = models.CharField(max_length=20, choices=HOTEL_TYPES, default='HOTEL')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='hotels')
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    manager = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='managed_hotel'
    )
    
    zta_registration_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    is_approved_by_zta = models.BooleanField(default=False)
    
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_code_url = models.URLField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'region']
    
    def __str__(self):
        return f"{self.name} - {self.region.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            import re
            self.slug = re.sub(r'[^a-zA-Z0-9-]', '-', self.name.lower())
        super().save(*args, **kwargs)
    
    def get_total_reviews(self):
        return self.reviews.count()
    
    def get_average_rating(self):
        avg = self.reviews.aggregate(models.Avg('rating'))['rating__avg']
        return round(avg, 2) if avg else 0
    
    def get_sentiment_distribution(self):
        sentiments = self.reviews.values('sentiment_overall').annotate(
            count=models.Count('id')
        )
        result = {'positive': 0, 'neutral': 0, 'negative': 0}
        for s in sentiments:
            if s['sentiment_overall']:
                result[s['sentiment_overall']] = s['count']
        return result
    
    def get_aspect_sentiments(self):
        from django.db.models import Count
        
        aspects = ['food', 'accommodation', 'staff_hospitality', 
                   'welcome_experience', 'cleanliness', 'value_for_money', 'safety']
        
        result = {}
        for aspect in aspects:
            field_name = f'sentiment_{aspect}'
            reviews = self.reviews.exclude(**{field_name: None})
            
            if not reviews.exists():
                result[aspect] = {'positive': 0, 'neutral': 0, 'negative': 0}
                continue
            
            sentiment_counts = reviews.values(field_name).annotate(count=models.Count('id'))
            
            counts = {'positive': 0, 'neutral': 0, 'negative': 0}
            for sc in sentiment_counts:
                if sc[field_name]:
                    counts[sc[field_name]] = sc['count']
            
            result[aspect] = counts
        
        return result
    
    def get_service_gaps(self):
        aspect_sentiments = self.get_aspect_sentiments()
        gaps = []
        
        for aspect, sentiments in aspect_sentiments.items():
            total = sum(sentiments.values())
            if total > 0:
                negative_percentage = (sentiments['negative'] / total) * 100
                positive_percentage = (sentiments['positive'] / total) * 100
                neutral_percentage = (sentiments['neutral'] / total) * 100
                gaps.append({
                    'aspect': aspect,
                    'positive_count': sentiments['positive'],
                    'neutral_count': sentiments['neutral'],
                    'negative_count': sentiments['negative'],
                    'total_count': total,
                    'positive_percentage': round(positive_percentage, 2),
                    'neutral_percentage': round(neutral_percentage, 2),
                    'negative_percentage': round(negative_percentage, 2),
                    'sentiment_distribution': sentiments
                })
        
        gaps.sort(key=lambda x: x['negative_percentage'], reverse=True)
        return gaps

class Review(models.Model):
    """Guest review model with aspect-based sentiment analysis"""
    
    PLATFORM_CHOICES = [
        ('TRIPADVISOR', 'TripAdvisor'),
        ('GOOGLE', 'Google Reviews'),
        ('BOOKING', 'Booking.com'),
        ('QR', 'QR Code Feedback'),
        ('MANUAL', 'Manual Entry'),
    ]
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    review_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='reviews')
    review_text = models.TextField()
    rating = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='QR')
    platform_review_id = models.CharField(max_length=100, blank=True, null=True)
    reviewer_name = models.CharField(max_length=100, blank=True, null=True)
    review_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    sentiment_overall = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True, null=True)
    confidence_score = models.FloatField(default=0.0)
    
    # Aspect-based sentiments
    sentiment_food = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True, null=True)
    sentiment_accommodation = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True, null=True)
    sentiment_staff_hospitality = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True, null=True)
    sentiment_welcome_experience = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True, null=True)
    sentiment_cleanliness = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True, null=True)
    sentiment_value_for_money = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True, null=True)
    sentiment_safety = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, blank=True, null=True)
    
    is_processed = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-review_date']
        indexes = [
            models.Index(fields=['hotel', 'review_date']),
            models.Index(fields=['platform']),
            models.Index(fields=['sentiment_overall']),
        ]
    
    def __str__(self):
        return f"{self.hotel.name} - {self.review_date.strftime('%Y-%m-%d')}"
    
    def get_aspect_sentiments_dict(self):
        return {
            'food': self.sentiment_food,
            'accommodation': self.sentiment_accommodation,
            'staff_hospitality': self.sentiment_staff_hospitality,
            'welcome_experience': self.sentiment_welcome_experience,
            'cleanliness': self.sentiment_cleanliness,
            'value_for_money': self.sentiment_value_for_money,
            'safety': self.sentiment_safety,
        }

class WeeklyReport(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='reports')
    week_start = models.DateField()
    week_end = models.DateField()
    report_file = models.FileField(upload_to='reports/', blank=True, null=True)
    total_reviews = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0.0)
    positive_count = models.IntegerField(default=0)
    neutral_count = models.IntegerField(default=0)
    negative_count = models.IntegerField(default=0)
    aspect_summary = models.JSONField(default=dict)
    service_gaps = models.JSONField(default=dict)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-week_start']
        unique_together = ['hotel', 'week_start']
    
    def __str__(self):
        return f"{self.hotel.name} - Week of {self.week_start}"

class ZTAReport(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='zta_reports', null=True, blank=True)
    report_date = models.DateField()
    report_file = models.FileField(upload_to='zta_reports/', blank=True, null=True)
    total_hotels = models.IntegerField(default=0)
    total_reviews = models.IntegerField(default=0)
    average_rating_national = models.FloatField(default=0.0)
    regional_summary = models.JSONField(default=dict)
    aspect_summary_national = models.JSONField(default=dict)
    regional_service_gaps = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-report_date']
    
    def __str__(self):
        region_name = self.region.name if self.region else "National"
        return f"ZTA Report - {region_name} - {self.report_date}"
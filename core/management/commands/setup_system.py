from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.utils import timezone
from core.models import Region, Hotel, Review
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Setup the sentiment analysis system with initial data'
    
    def handle(self, *args, **options):
        self.stdout.write('Setting up the system...')
        
        # Create ZTA group
        zta_group, created = Group.objects.get_or_create(name='ZTA')
        if created:
            self.stdout.write('Created ZTA group')
        
        # Create regions
        regions_data = [
            {'name': 'Victoria Falls', 'code': 'VF'},
            {'name': 'Eastern Highlands', 'code': 'EH'},
            {'name': 'Harare', 'code': 'HRE'},
            {'name': 'Great Zimbabwe', 'code': 'GZ'},
            {'name': 'Hwange', 'code': 'HW'},
        ]
        
        regions = {}
        for region_data in regions_data:
            region, created = Region.objects.get_or_create(
                name=region_data['name'],
                defaults={'code': region_data['code']}
            )
            regions[region_data['name']] = region
            if created:
                self.stdout.write(f'Created region: {region.name}')
        
        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username='zta_admin',
            defaults={
                'email': 'zta@tourism.gov.zw',
                'first_name': 'ZTA',
                'last_name': 'Administrator',
                'is_superuser': True,
                'is_staff': True
            }
        )
        if created:
            admin_user.set_password('Zta@2026!')
            admin_user.save()
            admin_user.groups.add(zta_group)
            self.stdout.write('Created ZTA admin user')
        
        # Create sample hotels
        sample_hotels = [
            {'name': 'Victoria Falls Hotel', 'region': 'Victoria Falls', 'type': 'HOTEL'},
            {'name': 'The Elephant Hills Hotel', 'region': 'Victoria Falls', 'type': 'RESORT'},
            {'name': 'Amani Lodge', 'region': 'Victoria Falls', 'type': 'LODGE'},
            {'name': 'The Victoria Falls Safari Lodge', 'region': 'Victoria Falls', 'type': 'LODGE'},
            {'name': 'Troutbeck Resort', 'region': 'Eastern Highlands', 'type': 'RESORT'},
            {'name': 'The Leopard Rock Hotel', 'region': 'Eastern Highlands', 'type': 'HOTEL'},
            {'name': 'Zimbabwe Sun Hotel', 'region': 'Harare', 'type': 'HOTEL'},
            {'name': 'Cresta Lodge Harare', 'region': 'Harare', 'type': 'LODGE'},
            {'name': 'Great Zimbabwe Hotel', 'region': 'Great Zimbabwe', 'type': 'HOTEL'},
            {'name': 'Hwange Safari Lodge', 'region': 'Hwange', 'type': 'LODGE'},
        ]
        
        hotels = []
        for hotel_data in sample_hotels:
            region = regions[hotel_data['region']]
            hotel, created = Hotel.objects.get_or_create(
                name=hotel_data['name'],
                region=region,
                defaults={
                    'hotel_type': hotel_data['type'],
                    'is_approved_by_zta': True,
                    'is_active': True
                }
            )
            hotels.append(hotel)
            if created:
                self.stdout.write(f'Created hotel: {hotel.name}')
        
        # Create sample reviews with sentiment
        self.stdout.write('Creating sample reviews...')
        
        sentiments = ['positive', 'neutral', 'negative']
        aspects = ['food', 'accommodation', 'staff_hospitality', 
                   'welcome_experience', 'cleanliness', 'value_for_money', 'safety']
        
        review_templates = {
            'positive': [
                "Excellent service! The staff were incredibly friendly and helpful. The room was clean and comfortable. We had a wonderful stay!",
                "Amazing experience! The food was delicious and the location was perfect. Highly recommend to anyone visiting.",
                "Great value for money. The facilities were top-notch and the welcome was warm and professional. Will definitely return.",
                "Fantastic stay! The staff went above and beyond to make us feel welcome. The amenities were excellent.",
                "Beautiful hotel with stunning views. The service was impeccable and the rooms were spacious and clean."
            ],
            'neutral': [
                "Decent stay. The hotel was clean and the staff were okay. Nothing special but nothing terrible either.",
                "Average experience. The room was comfortable but the food was mediocre. The service was acceptable.",
                "It was fine. The location was good but the facilities were a bit dated. Staff were polite but not very attentive.",
                "The hotel met basic expectations. The welcome was standard and the amenities were adequate. Could be better.",
                "An okay hotel. The breakfast was decent and the room was clean. Nothing to complain about but nothing memorable."
            ],
            'negative': [
                "Disappointed with the service. The staff were rude and unhelpful. The room was dirty and the food was terrible.",
                "Terrible experience! The check-in took forever and the staff seemed disinterested. The facilities were poorly maintained.",
                "Not worth the money. The room was cramped and noisy. The staff were unprofessional and the service was slow.",
                "Very poor experience. The cleanliness was appalling and the staff were unhelpful. The food was cold and tasteless.",
                "I would not recommend this hotel. The service was slow, the room was outdated, and the facilities were in disrepair."
            ]
        }
        
        # Create 100 sample reviews
        review_count = 0
        for hotel in hotels:
            for i in range(10):
                sentiment = random.choice(sentiments)
                template = random.choice(review_templates[sentiment])
                rating = random.choice([3.0, 3.5, 4.0, 4.5, 5.0]) if sentiment == 'positive' else random.choice([1.0, 1.5, 2.0])
                
                review = Review.objects.create(
                    hotel=hotel,
                    review_text=template,
                    rating=rating,
                    platform=random.choice(['TRIPADVISOR', 'GOOGLE', 'BOOKING']),
                    review_date=timezone.now() - timedelta(days=random.randint(1, 90)),
                    sentiment_overall=sentiment,
                    confidence_score=random.uniform(0.75, 0.98)
                )
                
                # Set random aspect sentiments
                for aspect in aspects:
                    field_name = f'sentiment_{aspect}'
                    # 70% chance of having a sentiment for this aspect
                    if random.random() < 0.7:
                        setattr(review, field_name, random.choice(sentiments))
                
                review.save()
                review_count += 1
        
        self.stdout.write(f'Created {review_count} sample reviews')
        self.stdout.write(self.style.SUCCESS('System setup complete!'))
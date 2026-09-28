import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentiment_system.settings')
django.setup()

from core.models import Hotel, Review

hotel = Hotel.objects.first()
if not hotel:
    print("No hotel found. Create one first.")
    exit()

# English reviews
reviews = [
    # Positive
    ("Excellent service, very friendly staff!", "positive", 5),
    ("Beautiful hotel with amazing views", "positive", 5),
    ("The food was delicious and the staff were wonderful", "positive", 5),
    ("Great experience, will definitely come back", "positive", 5),
    ("Very clean rooms and comfortable beds", "positive", 4),
    ("The staff went above and beyond to help us", "positive", 5),
    ("Amazing hospitality, felt like home", "positive", 5),
    ("Fantastic place, everything was perfect", "positive", 5),
    ("Excellent value for money", "positive", 4),
    ("Loved the welcome experience, very warm", "positive", 5),
    
    # Negative
    ("Terrible service, rude staff", "negative", 1),
    ("Room was very dirty and smelly", "negative", 1),
    ("Worst experience ever, don't recommend", "negative", 1),
    ("Food was cold and tasteless", "negative", 1),
    ("Staff were unfriendly and unhelpful", "negative", 1),
    ("Check-in took forever, very unprofessional", "negative", 1),
    ("The room was noisy and uncomfortable", "negative", 2),
    ("Very disappointing, not worth the money", "negative", 1),
    ("Bad experience, will not return", "negative", 2),
    ("The service was extremely slow", "negative", 2),
    
    # Neutral
    ("It was okay, nothing special", "neutral", 3),
    ("Average hotel, decent but not great", "neutral", 3),
    ("The room was clean but the staff were just okay", "neutral", 3),
    ("Not bad, not great, just okay", "neutral", 3),
    ("Standard hotel, met expectations", "neutral", 3),
    ("Mediocre service, average food", "neutral", 3),
    ("Pretty average stay, nothing remarkable", "neutral", 3),
    ("Decent place, would stay again if needed", "neutral", 3),
    ("Fine for a night, nothing special", "neutral", 3),
    ("Acceptable but not memorable", "neutral", 3),
]

# Shona reviews
shona_reviews = [
    # Positive Shona
    ("Waita basa, vashandi vakanaka", "positive", 5),
    ("Mhoro hama, zvakanaka zvikuru", "positive", 5),
    ("Ndakafara zvikuru kugara apa", "positive", 5),
    ("Makasara, basa rakanaka", "positive", 5),
    ("Zvakanaka chaizvo, ndinokutendai", "positive", 5),
    
    # Negative Shona
    ("Hazvina kunaka, vashandi vakashata", "negative", 1),
    ("Handina kufara, hazvina kugadzikana", "negative", 1),
    ("Nhamo, zvakashata chaizvo", "negative", 1),
    ("Haana hanya, akashata", "negative", 1),
    ("Handizvifarire, hazvina chinhu", "negative", 1),
]

# Emoji reviews
emoji_reviews = [
    ("😊 Great stay! 👍", "positive", 5),
    ("👎 Horrible experience 😡", "negative", 1),
    ("😐 It was okay", "neutral", 3),
    ("😍 Loved it! ❤️", "positive", 5),
    ("😢 Very disappointed 😤", "negative", 1),
    ("👍👍👍 Excellent service", "positive", 5),
    ("💔 Terrible place", "negative", 1),
]

all_reviews = reviews + shona_reviews + emoji_reviews

count = 0
for text, sentiment, rating in all_reviews:
    if not Review.objects.filter(review_text=text, hotel=hotel).exists():
        Review.objects.create(
            hotel=hotel,
            review_text=text,
            rating=rating,
            sentiment_overall=sentiment,
            platform='MANUAL',
            is_processed=True
        )
        count += 1

print(f"✅ Added {count} labeled reviews to {hotel.name}")
print(f"Total reviews now: {Review.objects.count()}")
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sentiment_system.settings')
django.setup()

from core.models import Region

regions = ['Victoria Falls', 'Eastern Highlands', 'Harare', 'Great Zimbabwe', 'Hwange', 'Bulawayo', 'Masvingo']

for name in regions:
    Region.objects.get_or_create(name=name, code=name[:3].upper())

print("Regions created successfully!")
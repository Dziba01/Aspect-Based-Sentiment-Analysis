from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Avg
from datetime import timedelta
from core.models import Hotel, WeeklyReport
from core.utils.report_generator import ReportGenerator

class Command(BaseCommand):
    help = 'Generate weekly reports for all hotels'
    
    def handle(self, *args, **options):
        self.stdout.write('Generating weekly reports...')
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        hotels = Hotel.objects.filter(is_active=True)
        generated = 0
        
        for hotel in hotels:
            # Check if report already exists
            existing = WeeklyReport.objects.filter(
                hotel=hotel,
                week_start=week_start
            ).first()
            
            if existing:
                continue
            
            # Get reviews for this week
            reviews = hotel.reviews.filter(
                review_date__date__gte=week_start,
                review_date__date__lte=week_end
            )
            
            if reviews.exists():
                try:
                    # Generate PDF
                    pdf_buffer = ReportGenerator.generate_hotel_weekly_report(
                        hotel, reviews, week_start, week_end
                    )
                    
                    # Create report
                    report = WeeklyReport.objects.create(
                        hotel=hotel,
                        week_start=week_start,
                        week_end=week_end,
                        total_reviews=reviews.count(),
                        average_rating=reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
                        positive_count=reviews.filter(sentiment_overall='positive').count(),
                        neutral_count=reviews.filter(sentiment_overall='neutral').count(),
                        negative_count=reviews.filter(sentiment_overall='negative').count(),
                        aspect_summary=hotel.get_aspect_sentiments(),
                        service_gaps=hotel.get_service_gaps()
                    )
                    
                    # Save PDF
                    from django.core.files.base import ContentFile
                    report.report_file.save(
                        f"weekly_report_{hotel.slug}_{week_start.strftime('%Y%m%d')}.pdf",
                        ContentFile(pdf_buffer.getvalue())
                    )
                    report.save()
                    
                    # Send email
                    if hotel.email:
                        try:
                            ReportGenerator.send_report_email(
                                pdf_buffer, hotel.email, hotel.name, week_start, week_end
                            )
                            report.email_sent = True
                            report.email_sent_at = timezone.now()
                            report.save()
                            self.stdout.write(f'Sent report to {hotel.name}')
                        except Exception as e:
                            self.stdout.write(f'Failed to send email to {hotel.name}: {e}')
                    
                    generated += 1
                    self.stdout.write(f'Generated report for {hotel.name}')
                except Exception as e:
                    self.stdout.write(f'Error generating report for {hotel.name}: {e}')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully generated {generated} reports'))
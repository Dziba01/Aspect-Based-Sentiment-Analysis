from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
import io
import datetime
from django.core.mail import EmailMessage
from django.conf import settings

class ReportGenerator:
    """Generate PDF reports for hotels and ZTA"""
    
    @classmethod
    def generate_hotel_weekly_report(cls, hotel, reviews, week_start, week_end):
        """Generate weekly PDF report for a hotel"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        heading_style = styles['Heading1']
        normal_style = styles['Normal']
        
        # Custom styles
        center_style = ParagraphStyle(
            'CenterStyle',
            parent=styles['Normal'],
            alignment=TA_CENTER,
            fontSize=10
        )
        
        # Build content
        story = []
        
        # Header
        story.append(Paragraph(f"Weekly Sentiment Report", title_style))
        story.append(Paragraph(f"{hotel.name}", heading_style))
        story.append(Paragraph(f"Region: {hotel.region.name}", normal_style))
        story.append(Paragraph(f"Week: {week_start.strftime('%d %B %Y')} - {week_end.strftime('%d %B %Y')}", normal_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Summary statistics
        story.append(Paragraph("Summary Statistics", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Get sentiment distribution
        sentiment_counts = hotel.get_sentiment_distribution()
        total = sum(sentiment_counts.values())
        
        stats_data = [
            ['Metric', 'Value'],
            ['Total Reviews', str(total)],
            ['Positive Reviews', str(sentiment_counts.get('positive', 0))],
            ['Neutral Reviews', str(sentiment_counts.get('neutral', 0))],
            ['Negative Reviews', str(sentiment_counts.get('negative', 0))],
            ['Average Rating', str(hotel.get_average_rating())]
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Aspect Sentiment Analysis
        story.append(Paragraph("Aspect-Based Sentiment Analysis", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        aspect_sentiments = hotel.get_aspect_sentiments()
        
        aspect_data = [['Aspect', 'Positive', 'Neutral', 'Negative', 'Total']]
        for aspect, sentiments in aspect_sentiments.items():
            total_aspect = sum(sentiments.values())
            aspect_display = aspect.replace('_', ' ').title()
            aspect_data.append([
                aspect_display,
                str(sentiments['positive']),
                str(sentiments['neutral']),
                str(sentiments['negative']),
                str(total_aspect)
            ])
        
        aspect_table = Table(aspect_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        aspect_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(aspect_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Service Gaps (Top Priority Issues)
        story.append(Paragraph("Top Priority Service Gaps", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        gaps = hotel.get_service_gaps()
        if gaps:
            gap_data = [['Priority', 'Aspect', 'Negative %', 'Negative Count', 'Total']]
            for idx, gap in enumerate(gaps[:5], 1):
                aspect_display = gap['aspect'].replace('_', ' ').title()
                gap_data.append([
                    str(idx),
                    aspect_display,
                    f"{gap['negative_percentage']:.1f}%",
                    str(gap['negative_count']),
                    str(gap['total_count'])
                ])
            
            gap_table = Table(gap_data, colWidths=[0.8*inch, 1.8*inch, 1.2*inch, 1.2*inch, 1*inch])
            gap_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(gap_table)
        else:
            story.append(Paragraph("No service gaps identified. Great job!", normal_style))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Recent Reviews (Sample)
        story.append(Paragraph("Recent Guest Reviews (Sample)", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        recent_reviews = reviews[:5]
        if recent_reviews:
            for idx, review in enumerate(recent_reviews, 1):
                sentiment_emoji = {
                    'positive': '😊',
                    'neutral': '😐',
                    'negative': '😢'
                }.get(review.sentiment_overall, '😐')
                
                story.append(Paragraph(
                    f"{idx}. {sentiment_emoji} \"{review.review_text[:100]}{'...' if len(review.review_text) > 100 else ''}\"",
                    normal_style
                ))
                story.append(Paragraph(f"   Rating: {review.rating}/5 | Date: {review.review_date.strftime('%d %b %Y')}", center_style))
                story.append(Spacer(1, 0.1*inch))
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(
            f"Report generated on {datetime.datetime.now().strftime('%d %B %Y at %H:%M')}",
            center_style
        ))
        story.append(Paragraph(
            "© Aspect-Based Sentiment Analysis System | Midlands State University",
            center_style
        ))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    @classmethod
    def generate_zta_regional_report(cls, region, hotels, reviews):
        """Generate ZTA regional report"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        heading_style = styles['Heading1']
        normal_style = styles['Normal']
        
        story = []
        
        # Header
        story.append(Paragraph(f"ZTA Regional Sentiment Report", title_style))
        story.append(Paragraph(f"{region.name} Region", heading_style))
        story.append(Paragraph(f"Report Date: {datetime.datetime.now().strftime('%d %B %Y')}", normal_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Summary
        total_hotels = len(hotels)
        total_reviews = sum(h.get_total_reviews() for h in hotels)
        avg_rating = sum(h.get_average_rating() for h in hotels) / total_hotels if total_hotels > 0 else 0
        
        stats_data = [
            ['Metric', 'Value'],
            ['Total Hotels', str(total_hotels)],
            ['Total Reviews', str(total_reviews)],
            ['Average Rating', f"{avg_rating:.2f}/5"]
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 3*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Hotel Performance
        story.append(Paragraph("Hotel Performance Summary", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        hotel_data = [['Hotel', 'Type', 'Total Reviews', 'Avg Rating', 'Sentiment']]
        for hotel in hotels:
            sentiment_dist = hotel.get_sentiment_distribution()
            total = sum(sentiment_dist.values())
            if total > 0:
                pos_pct = (sentiment_dist.get('positive', 0) / total) * 100
                if pos_pct >= 60:
                    sentiment = 'Positive 😊'
                elif pos_pct >= 40:
                    sentiment = 'Neutral 😐'
                else:
                    sentiment = 'Negative 😢'
            else:
                sentiment = 'No Reviews'
            
            hotel_data.append([
                hotel.name[:30],
                hotel.get_hotel_type_display(),
                str(hotel.get_total_reviews()),
                f"{hotel.get_average_rating():.2f}",
                sentiment
            ])
        
        hotel_table = Table(hotel_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.5*inch])
        hotel_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(hotel_table)
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(
            f"Report generated on {datetime.datetime.now().strftime('%d %B %Y at %H:%M')}",
            normal_style
        ))
        story.append(Paragraph(
            "© Zimbabwe Tourism Authority | Aspect-Based Sentiment Analysis System",
            normal_style
        ))
        
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    @classmethod
    def send_report_email(cls, report_file, recipient_email, hotel_name, week_start, week_end):
        """Send report via email"""
        subject = f"Weekly Sentiment Report - {hotel_name}"
        body = f"""
        Dear Hotel Manager,

        Please find attached your weekly sentiment analysis report for {hotel_name}.

        Report Period: {week_start.strftime('%d %B %Y')} - {week_end.strftime('%d %B %Y')}
        
        This report includes:
        - Summary statistics of guest reviews
        - Aspect-based sentiment analysis
        - Top priority service gaps
        - Sample of recent reviews

        For more detailed insights, please log in to your dashboard.

        Best regards,
        Aspect-Based Sentiment Analysis System
        Midlands State University
        """
        
        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email]
        )
        
        email.attach(
            f"weekly_report_{hotel_name}_{week_start.strftime('%Y%m%d')}.pdf",
            report_file.getvalue(),
            'application/pdf'
        )
        
        return email.send()
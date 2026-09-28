import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.conf import settings
from datetime import datetime, timedelta
from .models import Hotel, Region, Review, WeeklyReport, ZTAReport
import json
from io import BytesIO
from django.views.decorators.csrf import csrf_exempt

from .models import Hotel, Region, Review, WeeklyReport, ZTAReport
from .forms import (
    GuestFeedbackForm, HotelLoginForm, ZTALoginForm,
    HotelRegistrationForm, DateRangeForm
)
from .utils.sentiment_analyzer import SentimentAnalyzer, sentiment_analyzer
from .utils.report_generator import ReportGenerator
from .utils.emoji_processor import EmojiProcessor


# ============================================
# SENTIMENT ANALYZER
# ============================================

def get_sentiment_analyzer():
    try:
        status = sentiment_analyzer.get_model_status()
        if status['is_loaded']:
            print('✅ Using trained sentiment models')
        else:
            print('⚠️ Using fallback sentiment analysis')
        return sentiment_analyzer
    except Exception as e:
        print(f'❌ Error initializing sentiment analyzer: {e}')
        return SentimentAnalyzer()


sentiment_analyzer_instance = get_sentiment_analyzer()


def custom_logout(request):
    logout(request)
    return redirect('/')


# ============================================
# PUBLIC / GUEST VIEWS
# ============================================

def home(request):
    total_reviews = Review.objects.filter(sentiment_overall__isnull=False).count()
    total_hotels = Hotel.objects.filter(is_active=True).count()
    avg_rating = (
        Review.objects.filter(sentiment_overall__isnull=False)
        .aggregate(Avg('rating'))['rating__avg'] or 0
    )

    context = {
        'total_reviews': total_reviews,
        'total_hotels': total_hotels,
        'avg_rating': round(avg_rating, 1),
        'regions': Region.objects.all(),
        'hotels': Hotel.objects.filter(is_active=True),
    }
    return render(request, 'guest/home.html', context)


@csrf_exempt
def guest_feedback(request, hotel_slug=None):
    """Guest feedback form - Shona / Ndebele auto-translated then analyzed."""

    hotel = None
    hotel_name = None

    if hotel_slug:
        try:
            hotel = Hotel.objects.get(slug=hotel_slug, is_active=True)
            hotel_name = hotel.name
            request.session['last_hotel_id'] = hotel.id
            request.session['last_hotel_slug'] = hotel.slug
        except Hotel.DoesNotExist:
            messages.warning(request, f'Hotel "{hotel_slug}" not found.')
            return redirect('core:home')

    if not hotel and 'last_hotel_id' in request.session:
        try:
            hotel = Hotel.objects.get(id=request.session['last_hotel_id'], is_active=True)
            hotel_name = hotel.name
        except Hotel.DoesNotExist:
            pass

    if not hotel:
        messages.info(request, "Please select a hotel from the list below.")
        return redirect('core:home')

    if request.method == 'POST':
        form = GuestFeedbackForm(request.POST, hotel=hotel)

        if form.is_valid():
            review = form.save(commit=False)
            review.hotel = hotel
            review.platform = 'QR'
            review.ip_address = request.META.get('REMOTE_ADDR')
            review.user_agent = request.META.get('HTTP_USER_AGENT', '')
            review.rating = 3.0

            text = review.review_text

            # -----------------------------
            # UNIFIED SENTIMENT ANALYSIS
            # -----------------------------
            analysis_result = sentiment_analyzer_instance.analyze_review(text, review.rating)
            overall = analysis_result['overall_sentiment']

            sentiment = overall['sentiment']
            confidence = overall['confidence']
            language = overall.get('language', 'english')

            print(f"🔍 [{language}] '{text[:60]}' → {sentiment} ({confidence:.2f})")

            review.sentiment_overall = sentiment
            review.confidence_score = confidence
            review.review_date = timezone.now()
            review.created_at = timezone.now()
            review.is_processed = True

            # -----------------------------
            # ASPECT SENTIMENTS
            # -----------------------------
            for aspect, result in analysis_result['aspect_sentiments'].items():
                if aspect == '_other':
                    continue
                field_name = f'sentiment_{aspect}'
                if isinstance(result, dict) and result.get('mentioned', False):
                    setattr(review, field_name, result['sentiment'])
                else:
                    setattr(review, field_name, None)

            review.save()

            print(f"✅ Review saved: '{text[:50]}' → {review.sentiment_overall} "
                  f"({review.confidence_score:.2f})")

            messages.success(request, "Thank you for your feedback! 😊")
            return redirect('core:feedback_success')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = GuestFeedbackForm(hotel=hotel)

    context = {
        'form': form,
        'hotel': hotel,
        'hotel_name': hotel_name,
    }
    return render(request, 'guest/feedback_form.html', context)


def feedback_success(request):
    hotel = None
    hotel_slug = request.session.get('last_hotel_slug')
    if hotel_slug:
        try:
            hotel = Hotel.objects.get(slug=hotel_slug, is_active=True)
        except Hotel.DoesNotExist:
            pass

    return render(request, 'guest/feedback_success.html', {
        'hotel': hotel,
        'hotel_slug': hotel_slug,
    })


def hotel_not_found_view(request):
    return render(request, 'guest/hotel_not_found.html', {'slug': request.path})


# ============================================
# HOTEL MANAGER VIEWS
# ============================================

@csrf_exempt
def hotel_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'managed_hotel'):
            return redirect('/hotel/dashboard/')
        elif request.user.is_superuser or request.user.groups.filter(name='ZTA').exists():
            messages.info(request, "You are logged in as ZTA. Use the ZTA dashboard.")
            return redirect('/zta/dashboard/')

    if request.method == 'POST':
        form = HotelLoginForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data.get('username'),
                password=form.cleaned_data.get('password'),
            )
            if user is not None:
                login(request, user)
                if user.is_superuser or user.groups.filter(name='ZTA').exists():
                    messages.info(request, "ZTA user logged in. Redirecting to ZTA dashboard.")
                    return redirect('/zta/dashboard/')
                elif hasattr(user, 'managed_hotel'):
                    return redirect('/hotel/dashboard/')
                else:
                    messages.warning(request, "Your account is not linked to a hotel.")
                    return redirect('/hotel/login/')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = HotelLoginForm()

    return render(request, 'hotel/login.html', {'form': form})


@csrf_exempt
def hotel_register(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'managed_hotel'):
            return redirect('/hotel/dashboard/')
        elif request.user.is_superuser or request.user.groups.filter(name='ZTA').exists():
            return redirect('/zta/dashboard/')

    if request.method == 'POST':
        form = HotelRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            if User.objects.filter(username=username).exists():
                messages.error(request, f"Username '{username}' is already taken.")
                return render(request, 'hotel/register.html', {'form': form})

            try:
                user = form.save()
            except Exception as e:
                messages.error(request, f"Error creating user: {str(e)}")
                return render(request, 'hotel/register.html', {'form': form})

            hotel_name = form.cleaned_data['hotel_name']
            region = form.cleaned_data['region']

            hotel, created = Hotel.objects.get_or_create(
                name=hotel_name,
                region=region,
                defaults={
                    'hotel_type': form.cleaned_data['hotel_type'],
                    'phone': form.cleaned_data.get('phone', ''),
                    'email': user.email,
                    'manager': user,
                }
            )

            if not created:
                hotel.manager = user
                hotel.phone = form.cleaned_data.get('phone', '')
                hotel.email = user.email
                hotel.save()
                messages.info(request, f"Hotel '{hotel.name}' already exists. You have been assigned as manager.")
            else:
                generate_hotel_qr_code(hotel)
                messages.success(request, f"Registration successful! Hotel '{hotel.name}' created.")

            login(request, user)
            return redirect('/hotel/dashboard/')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = HotelRegistrationForm()

    return render(request, 'hotel/register.html', {'form': form})


@login_required
def hotel_dashboard(request):
    if not hasattr(request.user, 'managed_hotel'):
        if request.user.is_superuser or request.user.groups.filter(name='ZTA').exists():
            messages.info(request, "You are logged in as ZTA. Please use the ZTA dashboard.")
            return redirect('/zta/dashboard/')
        messages.error(request, "You don't have access to a hotel dashboard.")
        return redirect('/hotel/login/')

    hotel = request.user.managed_hotel
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    recent_reviews = hotel.reviews.filter(
        review_date__gte=timezone.make_aware(datetime.combine(week_ago, datetime.min.time()))
    ).order_by('-review_date')[:20]

    sentiment_dist = hotel.get_sentiment_distribution()
    total_reviews = sum(sentiment_dist.values())
    aspect_sentiments = hotel.get_aspect_sentiments()
    service_gaps = hotel.get_service_gaps()

    weekly_reviews = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        day_reviews = hotel.reviews.filter(review_date__date=date)
        weekly_reviews.append({
            'date': date.strftime('%a'),
            'count': day_reviews.count(),
            'avg_rating': day_reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
        })

    rating_distribution = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}
    for review in hotel.reviews.all():
        rating_key = str(int(review.rating))
        if rating_key in rating_distribution:
            rating_distribution[rating_key] += 1

    context = {
        'hotel': hotel,
        'sentiment_dist': sentiment_dist,
        'total_reviews': total_reviews,
        'aspect_sentiments': aspect_sentiments,
        'service_gaps': service_gaps[:5],
        'recent_reviews': recent_reviews,
        'weekly_reviews': json.dumps(weekly_reviews),
        'rating_distribution': json.dumps(rating_distribution),
        'avg_rating': hotel.get_average_rating(),
        'today': today,
    }
    return render(request, 'hotel/dashboard.html', context)


@login_required
def hotel_aspect_detail(request, aspect):
    if not hasattr(request.user, 'managed_hotel'):
        messages.error(request, "You don't have access.")
        return redirect('/hotel/login/')

    hotel = request.user.managed_hotel

    if aspect not in sentiment_analyzer_instance.ASPECTS:
        messages.error(request, "Invalid aspect.")
        return redirect('/hotel/dashboard/')

    field_name = f'sentiment_{aspect}'
    reviews = hotel.reviews.exclude(**{field_name: None}).order_by('-review_date')

    sentiment_counts = reviews.values(field_name).annotate(count=Count('id'))
    distribution = {'positive': 0, 'neutral': 0, 'negative': 0}
    for sc in sentiment_counts:
        if sc[field_name]:
            distribution[sc[field_name]] = sc['count']

    paginator = Paginator(reviews, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    keywords = sentiment_analyzer_instance.ASPECT_KEYWORDS.get(aspect, [])

    context = {
        'hotel': hotel,
        'aspect': aspect,
        'aspect_display': aspect.replace('_', ' ').title(),
        'distribution': distribution,
        'reviews': page_obj,
        'keywords': keywords[:10],
        'total_reviews': reviews.count(),
    }
    return render(request, 'hotel/aspect_detail.html', context)


@login_required
def hotel_reports(request):
    if not hasattr(request.user, 'managed_hotel'):
        messages.error(request, "You don't have access.")
        return redirect('/hotel/login/')

    hotel = request.user.managed_hotel
    today = timezone.now().date()
    reports = hotel.reports.all().order_by('-week_start')

    if request.method == 'POST' and 'generate_report' in request.POST:
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        existing_report = WeeklyReport.objects.filter(
            hotel=hotel, week_start=week_start
        ).first()

        if existing_report:
            messages.warning(request, "Report for this week already exists.")
        else:
            reviews = hotel.reviews.filter(
                review_date__date__gte=week_start,
                review_date__date__lte=week_end,
            )

            if reviews.exists():
                pdf_buffer = ReportGenerator.generate_hotel_weekly_report(
                    hotel, reviews, week_start, week_end
                )

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
                    service_gaps=hotel.get_service_gaps(),
                )

                from django.core.files.base import ContentFile
                report.report_file.save(
                    f"weekly_report_{hotel.slug}_{week_start.strftime('%Y%m%d')}.pdf",
                    ContentFile(pdf_buffer.getvalue()),
                )
                report.save()

                messages.success(request, "Report generated successfully!")

                if hotel.email and settings.EMAIL_HOST_USER:
                    try:
                        ReportGenerator.send_report_email(
                            pdf_buffer, hotel.email, hotel.name, week_start, week_end
                        )
                        report.email_sent = True
                        report.email_sent_at = timezone.now()
                        report.save()
                        messages.info(request, "Report also sent via email.")
                    except Exception:
                        messages.warning(request, "Report generated but email sending failed.")
            else:
                messages.warning(request, "No reviews found for this week.")

        return redirect('/hotel/reports/')

    return render(request, 'hotel/reports.html', {
        'hotel': hotel,
        'reports': reports,
        'today': today,
    })


@login_required
def download_report(request, report_id):
    report = get_object_or_404(WeeklyReport, id=report_id)
    hotel = request.user.managed_hotel

    if report.hotel != hotel:
        messages.error(request, "You don't have access to this report.")
        return redirect('/hotel/reports/')

    if report.report_file:
        response = HttpResponse(report.report_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report.report_file.name}"'
        return response

    messages.error(request, "Report file not found.")
    return redirect('/hotel/reports/')


# ============================================
# ZTA VIEWS
# ============================================

@csrf_exempt
def zta_login(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.groups.filter(name='ZTA').exists():
            return redirect('/zta/dashboard/')
        elif hasattr(request.user, 'managed_hotel'):
            messages.info(request, "You are logged in as a hotel manager. Use the hotel dashboard.")
            return redirect('/hotel/dashboard/')

    if request.method == 'POST':
        form = ZTALoginForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data.get('username'),
                password=form.cleaned_data.get('password'),
            )
            if user is not None:
                login(request, user)
                if user.is_superuser or user.groups.filter(name='ZTA').exists():
                    return redirect('/zta/dashboard/')
                elif hasattr(user, 'managed_hotel'):
                    messages.info(request, "You are a hotel manager. Redirecting to hotel dashboard.")
                    return redirect('/hotel/dashboard/')
                else:
                    messages.warning(request, "Unknown user type.")
                    return redirect('/')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = ZTALoginForm()

    return render(request, 'zta/login.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='ZTA').exists(),
                  login_url='/hotel/dashboard/')
def zta_dashboard(request):
    today = timezone.now().date()

    regions = Region.objects.all()
    hotels = Hotel.objects.filter(is_active=True)
    total_hotels = hotels.count()
    all_reviews = Review.objects.filter(sentiment_overall__isnull=False)
    total_reviews = all_reviews.count()
    national_avg_rating = all_reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    # ---------- Sentiment counts ----------
    sentiment_dist = all_reviews.values('sentiment_overall').annotate(count=Count('id'))
    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    for sd in sentiment_dist:
        if sd['sentiment_overall']:
            sentiment_counts[sd['sentiment_overall']] = sd['count']

    positive_rate = (sentiment_counts['positive'] / total_reviews * 100) if total_reviews else 0

    # ---------- Regional stats (plain dicts — JSON safe) ----------
    regional_stats_list = []
    for region in regions:
        region_hotels = hotels.filter(region=region)
        region_reviews = Review.objects.filter(
            hotel__in=region_hotels, sentiment_overall__isnull=False
        )
        sentiment_map = {'positive': 0, 'neutral': 0, 'negative': 0}
        for row in region_reviews.values('sentiment_overall').annotate(count=Count('id')):
            if row['sentiment_overall']:
                sentiment_map[row['sentiment_overall']] = row['count']

        regional_stats_list.append({
            'region': {'id': region.id, 'name': region.name, 'code': region.code},
            'hotel_count': region_hotels.count(),
            'review_count': region_reviews.count(),
            'avg_rating': round(region_reviews.aggregate(Avg('rating'))['rating__avg'] or 0, 2),
            'sentiment_map': sentiment_map,
        })

    # Template loop version (needs objects with attributes)
    regional_stats = []
    for rs in regional_stats_list:
        regional_stats.append({
            'region': Region.objects.get(id=rs['region']['id']),
            'hotel_count': rs['hotel_count'],
            'review_count': rs['review_count'],
            'avg_rating': rs['avg_rating'],
            'sentiment_dist': [
                {'sentiment_overall': k, 'count': v}
                for k, v in rs['sentiment_map'].items()
            ],
        })

    # ---------- Top / Bottom hotels ----------
    top_hotels = list(
        hotels.annotate(avg_rating=Avg('reviews__rating'))
        .filter(avg_rating__isnull=False)
        .order_by('-avg_rating')[:5]
    )
    bottom_hotels = list(
        hotels.annotate(avg_rating=Avg('reviews__rating'))
        .filter(avg_rating__isnull=False)
        .order_by('avg_rating')[:5]
    )

    # ---------- Rating distribution ----------
    rating_distribution = {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0}
    for review in all_reviews:
        rating_key = str(int(review.rating)) if review.rating else '0'
        if rating_key in rating_distribution:
            rating_distribution[rating_key] += 1

    # ---------- Monthly trend (6 months) ----------
    monthly_trend = []
    for i in range(5, -1, -1):
        # Calculate month start
        first_of_this_month = today.replace(day=1)
        # Step back i months safely
        year = first_of_this_month.year
        month = first_of_this_month.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_start = first_of_this_month.replace(year=year, month=month, day=1)

        # Calculate month end
        if month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1, day=1)
        month_end = next_month_start - timedelta(days=1)

        month_reviews = all_reviews.filter(
            review_date__date__gte=month_start,
            review_date__date__lte=month_end,
        )
        monthly_trend.append({
            'month': month_start.strftime('%b %Y'),
            'count': month_reviews.count(),
            'avg_rating': round(month_reviews.aggregate(Avg('rating'))['rating__avg'] or 0, 2),
        })

    context = {
        'regions': regions,
        'total_hotels': total_hotels,
        'total_reviews': total_reviews,
        'national_avg_rating': round(national_avg_rating, 2),
        'sentiment_counts': sentiment_counts,
        'positive_rate': round(positive_rate, 1),
        'regional_stats': regional_stats,
        'top_hotels': top_hotels,
        'bottom_hotels': bottom_hotels,
        # 👇 RAW PYTHON OBJECTS — json_script will serialize them correctly
        'rating_distribution': rating_distribution,
        'monthly_trend': monthly_trend,
        'regional_stats_json': regional_stats_list,
        'today': today,
    }
    return render(request, 'zta/dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='ZTA').exists())
def zta_hotel_detail(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id, is_active=True)
    reviews = hotel.reviews.all()
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    context = {
        'hotel': hotel,
        'total_reviews': total_reviews,
        'avg_rating': avg_rating,
        'sentiment_dist': hotel.get_sentiment_distribution(),
        'aspect_sentiments': hotel.get_aspect_sentiments(),
        'service_gaps': hotel.get_service_gaps()[:10],
    }
    return render(request, 'zta/hotel_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='ZTA').exists())
def zta_regional_report(request, region_id=None):
    if region_id:
        region = get_object_or_404(Region, id=region_id)
        hotels = Hotel.objects.filter(region=region, is_active=True)
    else:
        region = None
        hotels = Hotel.objects.filter(is_active=True)

    if request.method == 'POST' and 'generate_report' in request.POST:
        pdf_buffer = ReportGenerator.generate_zta_regional_report(
            region or Region(name="National", code="ALL"),
            hotels,
            Review.objects.filter(hotel__in=hotels, sentiment_overall__isnull=False),
        )

        zta_report = ZTAReport.objects.create(
            region=region,
            report_date=timezone.now().date(),
            total_hotels=hotels.count(),
            total_reviews=Review.objects.filter(hotel__in=hotels).count(),
            average_rating_national=(
                Review.objects.filter(hotel__in=hotels)
                .aggregate(Avg('rating'))['rating__avg'] or 0
            ),
        )

        from django.core.files.base import ContentFile
        region_name = region.name if region else "National"
        zta_report.report_file.save(
            f"zta_report_{region_name}_{timezone.now().strftime('%Y%m%d')}.pdf",
            ContentFile(pdf_buffer.getvalue()),
        )
        zta_report.save()

        messages.success(request, "ZTA Report generated successfully!")
        return redirect('/zta/dashboard/')

    return render(request, 'zta/regional_report.html', {
        'region': region,
        'hotels': hotels,
        'today': timezone.now().date(),
        'regions': Region.objects.all(),
    })


# ============================================
# API VIEWS
# ============================================

@login_required
def api_hotel_stats(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)

    if not request.user.is_superuser and not request.user.groups.filter(name='ZTA').exists():
        if not hasattr(request.user, 'managed_hotel') or request.user.managed_hotel.id != hotel.id:
            return JsonResponse({'error': 'Access denied'}, status=403)

    data = {
        'name': hotel.name,
        'region': hotel.region.name,
        'total_reviews': hotel.get_total_reviews(),
        'average_rating': hotel.get_average_rating(),
        'sentiment_distribution': hotel.get_sentiment_distribution(),
        'aspect_sentiments': hotel.get_aspect_sentiments(),
        'service_gaps': hotel.get_service_gaps(),
        'recent_reviews': [
            {
                'text': r.review_text[:200],
                'rating': r.rating,
                'sentiment': r.sentiment_overall,
                'date': r.review_date.strftime('%Y-%m-%d'),
                'time': r.review_date.strftime('%H:%M'),
            }
            for r in hotel.reviews.order_by('-review_date')[:10]
        ],
    }
    return JsonResponse(data)


@login_required
def api_zta_summary(request):
    if not request.user.is_superuser and not request.user.groups.filter(name='ZTA').exists():
        return JsonResponse({'error': 'Access denied'}, status=403)

    data = {
        'total_hotels': Hotel.objects.filter(is_active=True).count(),
        'total_reviews': Review.objects.filter(sentiment_overall__isnull=False).count(),
        'national_avg_rating': Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0,
        'regions': [],
    }

    for region in Region.objects.all():
        hotels = Hotel.objects.filter(region=region, is_active=True)
        reviews = Review.objects.filter(hotel__in=hotels, sentiment_overall__isnull=False)
        data['regions'].append({
            'name': region.name,
            'hotel_count': hotels.count(),
            'review_count': reviews.count(),
            'avg_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
            'sentiment_distribution': {
                'positive': reviews.filter(sentiment_overall='positive').count(),
                'neutral': reviews.filter(sentiment_overall='neutral').count(),
                'negative': reviews.filter(sentiment_overall='negative').count(),
            },
        })

    return JsonResponse(data)


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_hotel_qr_code(hotel):
    import qrcode
    from django.core.files.base import ContentFile

    base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    feedback_url = f"{base_url}/feedback/{hotel.slug}/"

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
    hotel.qr_code.save(f"qr_{hotel.slug}.png", ContentFile(buffer.getvalue()), save=True)
    hotel.qr_code_url = feedback_url
    hotel.save()


def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)
from django.urls import path
from . import views
from django.views.generic import RedirectView

app_name = 'core'

urlpatterns = [
    # ============================================
    # PUBLIC / GUEST ROUTES
    # ============================================
    path('', views.home, name='home'),
    path('feedback/', views.guest_feedback, name='guest_feedback'),
    path('feedback/success/', views.feedback_success, name='feedback_success'),
    path('hotel/', RedirectView.as_view(pattern_name='core:hotel_login', permanent=False)),
    path('feedback/<slug:hotel_slug>/', views.guest_feedback, name='guest_feedback_hotel'),
    
    # ============================================
    # HOTEL MANAGER ROUTES (login only — no public registration)
    # ============================================
    path('hotel/login/', views.hotel_login, name='hotel_login'),
    # path('hotel/register/', views.hotel_register, name='hotel_register'),  # ❌ REMOVED - hotels are created by ZTA admin only
    path('hotel/dashboard/', views.hotel_dashboard, name='hotel_dashboard'),
    path('hotel/aspect/<str:aspect>/', views.hotel_aspect_detail, name='hotel_aspect_detail'),
    path('hotel/reports/', views.hotel_reports, name='hotel_reports'),
    path('hotel/reports/download/<int:report_id>/', views.download_report, name='download_report'),
    
    # ============================================
    # ZTA ROUTES
    # ============================================
    path('zta/login/', views.zta_login, name='zta_login'),
    path('zta/dashboard/', views.zta_dashboard, name='zta_dashboard'),
    path('zta/hotel/<int:hotel_id>/', views.zta_hotel_detail, name='zta_hotel_detail'),
    path('zta/regional-report/', views.zta_regional_report, name='zta_regional_report'),
    path('zta/regional-report/<int:region_id>/', views.zta_regional_report, name='zta_regional_report_region'),
    path('admin-dashboard/', views.zta_dashboard, name='admin_dashboard'),
    
    # ============================================
    # API ROUTES
    # ============================================
    path('api/hotel/<int:hotel_id>/', views.api_hotel_stats, name='api_hotel_stats'),
    path('api/zta/summary/', views.api_zta_summary, name='api_zta_summary'),
    
    # ============================================
    # LOGOUT
    # ============================================
    path('logout/', views.custom_logout, name='logout'),
]
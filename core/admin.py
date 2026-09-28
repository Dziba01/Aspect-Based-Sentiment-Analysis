from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import Region, Hotel, Review, WeeklyReport, ZTAReport


# ============================================
# CUSTOM USER FORM — for creating hotel managers from admin
# ============================================
class HotelManagerCreationForm(UserCreationForm):
    """
    Admin form for creating a hotel manager user.
    Allows ZTA admin to set username, email, password, and link a hotel.
    """
    hotel = forms.ModelChoiceField(
        queryset=Hotel.objects.all(),
        required=False,
        help_text="Assign this user as manager of a specific hotel",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill hotels that don't have a manager yet
        if self.instance and self.instance.pk:
            try:
                current_hotel = self.instance.managed_hotel
                self.fields['hotel'].initial = current_hotel
            except Hotel.DoesNotExist:
                pass
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            hotel = self.cleaned_data.get('hotel')
            if hotel:
                hotel.manager = user
                hotel.save()
        return user


# ============================================
# REGION ADMIN
# ============================================
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']
    prepopulated_fields = {'code': ('name',)}


# ============================================
# HOTEL ADMIN — with inline manager creation
# ============================================
class HotelAdminForm(forms.ModelForm):
    """Form to allow ZTA to assign or change a manager when creating/editing a hotel."""
    
    manager_username = forms.CharField(
        max_length=150,
        required=False,
        help_text="Username for the hotel manager. A new user will be created if it doesn't exist.",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    manager_email = forms.EmailField(
        required=False,
        help_text="Email for the hotel manager",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    manager_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="Set a password (only used if creating a new manager)"
    )
    
    class Meta:
        model = Hotel
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.manager:
            self.fields['manager_username'].initial = self.instance.manager.username
            self.fields['manager_email'].initial = self.instance.manager.email
    
    def save(self, commit=True):
        hotel = super().save(commit=False)
        
        username = self.cleaned_data.get('manager_username', '').strip()
        email = self.cleaned_data.get('manager_email', '').strip()
        password = self.cleaned_data.get('manager_password', '').strip()
        
        if username:
            try:
                # Existing user — just link
                user = User.objects.get(username=username)
                hotel.manager = user
                if email:
                    user.email = email
                    user.save()
            except User.DoesNotExist:
                # Create new user
                if not password:
                    password = User.objects.make_random_password()
                user = User.objects.create_user(
                    username=username,
                    email=email or f"{username}@hotel.local",
                    password=password
                )
                user.first_name = "Hotel"
                user.last_name = "Manager"
                user.save()
                hotel.manager = user
        
        if commit:
            hotel.save()
        return hotel


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    form = HotelAdminForm
    list_display = ['name', 'region', 'hotel_type', 'manager', 'is_active', 'is_approved_by_zta']
    list_filter = ['region', 'hotel_type', 'is_active', 'is_approved_by_zta']
    search_fields = ['name', 'address', 'zta_registration_number']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['qr_code', 'qr_code_url', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'hotel_type', 'region', 'address', 'phone', 'email', 'website')
        }),
        ('Management — ZTA Only', {
            'fields': ('manager_username', 'manager_email', 'manager_password'),
            'description': (
                'Only ZTA administrators can create hotel manager accounts. '
                'Fill in the username, email and password to create or update a manager. '
                'Leave password blank to auto-generate one.'
            )
        }),
        ('ZTA Approval', {
            'fields': ('zta_registration_number', 'is_approved_by_zta')
        }),
        ('QR Code', {
            'fields': ('qr_code', 'qr_code_url')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure only ZTA/superusers can create hotels."""
        if not (request.user.is_superuser or request.user.groups.filter(name='ZTA').exists()):
            raise PermissionError("Only ZTA administrators can create or edit hotels.")
        super().save_model(request, obj, form, change)


# ============================================
# REVIEW ADMIN
# ============================================
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['hotel', 'rating', 'sentiment_overall', 'platform', 'review_date']
    list_filter = ['platform', 'sentiment_overall', 'review_date', 'hotel__region']
    search_fields = ['review_text', 'hotel__name']
    readonly_fields = ['review_id', 'created_at']
    
    fieldsets = (
        ('Review Content', {
            'fields': ('hotel', 'review_text', 'rating', 'review_date')
        }),
        ('Sentiment Analysis', {
            'fields': ('sentiment_overall', 'confidence_score', 
                      'sentiment_food', 'sentiment_accommodation', 
                      'sentiment_staff_hospitality', 'sentiment_welcome_experience',
                      'sentiment_cleanliness', 'sentiment_value_for_money', 
                      'sentiment_safety')
        }),
        ('Metadata', {
            'fields': ('platform', 'platform_review_id', 'reviewer_name',
                      'is_processed', 'ip_address', 'user_agent', 'review_id')
        }),
    )


# ============================================
# WEEKLY REPORT ADMIN
# ============================================
@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ['hotel', 'week_start', 'week_end', 'total_reviews', 'email_sent']
    list_filter = ['email_sent', 'week_start']
    search_fields = ['hotel__name']
    readonly_fields = ['created_at']


# ============================================
# ZTA REPORT ADMIN
# ============================================
@admin.register(ZTAReport)
class ZTAReportAdmin(admin.ModelAdmin):
    list_display = ['region', 'report_date', 'total_hotels', 'total_reviews']
    list_filter = ['region', 'report_date']
    search_fields = ['region__name']
    readonly_fields = ['created_at']


# ============================================
# CUSTOM USER ADMIN — ZTA creates hotel managers here
# ============================================
class CustomUserAdmin(UserAdmin):
    add_form = HotelManagerCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'hotel'),
        }),
    )
    
    # Show which hotel this user manages
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_managed_hotel')
    
    def get_managed_hotel(self, obj):
        try:
            return obj.managed_hotel.name
        except Hotel.DoesNotExist:
            return "—"
    get_managed_hotel.short_description = 'Manages Hotel'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Allow any username — but only ZTA admins reach this page anyway
        if 'username' in form.base_fields:
            form.base_fields['username'].validators = []
        return form


# Unregister default and register custom
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
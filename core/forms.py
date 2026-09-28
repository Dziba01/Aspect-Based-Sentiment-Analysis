from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Review, Hotel, Region


class GuestFeedbackForm(forms.ModelForm):
    """Form for guests to submit feedback via QR code - NO RATING"""
    
    consent = forms.BooleanField(
        required=True,
        label="I consent to my feedback being used for service improvement",
        help_text="Your feedback will be anonymized and used to improve service quality"
    )
    
    class Meta:
        model = Review
        fields = ['review_text']  # REMOVED 'rating'
        widgets = {
            'review_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Tell us about your experience... What did you like? What could be improved?',
                'required': True
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.hotel = kwargs.pop('hotel', None)
        super().__init__(*args, **kwargs)
        if self.hotel:
            self.fields['review_text'].widget.attrs['placeholder'] = (
                f'Tell us about your experience at {self.hotel.name}...'
            )


class HotelLoginForm(AuthenticationForm):
    """Custom login form for hotel managers"""
    
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password'
    }))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Username or Email'
        self.fields['password'].label = 'Password'


class ZTALoginForm(AuthenticationForm):
    """Custom login form for ZTA users"""
    
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'ZTA Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'ZTA Password'
    }))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'ZTA Username'
        self.fields['password'].label = 'Password'


class HotelRegistrationForm(UserCreationForm):
    """Form for registering a new hotel manager"""
    
    username = forms.CharField(
        label="Username",
        max_length=150,
        help_text="Any username you want. No restrictions.",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose any username'
        })
    )
    
    hotel_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Hotel/Lodge Name'
    }))
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    hotel_type = forms.ChoiceField(
        choices=Hotel.HOTEL_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Email Address'
    }))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Phone Number'
    }))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 
                  'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['username'].validators = []
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            hotel = Hotel.objects.create(
                name=self.cleaned_data['hotel_name'],
                region=self.cleaned_data['region'],
                hotel_type=self.cleaned_data['hotel_type'],
                phone=self.cleaned_data.get('phone', ''),
                email=user.email,
                manager=user
            )
        return user


class DateRangeForm(forms.Form):
    """Form for filtering reports by date range"""
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
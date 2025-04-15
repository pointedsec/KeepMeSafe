from django import forms
from .models import Profile

class ProfileForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Master Key')
    confirm_password = forms.CharField(widget=forms.PasswordInput, label='Confirm your master key')
    
    class Meta:
        model = Profile
        fields = ['name']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password != confirm_password:
            raise forms.ValidationError('The passwords doesn\'t match')
        return cleaned_data

class LoginProfileForm(forms.Form):
    name = forms.CharField(label='Profile Name')
    password = forms.CharField(widget=forms.PasswordInput, label='Profile Master Password')
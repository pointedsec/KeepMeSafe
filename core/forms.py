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
    name = forms.CharField(label='Vault Name')
    password = forms.CharField(widget=forms.PasswordInput, label='Vault Master Password')

class CredentialForm(forms.Form):
    service = forms.CharField(label='Service', widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-150 ease-in-out'
    }))
    description = forms.CharField(label='Description', widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-150 ease-in-out'
    }))
    username = forms.CharField(label='Username', widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-150 ease-in-out'
    }))
    password = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-150 ease-in-out'
    }))

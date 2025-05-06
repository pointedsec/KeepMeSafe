from django.test import TestCase
from core.forms import ProfileForm, LoginProfileForm, CredentialForm
from core.models import Profile

class ProfileFormTest(TestCase):

    def test_profile_form_valid(self):
        form_data = {
            'name': 'TestProfile',
            'password': 'securepassword123',
            'confirm_password': 'securepassword123'
        }
        form = ProfileForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_profile_form_password_mismatch(self):
        form_data = {
            'name': 'TestProfile',
            'password': 'securepassword123',
            'confirm_password': 'differentpassword'
        }
        form = ProfileForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('The passwords doesn\'t match', form.errors['__all__'])

class LoginProfileFormTest(TestCase):

    def test_login_profile_form_valid(self):
        form_data = {
            'name': 'TestProfile',
            'password': 'securepassword123'
        }
        form = LoginProfileForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_login_profile_form_missing_fields(self):
        form_data = {
            'name': 'TestProfile'
            # password is missing
        }
        form = LoginProfileForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

class CredentialFormTest(TestCase):

    def test_credential_form_valid(self):
        form_data = {
            'service': 'Github',
            'description': 'Personal account',
            'username': 'user123',
            'password': 'pass123'
        }
        form = CredentialForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_credential_form_missing_fields(self):
        form_data = {
            'service': 'Github',
            'description': 'Personal account',
            # username and password are missing
        }
        form = CredentialForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('password', form.errors)

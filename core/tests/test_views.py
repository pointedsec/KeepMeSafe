from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.conf import settings
from core.utils.encrypted_actions import gen_master_key
from unittest import mock
from core.models import Profile
import tempfile
import shutil
import os

PROFILE_NAME = 'testing_name'
PROFILE_PASSWORD = 'testing_password'

class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.temp_media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.temp_media)
        self.override.enable()
        self.admin_password = settings.ADMIN_VAULT_PASSWORD
        os.makedirs(os.path.join(self.temp_media, 'vaults'), exist_ok=True)

    def create_test_profile(self):
        url = reverse('create_profile')
        form_data = {
            'name': PROFILE_NAME,
            'password': PROFILE_PASSWORD,
            'confirm_password': PROFILE_PASSWORD
        }
        session = self.client.session
        session['admin_authenticated'] = True
        session.save()
        response = self.client.post(url, form_data)
        profile = Profile.objects.get(name=PROFILE_NAME)
        return profile
    
    def test_create_profile_success(self):
        url = reverse('create_profile')
        form_data = {
            'name': PROFILE_NAME,
            'password': PROFILE_PASSWORD,
            'confirm_password': PROFILE_PASSWORD
        }
        session = self.client.session
        session['admin_authenticated'] = True
        session.save()
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, 302)
        profile = Profile.objects.get(name=PROFILE_NAME)
        self.assertEqual(profile.name, PROFILE_NAME)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.temp_media)

    def test_create_profile_redirect_if_not_admin(self):
        response = self.client.get(reverse('create_profile'))
        self.assertRedirects(response, reverse('admin_gate'))

    def test_profile_created_renders(self):
        profile = self.create_test_profile()
        response = self.client.get(reverse('profile_created', args=[profile.id]))
        self.assertEqual(response.status_code, 200)

    def test_login_profile_get_shows_form(self):
        response = self.client.get(reverse('login_profile_input'))
        self.assertEqual(response.status_code, 200)

    def test_login_profile_post_valid(self):
        data = {
            'name': PROFILE_NAME,
            'password': PROFILE_PASSWORD
        }
        profile = self.create_test_profile()
        response = self.client.post(reverse('login_profile_input'), data)
        self.assertRedirects(response, reverse('profile_accessed', args=[profile.id]))

    def test_profile_accessed_redirects_without_vault_key(self):
        self.client.session.pop('vault_key', None)
        self.client.session.save()
        profile = self.create_test_profile()
        response = self.client.get(reverse('profile_accessed', args=[profile.id]))
        self.assertRedirects(response, '/')

    def test_profile_accessed_renders(self):
        profile = self.create_test_profile()
        fernet, encoded_key = gen_master_key(PROFILE_PASSWORD)
        session = self.client.session
        session['vault_key'] = encoded_key
        session['vault_name'] = profile.name.capitalize()
        session['vault_id'] = str(profile.id)
        session.save()

        response = self.client.get(reverse('profile_accessed', args=[profile.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, profile.name)

    def test_close_vault_post(self):
        response = self.client.post(reverse('close_vault'))
        self.assertRedirects(response, '/')

    def test_close_vault_get_not_allowed(self):
        response = self.client.get(reverse('close_vault'))
        self.assertEqual(response.status_code, 405)

    def test_admin_gate_get(self):
        response = self.client.get(reverse('admin_gate'))
        self.assertEqual(response.status_code, 200)

    def test_admin_gate_post_correct_password(self):
        response = self.client.post(reverse('admin_gate'), {'admin_password': self.admin_password})
        self.assertRedirects(response, reverse('create_profile'))

    def test_admin_gate_post_incorrect_password(self):
        response = self.client.post(reverse('admin_gate'), {'admin_password': 'wrongpass'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid admin password')
    
    def test_zzzzz_delete_vault_success(self):
        profile = self.create_test_profile()
        fernet, encoded_key = gen_master_key(PROFILE_PASSWORD)
        session = self.client.session
        session['vault_key'] = encoded_key
        session['vault_name'] = profile.name.capitalize()
        session['vault_id'] = str(profile.id)
        session.save()

        response = self.client.delete(reverse('delete_vault', args=[profile.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vault deleted successfully')

    def test_delete_vault_no_vault_key(self):
        self.client.session.pop('vault_key', None)
        self.client.session.save()
        profile = self.create_test_profile()
        response = self.client.delete(reverse('delete_vault', args=[profile.id]))
        print("Status code:", response.status_code)
        self.assertEqual(response.status_code, 500)

    def test_delete_vault_wrong_method(self):
        profile = self.create_test_profile()
        response = self.client.get(reverse('delete_vault', args=[profile.id]))
        self.assertEqual(response.status_code, 405)
    
    def test_add_credential(self):
        profile = self.create_test_profile()
        fernet, encoded_key = gen_master_key(PROFILE_PASSWORD)
        session = self.client.session
        session['vault_key'] = encoded_key
        session['vault_name'] = profile.name.capitalize()
        session['vault_id'] = str(profile.id)
        session.save()
        url = reverse('profile_accessed', args=[profile.id])

        form_data = {
            'service': 'Test Service',
            'description': 'Test description',
            'username': 'test_user',
            'password': 'test_password'
        }

        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test_user')
    
    def test_update_credential(self):
        profile = self.create_test_profile()
        fernet, encoded_key = gen_master_key(PROFILE_PASSWORD)
        session = self.client.session
        session['vault_key'] = encoded_key
        session['vault_name'] = profile.name.capitalize()
        session['vault_id'] = str(profile.id)
        session.save()

        # Create credential first
        url = reverse('profile_accessed', args=[profile.id])

        form_data = {
            'service': 'Test Service',
            'description': 'Test description',
            'username': 'test_user',
            'password': 'test_password'
        }

        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test_user')

        # Update the credential
        url = reverse('profile_accessed', args=[profile.id])

        edit_form_data = {
            'edit_credential': '1',
            'edited_service': 'Updated Service',
            'edited_description': 'Updated description',
            'edited_user': 'updated_user',
            'edited_password': 'updated_password'
        }

        response = self.client.post(url, edit_form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'updated_user')

    def test_delete_credential(self):
        profile = self.create_test_profile()
        fernet, encoded_key = gen_master_key(PROFILE_PASSWORD)
        session = self.client.session
        session['vault_key'] = encoded_key
        session['vault_name'] = profile.name.capitalize()
        session['vault_id'] = str(profile.id)
        session.save()

        # Create credential first
        url = reverse('profile_accessed', args=[profile.id])

        form_data = {
            'service': 'Test Service',
            'description': 'Test description',
            'username': 'test_user',
            'password': 'test_password'
        }

        response = self.client.post(url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test_user')

        # Delete the credential
        url = reverse('profile_accessed', args=[profile.id])

        delete_form_data = {
            'delete_credential': '1'
        }

        response = self.client.post(url, delete_form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No saved credentials yet.')
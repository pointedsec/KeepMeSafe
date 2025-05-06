from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Profile, vault_upload_path
import uuid
import os

class ProfileModelTestCase(TestCase):

    def setUp(self):
        self.profile_name = "TestProfile"
        self.profile = Profile.objects.create(name=self.profile_name)

    def test_profile_creation(self):
        self.assertEqual(Profile.objects.count(), 1)
        self.assertEqual(self.profile.name, self.profile_name)
        self.assertIsInstance(self.profile.id, uuid.UUID)
        self.assertIsNotNone(self.profile.created_at)
        self.assertIsNotNone(self.profile.updated_at)
        self.assertEqual(str(self.profile), self.profile_name)

    def test_unique_name_constraint(self):
        with self.assertRaises(Exception):
            Profile.objects.create(name=self.profile_name)

    def test_vault_upload_path(self):
        filename = "vault.sqlite3"
        path = vault_upload_path(self.profile, filename)
        self.assertTrue(path.startswith("vaults/"))
        self.assertTrue(path.endswith(".sqlite3"))
        generated_uuid = path.split('/')[-1].split('.')[0]
        try:
            uuid.UUID(generated_uuid)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False
        self.assertTrue(is_valid_uuid)

    def test_file_upload_and_path(self):
        dummy_file = SimpleUploadedFile("testvault.sqlite3", b"dummy content")
        self.profile.vault_path = dummy_file
        self.profile.save()
        self.assertTrue(self.profile.vault_path.name.startswith("vaults/"))
        self.assertTrue(self.profile.vault_path.name.endswith(".sqlite3"))

    def test_str_method(self):
        self.assertEqual(str(self.profile), self.profile_name)

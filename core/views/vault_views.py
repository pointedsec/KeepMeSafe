from django.shortcuts import redirect, get_object_or_404, render
import os
from django.http import HttpResponseNotAllowed, HttpResponseServerError, JsonResponse
import logging
from core.models import Profile
from cryptography.fernet import Fernet
from core.utils.encrypted_actions import check_master_key, update_vault_encryption_key, gen_master_key
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def close_vault(request):
    if request.method == "POST":
        request.session.pop('vault_name', None)
        request.session.pop('vault_key', None)
        request.session.pop('vault_id', None)
        return redirect('/')
    else:
        return HttpResponseNotAllowed(['POST'])

def delete_vault(request, profile_id):
    if request.method == "DELETE":
        # Check if the vault_key in the session can decrypt the user's vault
        encoded_key = request.session.get('vault_key')
        if not encoded_key:
            logger.error('Cant delete vault without vault key..')
            return HttpResponseServerError('Error decrypting or loading the vault, vault key not found in the actual session')

        try:
            logger.info('Fernet created with vault key')
            cipher = Fernet(encoded_key.encode())
        except Exception as e:
            logger.error("Error decoding vault key: %s", e)
            return HttpResponseServerError('Error decrypting or loading the vault: %s', e)

        profile = get_object_or_404(Profile, id=profile_id)
        vault_path = profile.vault_path.path

        try:
            # Read and decrypt the vault
            with open(vault_path, 'rb') as f:
                encrypted_data = f.read()
            cipher.decrypt(encrypted_data)
            logger.info('Data decrypted for vault %s', profile.name)

            # Vault decrypted, deleting the vault
            if os.path.exists(vault_path):
                os.remove(vault_path)
                logger.info(f"Vault file {vault_path} deleted.")
            else:
                logger.warning(f"Vault file {vault_path} does not exist.")

            # User Deletion
            profile.delete()
            logger.info(f"Profile (vault) with ID {profile_id} deleted.")

            # Flushing the session
            request.session.flush()

        except Exception as e:
            logger.error('Error decrypting or loading the vault: %s', e)
            return HttpResponseServerError('Error decrypting or loading the vault: %s', e)

        return JsonResponse({'message': 'Vault deleted successfully'}, status=200)
    else:
        return HttpResponseNotAllowed('Method not allowed')

def edit_vault(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    if request.method == 'POST':
        new_name = request.POST.get('new_vault_name', '').strip()
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')

        # Check actual 'password'
        if not check_master_key(profile, current_password):
            return JsonResponse({'message': 'Password doesn\'t match with your actual password'}, status=500)

        # Check if a vault exists with the new name
        if new_name and Profile.objects.filter(name=new_name).exclude(id=profile.id).exists():
            return JsonResponse({'message': 'A vault exists already with that name'}, status=500)

        # Update name
        if new_name:
            profile.name = new_name

        # To update the 'password', we have to decrypt the vault to encrypt it with the new vault key
        if new_password:
            encoded_key = request.session.get('vault_key')
            cipher = Fernet(encoded_key.encode())
            try:
                update_vault_encryption_key(profile.vault_path.path, cipher, new_password)
                profile.save()
                fernet, encoded_key = gen_master_key(new_password)
                request.session['vault_key'] = encoded_key
                request.session['vault_name'] = profile.name.capitalize()
            except Exception as e:
                logger.error('Error updating encryption key for vault')
                return JsonResponse({'message': 'An error ocurred while changing the vault name or key'}, status=500)

        return JsonResponse({'message': 'Vault updated successfully'}, status=200)
    return JsonResponse({'message': 'Method not allowed'}, status=500)

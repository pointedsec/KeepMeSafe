from django.shortcuts import redirect, get_object_or_404
import os
from django.http import HttpResponseNotAllowed, HttpResponseServerError, JsonResponse
import logging
from core.models import Profile
from cryptography.fernet import Fernet
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

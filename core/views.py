from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProfileForm, LoginProfileForm, CredentialForm
import sqlite3
import os
from django.conf import settings
from django.http import HttpResponseNotAllowed, HttpResponseServerError, JsonResponse
import tempfile
import logging
import uuid
from .models import Profile
from .utils.encrypted_actions import gen_master_key, create_vault, check_master_key, save_database
from cryptography.fernet import Fernet
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_profile(request):
    # Only admins can create vaults
    if not request.session.get('admin_authenticated'):
        return redirect('admin_gate')
    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            profile = form.save(commit=False)

            # Generate the vault_path
            vault_path = os.path.join(settings.MEDIA_ROOT, 'vaults', f"{uuid.uuid4()}.sqlite3")
            logger.info('Vault path generated %s', vault_path)
            # Create the encrypted vault, cypher it and save the model
            create_vault(vault_path, password)
            profile.vault_path = vault_path
            profile.save()
            request.session.pop('admin_authenticated', None)
            return redirect('profile_created', profile_id=profile.id)
        else:
            return render(request, 'core/create_profile.html', {'form': form})
    else:
        form = ProfileForm()
        
    return render(request, 'core/create_profile.html', {'form': form})

def profile_created(request, profile_id):
    return render(request, 'core/profile_created.html', {'profile_id': profile_id})

def login_profile(request):
    if request.method == 'POST':
        form = LoginProfileForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['name']
            password = form.cleaned_data['password']
            # Check if a profile exists with that username
            try:
                profile = Profile.objects.get(name=username)
                # Check if the password is valid for his vault
                if check_master_key(profile, password):
                    logger.debug('Profile accesed succesfully, profile: %s', username)
                    fernet, encoded_key = gen_master_key(password)
                    request.session['vault_key'] = encoded_key
                    request.session['vault_name'] = profile.name.capitalize()
                    request.session['vault_id'] = str(profile.id)
                    return redirect('profile_accessed', profile_id=profile.id)
                else:
                    form.add_error('password', 'The profile and master password combination is incorrect')
            except Profile.DoesNotExist:
                logger.debug('Incorrect password introduced for a profile')
                form.add_error('password', 'The profile and master password combination is incorrect')
    else:
        form = LoginProfileForm()

    return render(request, 'core/login_profile.html', {'form': form})

# Also this method insert, update or delete a credential
def profile_accessed(request, profile_id):
    encoded_key = request.session.get('vault_key')
    if not encoded_key:
        logger.error('Profile accessed without vault key..')
        return redirect('/')
    
    form = CredentialForm(request.POST or None)

    try:
        logger.info('Fernet created with vault key')
        cipher = Fernet(encoded_key.encode())
    except Exception as e:
        logger.error("Error decoding vault key: %s", e)
        return redirect('/')

    profile = get_object_or_404(Profile, id=profile_id)
    vault_path = profile.vault_path.path

    try:
        # Read and decrypt the vault
        with open(vault_path, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = cipher.decrypt(encrypted_data)
        logger.info('Data decrypted for vault %s', profile.name)

        # Write the decrypted vault in a temporal file
        with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=True) as temp_vault:
            temp_vault.write(decrypted_data)
            temp_vault.flush()
            logger.info('Temporal decrypted vault file created for vault %s', profile.name)

            # Create a db instance with that file
            with sqlite3.connect(temp_vault.name) as conn:
                cursor = conn.cursor()
                logger.info('sqlite3 instance created for vault %s', profile.name)
                # Add a new credential
                if request.method == 'POST' and form.is_valid():
                    cursor.execute(
                    "INSERT INTO credentials (service, description, username, password) VALUES (?, ?, ?, ?)",
                    (
                        form.cleaned_data['service'],
                        form.cleaned_data['description'],
                        form.cleaned_data['username'],
                        form.cleaned_data['password']
                    )
                    )
                    conn.commit()
                    logger.info('inserted credential in vault %s', profile.name)
                    form = CredentialForm(None)
                    save_database(vault_path, temp_vault, cipher)
                 
                # Delete a credential
                if 'delete_credential' in request.POST:
                    credential_id = request.POST['delete_credential']
                    cursor.execute("DELETE FROM credentials WHERE id = ?", (credential_id,))
                    conn.commit()
                    logger.info('Delete credential in vault %s', profile.name)
                    save_database(vault_path, temp_vault, cipher)
                    form = CredentialForm(None)

                # Edit a credential
                if 'edit_credential' in request.POST:
                    credential_id = request.POST['edit_credential']
                    edited_service = request.POST['edited_service']
                    edited_description = request.POST['edited_description']
                    edited_user = request.POST['edited_user']
                    edited_password = request.POST['edited_password']
                    cursor.execute("UPDATE credentials SET service = ?, description = ?, username = ?, password = ? WHERE id = ?", (edited_service, edited_description, edited_user, edited_password, credential_id))
                    conn.commit()
                    logger.info('Updated credential in vault %s', profile.name)
                    save_database(vault_path, temp_vault, cipher)
                    form = CredentialForm(None)

                cursor.execute("SELECT id, service, description, username, password FROM credentials")
                credentials = cursor.fetchall()


    except Exception as e:
        logger.error("Error decrypting or loading the vault: %s", e)
        return redirect('/')        

    return render(request, 'core/profile_accessed.html', {
        'profile': profile,
        'credentials': credentials,
        'form': form
    })

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

def admin_gate(request):
    logger.info('Entered admin gate')
    if request.method == 'POST':
        password = request.POST.get('admin_password')
        if password == settings.ADMIN_VAULT_PASSWORD:
            logger.info('Admin "logged" in')
            request.session['admin_authenticated'] = True
            return redirect('create_profile')
        else:
            logger.error('Invalid admin password')
            return render(request, 'core/admin_gate.html', {'error': 'Invalid admin password'})
    
    return render(request, 'core/admin_gate.html')

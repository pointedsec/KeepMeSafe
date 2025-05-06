from django.shortcuts import render, redirect
from core.forms import LoginProfileForm
import logging
from core.models import Profile
from core.utils.encrypted_actions import gen_master_key, check_master_key
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
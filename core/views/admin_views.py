from django.shortcuts import render, redirect
from django.conf import settings
import logging
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

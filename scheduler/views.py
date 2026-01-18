from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
import os
import logging

logger = logging.getLogger(__name__)

@csrf_exempt  # ← 外部からのPOSTなのでCSRF除外
@require_POST
def run_trail_sync(request):
    # Cloud Schedulerからのトークン確認
    auth_header = request.headers.get('Authorization', '')
    expected_token = f"Bearer {os.environ.get('SCHEDULER_SECRET')}"
    
    if auth_header != expected_token:
        logger.warning(f"Unauthorized scheduler request from {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({'error': 'unauthorized'}, status=401)
    
    try:
        logger.info("Starting trail_sync command via scheduler")
        call_command('trail_sync')
        logger.info("trail_sync command completed successfully")
        return JsonResponse({'status': 'success'})
    except Exception as e:
        logger.error(f"trail_sync command failed: {e}")
        return JsonResponse({'error': str(e)}, status=500)
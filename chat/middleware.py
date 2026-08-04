from django.utils import timezone
from .models import UserProfile

class UpdateLastSeenMiddleware:
    """Update user's last_seen timestamp on each request"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                profile.last_seen = timezone.now()
                profile.save(update_fields=['last_seen'])
            except UserProfile.DoesNotExist:
                UserProfile.objects.create(user=request.user)
        
        response = self.get_response(request)
        return response
from accounts.models import Notification

def notifications_processor(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user, is_deleted=False).order_by('-created_at')[:10]
    else:
        notifications = []
    return {'notifications': notifications}

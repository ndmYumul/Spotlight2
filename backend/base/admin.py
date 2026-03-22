from django.contrib import admin
from .models import (
    Building, 
    UserProfile, 
    Reservation, 
    Plan, 
    UserSubscription, 
    Schedule, 
    Notification, 
    ChatMessage, 
)

# Register your models here.
admin.site.register(Building)
admin.site.register(UserProfile)
admin.site.register(Reservation)
admin.site.register(Plan)
admin.site.register(UserSubscription)
admin.site.register(Schedule)
admin.site.register(Notification)
admin.site.register(ChatMessage)
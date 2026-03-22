from rest_framework import serializers
from .models import Building, UserProfile, Reservation, Schedule, Notification, ChatMessage, Plan, UserSubscription
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
import datetime
from django.utils import timezone

class BuildingSerializer(serializers.ModelSerializer):
    _id = serializers.ReadOnlyField()
    slots = serializers.ReadOnlyField()

    class Meta:
        model = Building
        fields = ['_id', 'name', 'description', 'totalSlots', 'maxSlots', 'image', 'createdAt', 'slots']

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ['weekly_schedule', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)
    _id = serializers.SerializerMethodField(read_only=True)
    isAdmin = serializers.SerializerMethodField(read_only=True)
    image = serializers.SerializerMethodField(read_only=True) 
    arrival_hour = serializers.SerializerMethodField(read_only=True)
    isPro = serializers.SerializerMethodField(read_only=True)
    schedule = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['id', '_id', 'username', 'email', 'name', 'isAdmin', 'image', 'arrival_hour', 'isPro', 'schedule']

    def get__id(self, obj):
        return obj.id

    def get_isAdmin(self, obj):
        return obj.is_staff

    def get_name(self, obj):
        name = obj.first_name
        return name if name != '' else obj.email
    
    def get_image(self, obj):
        try:
            return obj.userprofile.image.url
        except:
            return None
        
    def get_arrival_hour(self, obj):
        try:
            return obj.userprofile.arrival_hour
        except:
            return 7

    def get_isPro(self, obj):
        try:
            return obj.is_staff or obj.userprofile.is_pro
        except:
            return obj.is_staff
        
    def get_schedule(self, obj):
        try:
            return ScheduleSerializer(obj.schedule, many=False).data
        except:
            return None

class UserSerializerWithToken(UserSerializer):
    token = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['id', '_id', 'username', 'email', 'name', 'isAdmin', 'image', 'token', 'arrival_hour', 'isPro', 'schedule']

    def get_token(self, obj):
        token = RefreshToken.for_user(obj)
        return str(token.access_token)

class ReservationSerializer(serializers.ModelSerializer):
    _id = serializers.ReadOnlyField()
    buildingName = serializers.ReadOnlyField(source='building.name')
    userName = serializers.SerializerMethodField(read_only=True)
    auto_completed = serializers.ReadOnlyField(source='status_check')

    class Meta:
        model = Reservation
        fields = [
            '_id', 'user', 'userName', 'building', 'buildingName', 
            'date', 'start_hour', 'end_hour', 'is_completed', 'auto_completed'
        ]

    def get_userName(self, obj):
        return obj.user.get_full_name() if obj.user.get_full_name() else obj.user.username

    def get_buildingName(self, obj):
        return obj.building.name if obj.building else "Campus Building"

    def get_is_completed(self, obj):
        return obj.is_completed
    
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'user_text', 'ai_response', 'timestamp']

class PlanSerializer(serializers.ModelSerializer):
        model = Plan
        fields = ['_id', 'name', 'price', 'description', 'stripe_price_id']

class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField(read_only=True)
    plan_details = serializers.SerializerMethodField(read_only=True)
    subscription_status = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserSubscription
        fields = ['_id', 'plan', 'plan_name', 'is_active', 'expire_date']

    def get_plan_name(self, obj):
        return obj.plan.name if obj.plan else "Free Tier"
    
    def get_plan_details(self, obj):
        return obj.plan.description if obj.plan else "Standard campus access."
    
    def get_subscription_status(self, obj):
        try:
            return UserSubscriptionSerializer(obj.usersubscription, many=False).data
        except:
            return {'plan_name': 'Free Tier', 'is_active': False}

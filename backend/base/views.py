# 1. IMPORTS
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from django.http import Http404, JsonResponse
import uuid
import traceback
from django.utils import timezone
from datetime import timedelta, date
import datetime
from django.db.models import F
from django.db import transaction

from .models import Building, UserProfile, Reservation, Schedule, Notification
from .serializers import (
    BuildingSerializer, 
    UserSerializer, 
    UserSerializerWithToken, 
    ReservationSerializer,
    ScheduleSerializer,
    NotificationSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# 2. ROUTES
@api_view(['GET'])
def getRoutes(request):
    routes = [
        '/api/buildings/',
        '/api/buildings/create/',
        '/api/buildings/upload/',
        '/api/buildings/<id>/reviews/',
        '/api/buildings/top/',
        '/api/buildings/<id>/',
        '/api/buildings/delete/<id>/',
        '/api/buildings/update/<id>/',
        '/api/users/login/',
        '/api/users/register/',
        '/api/users/profile/',
    ]
    return Response(routes)

# 3. AUTHENTICATION & JWT
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        serializer = UserSerializerWithToken(self.user).data
        for k, v in serializer.items():
            data[k] = v
        return data
    
class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
    permission_classes = [AllowAny]

@api_view(['POST'])
@permission_classes([AllowAny])
def registerUser(request):
    data = request.data
    try:
        user = User.objects.create(
            first_name=data['name'],
            username=data['email'], 
            email=data['email'],
            password=make_password(data['password'])
        )
        serializer = UserSerializerWithToken(user, many=False)
        return Response(serializer.data)
    except Exception as e:
        if User.objects.filter(email=data['email']).exists():
            return Response({'detail': 'User with this email already exists'}, status=400)
        return Response({'detail': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([AllowAny]) 
def auth_user(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        user = User.objects.get(username=username)
        if user.check_password(password):
            serializer = UserSerializerWithToken(user).data
            return Response(serializer)
        else:
            return Response({'detail': 'Invalid credentials'}, status=401)
    except User.DoesNotExist:
        return Response({'detail': 'User not found'}, status=404)
    except Exception as e:
        traceback.print_exc()
        return Response({'detail': str(e)}, status=500)

# 4. USER PROFILE MANAGEMENT
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserProfile(request):
    user = request.user
    serializer = UserSerializer(user, many=False)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateUserProfile(request):
    user = request.user
    data = request.data
    
    user.first_name = data.get('name', user.first_name)
    user.email = data.get('email', user.email)
    user.username = data.get('email', user.username) 

    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if 'isPro' in data:
        profile.is_pro = data['isPro']
    
    if 'preferences' in data:
        profile.preferences = data['preferences']
        
    if 'arrival_hour' in data:
        profile.arrival_hour = data.get('arrival_hour')
        
    profile.save()

    password = data.get('password')
    if password and password != '':
        user.password = make_password(password)

    user.save()
    
    serializer = UserSerializerWithToken(user, many=False)
    return Response(serializer.data)

# 5. USER MANAGEMENT (ADMIN ONLY)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def getUsers(request):
    try:
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([IsAdminUser])
def createUser(request):
    try:
        temp_id = str(uuid.uuid4())[:8] 
        user = User.objects.create(
            first_name='New Student',
            username=f'newuser_{temp_id}',
            email=f'temp_{temp_id}@spotlight.com',
            password=make_password('password123')
        )
        serializer = UserSerializer(user, many=False)
        return Response(serializer.data)
    except Exception as e:
        return Response({'detail': f'Error creating user: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateUser(request, pk):
    try:
        user = User.objects.get(id=pk)
        data = request.data
        user.first_name = data.get('name', user.first_name)
        user.email = data.get('email', user.email)
        user.username = data.get('email', user.username) 
        user.is_staff = data.get('isAdmin', user.is_staff)

        if 'password' in data and data['password'] != '':
            user.password = make_password(data['password'])
        user.save()

        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.is_pro = data.get('isPro', profile.is_pro)
        if 'arrival_hour' in data:
            profile.arrival_hour = data.get('arrival_hour')
        profile.save()

        serializer = UserSerializer(user, many=False)
        return Response(serializer.data)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def deleteUser(request, pk):
    userForDeletion = User.objects.get(id=pk)
    userForDeletion.delete()
    return Response('User was deleted')

@api_view(['GET'])
@permission_classes([IsAdminUser])
def getUserById(request, pk):
    try:
        user = User.objects.get(id=pk)
        serializer = UserSerializer(user, many=False)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({'detail': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)
    
# 6. BUILDING MANAGEMENT
@api_view(['GET'])
def getBuildings(request):
    buildings = Building.objects.all()
    serializer = BuildingSerializer(buildings, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getBuilding(request, pk):
    if pk == 'undefined' or not pk:
        return Response({'detail': 'A valid Building ID was not provided'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        building = Building.objects.get(_id=pk)
        serializer = BuildingSerializer(building, many=False)
        return Response(serializer.data)
    except (Building.DoesNotExist, ValueError):
        return Response({'detail': 'Building not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def createBuilding(request):
    try:
        building = Building.objects.create(
            user=request.user,
            name='New Building Name',
            description='Edit this description...',
            totalSlots=0 
        )
        serializer = BuildingSerializer(building, many=False)
        return Response(serializer.data)
    except Exception as e:
        return Response({'detail': f'Create Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateBuilding(request, pk):
    try:
        building = Building.objects.get(_id=pk)
        data = request.data
        
        building.name = data.get('name', building.name)
        building.description = data.get('description', building.description)
        
        if data.get('maxSlots') is not None:
            new_max = int(data.get('maxSlots'))
            building.maxSlots = new_max
            
            building.totalSlots = new_max

        if data.get('totalSlots') is not None:
            building.totalSlots = int(data.get('totalSlots'))

        building.save()
        
        serializer = BuildingSerializer(building, many=False)
        return Response(serializer.data)
        
    except Building.DoesNotExist:
        return Response({'detail': 'Building not found'}, status=404)
    except Exception as e:
        return Response({'detail': str(e)}, status=400)

@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def deleteBuilding(request, pk):
    try:
        building = Building.objects.get(_id=pk)
        building.delete()
        return Response({'detail': 'Building was successfully deleted'}, status=status.HTTP_200_OK)
    except Building.DoesNotExist:
        return Response({'detail': 'Building not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'detail': f'Delete Error: {str(e)}'}, status=500)
    
@api_view(['GET'])
def getBuildingAnalytics(request, pk):
    building = get_object_or_404(Building, _id=pk)
    today = timezone.now().date()
    
    reservations = Reservation.objects.filter(building=building, date=today)
    
    hourly_counts = [0] * 24
    for res in reservations:
        for hour in range(res.start_hour, res.end_hour):
            if 0 <= hour < 24:
                hourly_counts[hour] += 1
                
    return Response({'hourly_occupancy': hourly_counts})

# 7. IMAGE & FILE UPLOADS
@api_view(['POST'])
@permission_classes([AllowAny])
def uploadImage(request):
    data = request.data
    building_id = data.get('building_id')
    user_id = data.get('user_id')
    image_file = request.FILES.get('image')

    if building_id:
        try:
            building = Building.objects.get(_id=building_id)
            building.image = image_file
            building.save()
            return Response(building.image.url)
        except Building.DoesNotExist:
            return Response({'detail': 'Building not found'}, status=404)

    if user_id and image_file:
        try:
            user = User.objects.get(id=user_id)
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.image = image_file
            profile.save()
            return Response(profile.image.url)
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=404)

    return Response('No valid ID (building_id or user_id) provided', status=400)

# 8. RESERVATION MANAGEMENT
@api_view(['GET'])
@permission_classes([IsAdminUser])
def getReservations(request):
    try:
        reservations = Reservation.objects.all()
        serializer = ReservationSerializer(reservations, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getMyReservations(request):
    user = request.user
    reservations = user.reservation_set.all() 
    serializer = ReservationSerializer(reservations, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createReservation(request):
    try:
        user = request.user
        data = request.data
        building = Building.objects.get(_id=data.get('building_id'))
        
        if building.totalSlots <= 0:
            return JsonResponse({'error': 'This building is currently full.'}, status=400)
            
        reservation = Reservation.objects.create(
            user=user, building=building, date=data.get('date'),
            start_hour=data.get('start_hour'), end_hour=data.get('end_hour')
        )
        
        if building.totalSlots > 0:
            building.totalSlots -= 1
            building.save()
        
            create_user_notification(user, "Spot Secured", f"You have successfully reserved at {building.name}.", "info")
            return Response({'message': 'Reservation successful'})

        else:
            return Response({'detail': 'No slots available'}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateReservation(request, pk):
    try:
        reservation = get_object_or_404(Reservation, _id=pk, user=request.user)
        data = request.data
        
        reservation.start_hour = data.get('start_hour', reservation.start_hour)
        reservation.end_hour = data.get('end_hour', reservation.end_hour)
        reservation.date = data.get('date', reservation.date)
        
        if 'building_id' in data:
            new_building = get_object_or_404(Building, _id=data.get('building_id'))
            reservation.building = new_building
            
        reservation.save() 

        serializer = ReservationSerializer(reservation, many=False)
        return Response(serializer.data)
        
    except Exception as e:
        return Response({'detail': f'Update Error: {str(e)}'}, 
                        status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deleteReservation(request, pk):
    try:
        user = request.user
        reservation = Reservation.objects.get(_id=pk, user=user)
        building = reservation.building

        if building.totalSlots < building.maxSlots:
            building.totalSlots += 1
            building.save()
        
        create_user_notification(user, "Reservation Cancelled", f"Your booking for {building.name} has been removed.", "warning")
        reservation.delete()
        return Response({'message': 'Reservation deleted and slot restored'})
    except Reservation.DoesNotExist:
        return Response({'error': 'Reservation not found'}, status=404)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getReservationById(request, pk):
    try:
        reservation = get_object_or_404(Reservation, _id=pk)
        
        if not request.user.is_staff and reservation.user != request.user:
            return Response({'detail': 'Not authorized to view this reservation'}, 
                            status=status.HTTP_401_UNAUTHORIZED)

        serializer = ReservationSerializer(reservation, many=False)
        return Response(serializer.data)
        
    except (Reservation.DoesNotExist, ValueError):
        return Response({'detail': 'Reservation not found'}, 
                        status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'detail': f'Error: {str(e)}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkScheduleConflict(request):
    user = request.user
    data = request.data
    target_date = data.get('date')
    new_start = int(data.get('start_hour'))
    new_end = int(data.get('end_hour'))

    conflicts = Reservation.objects.filter(
        user=user, 
        date=target_date,
        start_hour__lt=new_end, 
        end_hour__gt=new_start
    )

    if conflicts.exists():
        return Response({
            'has_conflict': True, 
            'detail': 'You already have a spot reserved during these hours.'
        }, status=status.HTTP_409_CONFLICT)
        
    return Response({'has_conflict': False})

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def releaseSpotEarly(request, pk):
    reservation = get_object_or_404(Reservation, _id=pk, user=request.user)
    current_hour = timezone.now().hour
    
    if reservation.start_hour < current_hour < reservation.end_hour:
        reservation.end_hour = current_hour
        reservation.save()
        return Response({'detail': 'Spot released early. Thank you!'})
    
    return Response({'detail': 'Cannot release a spot that is not currently active.'}, status=400)

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def markReservationCompleted(request, pk):
    reservation = get_object_or_404(Reservation, _id=pk)
    reservation.is_completed = True
    reservation.save()
    
    return Response({'detail': 'Reservation marked as completed.'})

# 9. AI SCHEDULE & BULK SYNC LOGIC
@api_view(['POST']) 
@permission_classes([IsAuthenticated])
def update_user_schedule(request):
    try:
        user = request.user
        data = request.data 
        schedule, created = Schedule.objects.get_or_create(user=user)
        weekly_data = data.get('weekly_schedule')
        
        if weekly_data is None:
            return JsonResponse({'error': 'No schedule data provided'}, status=400)

        schedule.weekly_schedule = weekly_data
        schedule.save()
        return JsonResponse({
            'weekly_schedule': schedule.weekly_schedule,
            'updated_at': schedule.updated_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reserve_weekly_schedule(request):
    try:
        user = request.user
        # Get the profile to access the 'preferences' field (Tierlist)
        profile = user.userprofile 
        user_schedule = user.schedule # Assuming a OneToOne relationship
        
        if not user_schedule or not user_schedule.weekly_schedule:
            return JsonResponse({'error': 'No weekly schedule found.'}, status=400)

        created_count = 0
        overflow_notes = []
        
        # We start reserving from tomorrow onwards
        tomorrow = timezone.now().date() + datetime.timedelta(days=1)

        with transaction.atomic():
            # Clear existing future reservations to avoid conflicts
            user.reservation_set.filter(date__gte=tomorrow).delete()

            for item in user_schedule.weekly_schedule:
                if not item.get('active'):
                    continue

                target_day = item.get('day')
                # This matches your empty strings: ""
                manual_choice = item.get('building', '').strip()
                
                # Build the search order
                search_queue = []
                if manual_choice:
                    search_queue.append(manual_choice)
                
                # Add the Tierlist (Samurai Doggo, Pool) as fallbacks
                if profile.preferences:
                    for pref in profile.preferences:
                        if pref not in search_queue:
                            search_queue.append(pref)

                assigned_building = None
                
                # Waterfall search: check each building in the queue
                for b_name in search_queue:
                    building = Building.objects.select_for_update().filter(name__iexact=b_name).first()
                    
                    if building and building.totalSlots > 0:
                        assigned_building = building
                        break
                    elif building:
                        # If the building exists but is full, we move to the next in the queue
                        continue

                if assigned_building:
                    # Logic to find the actual date for the upcoming 'target_day'
                    target_date = get_next_date_for_day(target_day)
                    
                    Reservation.objects.create(
                        user=user,
                        building=assigned_building,
                        date=target_date,
                        start_hour=int(item.get('arrival', '08:00').split(':')[0]),
                        end_hour=int(item.get('departure', '17:00').split(':')[0]),
                        day=target_day
                    )

                    # Update the slot count
                    assigned_building.totalSlots -= 1
                    assigned_building.save()
                    created_count += 1
                    
                    # Log if we had to use a fallback because the first choice was full
                    if manual_choice and assigned_building.name.lower() != manual_choice.lower():
                        overflow_notes.append(f"{target_day}: {manual_choice} full, reserved {assigned_building.name}")
                else:
                    overflow_notes.append(f"{target_day}: No available slots in your preferred buildings.")

        return JsonResponse({
            'message': f'Successfully synced {created_count} days.',
            'overflow_warnings': overflow_notes
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_weekly_reservations(request):
    try:
        user = request.user
        today = timezone.now().date()
        upcoming = Reservation.objects.filter(user=user, date__gte=today)
        count = upcoming.count()
        for res in upcoming:
            building = res.building
            building.totalSlots += 1
            building.save()
            res.delete()
        
        if count > 0:
            create_user_notification(user, "Schedule Purged", f"Successfully cleared {count} spots.", "warning")
        return JsonResponse({'message': f'Cleared {count} reservations.'})
    except Exception as e:
        return JsonResponse({'error': f'Clear failed: {str(e)}'}, status=500)
    
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def clearExpiredReservations(request):
    yesterday = timezone.now().date() - timedelta(days=1)
    expired = Reservation.objects.filter(date__lte=yesterday)
    count = expired.count()
    expired.delete()
    
    return Response({'detail': f'Purged {count} expired records.'})

# 10. NOTIFICATION ENGINE & HELPERS
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getNotifications(request):
    user = request.user
    notifications = Notification.objects.filter(user=user).order_by('-created_at')
    data = [{
        'id': n.id, 'title': n.title, 'message': n.message,
        'notification_type': n.notification_type, 'is_read': n.is_read,
        'created_at': n.created_at
    } for n in notifications]
    return Response(data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def markAsRead(request, pk):
    try:
        notification = Notification.objects.get(id=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

def get_next_date_for_day(day_name):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    try:
        target_day_idx = days.index(day_name.capitalize())
        tomorrow = timezone.now().date() + datetime.timedelta(days=1)
        current_weekday = tomorrow.weekday() # Monday is 0
        
        days_ahead = (target_day_idx - current_weekday + 7) % 7
        
        return tomorrow + datetime.timedelta(days=days_ahead)
    except:
        return None

def create_user_notification(user, title, message, n_type='info'):
    Notification.objects.create(
        user=user, title=title, message=message, notification_type=n_type
    )
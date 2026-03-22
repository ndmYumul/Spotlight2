from base.models import Building, ParkingAssignment
from django.utils import timezone

def automated_assignment_logic(user):
    """
    The 'Brain': Assigns a spot based on Priority and Availability.
    """
    best_building = Building.objects.filter(totalSlots__gt=0).order_by('-totalSlots').first()

    if best_building:
        assignment = ParkingAssignment.objects.create(
            user=user,
            building=best_building,
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2) 
        )
    
        best_building.totalSlots -= 1
        best_building.save()
        
        return best_building.name
    return None
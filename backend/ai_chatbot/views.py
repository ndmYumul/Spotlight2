import os
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from google import genai
from google.genai import types, errors
from google.api_core import exceptions
from dotenv import load_dotenv

# Models
from base.models import Building, ChatMessage, Schedule

# DRF Imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.0-flash"

# Refined System Prompt for a College Student Persona
SYSTEM_PROMPT = """
You are 'Spotlight AI', the Parking Assistant at Holy Angel University. 
Your goal is to assist students using the provided data.

RULES:
- Use simple, college-level vocabulary. 
- Never use emojis. 
- Never use em dashes or en dashes. Use commas or periods instead.
- If a user asks to book or cancel, tell them to use the 'Schedule' or 'Dashboard' tabs.
- If a building is full (0 slots), suggest the next available one from their Tierlist.
- Explain that if their primary building is full, the system automatically checks their next preference.
"""

@csrf_exempt
@api_view(['POST']) 
@permission_classes([IsAuthenticated])
def chat(request):
    user = request.user
    user_message_raw = request.data.get('message', '')
    user_message = user_message_raw.lower()
    user_name = user.first_name if user.first_name else user.username
    now = timezone.now()

    # --- 1. DATA GATHERING ---
    buildings = Building.objects.all()
    user_schedule = Schedule.objects.filter(user=user).first()
    # Get preferences from UserProfile for the Waterfall logic context
    user_prefs = user.userprofile.preferences if hasattr(user, 'userprofile') else []
    
    building_list = [f"{b.name}: {b.slots}/{b.totalSlots} available" for b in buildings]
    building_context = "\n".join(building_list)
    
    tierlist_context = ", ".join(user_prefs) if user_prefs else "No preferences set."
    
    sched_items = []
    if user_schedule and user_schedule.weekly_schedule:
        sched_items = [f"- {item['day']}: {item.get('building') or 'Auto-Assign'} ({item['arrival']}-{item['departure']})" 
                       for item in user_schedule.weekly_schedule if item.get('active')]
    schedule_context = "\n".join(sched_items) if sched_items else "No active schedule set."

    # --- 2. TRY GEMINI ---
    ai_reply = None
    try:
        full_instruction = (
            f"{SYSTEM_PROMPT}\n"
            f"USER: {user_name} | TIME: {now.strftime('%H:%M')}\n"
            f"BUILDING_STATUS:\n{building_context}\n"
            f"USER_SCHEDULE:\n{schedule_context}\n"
            f"USER_TIERLIST_PREFERENCES: {tierlist_context}"
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_message_raw,
            config=types.GenerateContentConfig(
                system_instruction=full_instruction, 
                temperature=0.3
            ),
        )
        ai_reply = response.text

    except (errors.ClientError, exceptions.ResourceExhausted, Exception) as e:
        # --- 3. LOCAL FALLBACK ENGINE (Improved Keyword Matching) ---
        
        # Scenario: Asking about Status or specific building availability
        if any(word in user_message for word in ['status', 'available', 'full', 'parking', 'slots']):
            status_summary = "\n".join([f"• {b}" for b in building_list])
            ai_reply = (f"Hello {user_name}. I am pulling the latest HAU parking data for you. "
                        f"Current status: {status_summary}. "
                        "Is there a building you want to check?")

        # Scenario: Asking about Schedule or current assignments
        elif any(word in user_message for word in ['schedule', 'my', 'routine', 'given', 'assigned', 'thursday', 'monday', 'tuesday', 'wednesday', 'friday']):
            # This branch now catches "Why was I given Pool on Thursday"
            ai_reply = (f"I see you are asking about your assignments, {user_name}. "
                        f"Your current routine is: {schedule_context}. "
                        "If you were given a building that was not your first choice, it is likely "
                        "because your preferred building was full at the time of syncing.")

        # Scenario: Tierlist/Preference explanation
        elif any(word in user_message for word in ['tierlist', 'preference', 'priority', 'rank', 'choice']):
            ai_reply = (f"Your current building priority is: {tierlist_context}. "
                        "The system checks these in order. If the first one is full, it moves to the next.")

        # Default Fallback
        else:
            ai_reply = (f"Hi {user_name}. I am here to help with your HAU parking questions. "
                        "You can ask about parking status, your schedule, or your building preferences. "
                        "How can I help you today?")

    # --- 4. LOG AND RETURN ---
    ChatMessage.objects.create(user=user, user_text=user_message_raw, ai_response=ai_reply)
    return JsonResponse({"reply": ai_reply})

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_chat(request):
    ChatMessage.objects.filter(user=request.user).delete()
    return JsonResponse({"reply": "History cleared!"})
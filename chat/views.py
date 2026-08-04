from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Max
from .models import ChatRoom, Message, UserProfile
from .forms import UserRegisterForm, UserUpdateForm

def register_view(request):
    if request.user.is_authenticated:
        return redirect('chat_list')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save() 
            
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('chat_list')
    else:
        form = UserRegisterForm()
    return render(request, 'chat/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat_list')
    
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('chat_list')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'chat/login.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def chat_list_view(request):
    # Get all users except current user
    users = User.objects.exclude(id=request.user.id).select_related('profile')
    
    # Get user's chat rooms with last message
    chat_rooms = ChatRoom.objects.filter(
        participants=request.user
    ).prefetch_related('participants', 'messages')
    
    # Add last message and other user to each room
    chats = []
    for room in chat_rooms:
        other_user = room.get_other_user(request.user)
        last_message = room.get_last_message()
        chats.append({
            'room': room,
            'other_user': other_user,
            'last_message': last_message
        })
    
    context = {
        'users': users,
        'chats': chats
    }
    return render(request, 'chat/chat_list.html', context)

@login_required
def chat_room_view(request, username):
    other_user = get_object_or_404(User, username=username)
    
    if other_user == request.user:
        messages.error(request, "You cannot chat with yourself!")
        return redirect('chat_list')
    
    # Get or create chat room
    room = ChatRoom.get_or_create_room(request.user, other_user)
    
    # Get messages
    chat_messages = room.messages.all().order_by('timestamp')
    
    # Mark messages as read
    chat_messages.filter(sender=other_user, is_read=False).update(is_read=True)
    
    context = {
        'room': room,
        'other_user': other_user,
        'messages': chat_messages
    }
    return render(request, 'chat/chat_room.html', context)

@login_required
def start_chat_view(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    return redirect('chat_room', username=other_user.username)
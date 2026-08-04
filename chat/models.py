from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

class ChatRoom(models.Model):
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        users = ", ".join([user.username for user in self.participants.all()])
        return f"Chat: {users}"

    def get_other_user(self, current_user):
        """Get the other participant in the chat"""
        return self.participants.exclude(id=current_user.id).first()

    def get_last_message(self):
        return self.messages.order_by('-timestamp').first()

    @staticmethod
    def get_or_create_room(user1, user2):
        """Get existing chat room or create new one"""
        rooms = ChatRoom.objects.filter(participants=user1).filter(participants=user2)
        if rooms.exists():
            return rooms.first()
        
        room = ChatRoom.objects.create()
        room.participants.add(user1, user2)
        return room

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
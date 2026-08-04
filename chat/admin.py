from django.contrib import admin
from .models import UserProfile, ChatRoom, Message

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin view for UserProfile model.
    """
    list_display = ['user', 'online', 'last_seen']
    list_filter = ['online']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['last_seen']

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """
    Admin view for ChatRoom model.
    """
    list_display = ['id', 'get_participants', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    filter_horizontal = ['participants']
    readonly_fields = ['id', 'created_at', 'updated_at']
    search_fields = ['participants__username']

    def get_participants(self, obj):
        """
        Display participants in the list view.
        """
        return ", ".join([user.username for user in obj.participants.all()])
    get_participants.short_description = 'Participants'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin view for Message model.
    """
    list_display = ['id', 'sender', 'get_receiver', 'content_preview', 'timestamp', 'is_read']
    list_filter = ['timestamp', 'is_read', 'sender']
    search_fields = ['sender__username', 'room__participants__username', 'content']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    list_editable = ['is_read']
    list_per_page = 20

    def content_preview(self, obj):
        """
        Return a shortened preview of the message content.
        """
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Message Preview'

    def get_receiver(self, obj):
        """
        Display the other user in the room (the receiver).
        """
        other_user = obj.room.get_other_user(obj.sender)
        return other_user.username if other_user else 'N/A'
    get_receiver.short_description = 'Receiver'
from django.contrib import admin

from .models import App, Job, JobMessage, JobStep, Ticket


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'owner__email')
    ordering = ('-created_at',)


@admin.register(JobStep)
class JobStepAdmin(admin.ModelAdmin):
    list_display = ('job', 'order', 'agent_name', 'created_at')
    ordering = ('job', 'order')
    search_fields = ('job__id', 'agent_name')


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('job', 'owner', 'created_at')
    search_fields = ('job__id', 'owner__email')


@admin.register(JobMessage)
class JobMessageAdmin(admin.ModelAdmin):
    list_display = ('job', 'role', 'sender', 'created_at')
    search_fields = ('job__id', 'sender', 'content')
    ordering = ('-created_at',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'status', 'job', 'assigned_to', 'created_at')
    list_filter = ('type', 'status', 'created_at')
    search_fields = ('title', 'job__id')
    ordering = ('-created_at',)


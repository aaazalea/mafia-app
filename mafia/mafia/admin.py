from models import *
from django.contrib import admin
from django.db.models import get_models,get_app





admin.site.register(Game)
admin.site.register(Player)
admin.site.register(Role)

class DeathAdmin(admin.ModelAdmin):
    list_display = ('murderee','murderer','when')

admin.site.register(Death,DeathAdmin)

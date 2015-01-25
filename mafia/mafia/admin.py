from models import *
from django.contrib import admin
from django.db.models import get_models,get_app
from random import shuffle




admin.site.register(Player)

class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

admin.site.register(Role, RoleAdmin)

class DeathAdmin(admin.ModelAdmin):
    list_display = ('murderee','murderer','when')


admin.site.register(Death,DeathAdmin)


class PlayerInline(admin.TabularInline):
    model = Player
    extra = 0


def pair_gay_knights(modeladmin,request,queryset):
    for g in queryset:
        gay_knights = Player.objects.filter(
            role__name__iexact='gay knight',
            game=g)
        unpaired_gay_knights = list(g for g in gay_knights if not g.gn_partner)
        shuffle(unpaired_gay_knights)
        for i in xrange(len(unpaired_gay_knights)/2):
            GayKnightPair.objects.create(player1=unpaired_gay_knights[i*2],
                                         player2=unpaired_gay_knights[i*2+1])
    modeladmin.message_user(request,"Successfully paired up GNs.")
pair_gay_knights.short_description = "Pair up gay knights"

class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'number_of_players')
    inlines = (PlayerInline,)
    actions = [pair_gay_knights]



admin.site.register(Game, GameAdmin)
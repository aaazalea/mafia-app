from random import shuffle

from models import *
from django.contrib import admin


# admin.site.register(Investigation)
# admin.site.register(Item)


class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

admin.site.register(Role, RoleAdmin)


class DeathAdmin(admin.ModelAdmin):
    list_display = ('murderee', 'murderer', 'when', 'where')


admin.site.register(Death, DeathAdmin)
#from django.utils import strip_tags

class PlayerInline(admin.TabularInline):
    fields = ("user", "role")
    model = Player
    extra = 0
class PlayerAdmin(admin.ModelAdmin):
    def html_image(self, item):
        return "<img src='%s' width='150'>" % (item.photo)
    html_image.short_description = 'Picture'
    html_image.allow_tags = True
    def desc(self, item): 
       return ("(ARCHIVED) " if item.game.archived else "") + item.user.username + ((" (" + item.role.name + ")") if item.role else "")
    desc.short_description = "Player"
    intro = lambda s, p: p.introduction.replace('\n','<br>\n')
    intro.short_description = "Introduction"
    intro.allow_tags = True
    list_display = ('desc', 'html_image', 'intro')
admin.site.register(Player, PlayerAdmin)

class MafiaPowerInline(admin.TabularInline):
    fields = ('power',)
    model = MafiaPower
    extra = 0

class GameAdmin(admin.ModelAdmin):
    # def advance_day(self, request, queryset):
    #     for g in queryset:
    #         g.increment_day()
    #     self.message_user(request, "Activated game(s) successfully")
    #
    # advance_day.short_description = "Activate game"

    def archive_games(self, request, queryset):
        for g in queryset:
            g.active = False
            g.archived = True
            g.save()
        self.message_user(request, "Archived game(s) successfully")

    archive_games.short_description = "Archive selected games"

    # def pair_gay_knights(self, request, queryset):
    #     for g in queryset:
    #         gay_knights = Player.objects.filter(
    #             role__name__iexact='gay knight',
    #             game=g)
    #         unpaired_gay_knights = list(g for g in gay_knights if not g.gn_partner)
    #         shuffle(unpaired_gay_knights)
    #         for i in xrange(len(unpaired_gay_knights) / 2):
    #             GayKnightPair.objects.create(player1=unpaired_gay_knights[i * 2],
    #                                          player2=unpaired_gay_knights[i * 2 + 1])
    #     self.message_user(request, "Successfully paired up GNs.")

    # pair_gay_knights.short_description = "Pair up gay knights"

    list_display = ('name', 'active', 'archived', 'number_of_players', 'number_of_living_players')
    exclude = ('active', 'archived', 'current_day', 'mafia_counts', 'today_start')
    inlines = (PlayerInline, MafiaPowerInline)
    actions = [archive_games]


admin.site.register(Game, GameAdmin)

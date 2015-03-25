from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
import form_urls
import accounts_urls
from settings import PRODUCTION

urlpatterns = patterns('',
                       # Examples:
                       url(r'^$', 'mafia.views.index', name='index'),
                       url(r'^recent-deaths/$', 'mafia.views.recent_deaths', name='recent_deaths'),
                       url(r'^your-role/$', 'mafia.views.your_role', name='your_role'),
                       url(r'^lynch/(?P<day>\d+)', 'mafia.views.daily_lynch', name='daily_lynch'),
                       url(r'^player-intros/$', 'mafia.views.player_intros', name='player_intros'),
                       url(r'^destroy-item/(?P<id>\d+)', 'mafia.views.destroy_item', name='destroy_item'),
                       url(r'^logs/$', 'mafia.views.logs', name='logs'),
                       url(r'^message-seen/(?P<message>.*)$', 'mafia.views.message_seen', name='message_seen'),
                       url(r'^item/(?P<id>\d+)/(?P<password>\d+)', 'mafia.views.item', name='item'),
                       url(r'^past-games/(?P<game_id>\d+)', 'mafia.views.old_logs', name='old_logs'),
                       url(r'^past-games/$', 'mafia.views.past_games', name='past_games'),


                       url(r'^rogue-disarmed/$', 'mafia.views.rogue_disarmed', name='rogue_disarmed'),
                       url(r'^count-the-mafia/$', 'mafia.views.count_the_mafia', name='count_the_mafia'),
                       url(r'^go-desperado/$', 'mafia.views.go_desperado', name='go_desperado'),
                       url(r'^undo-desperado/$', 'mafia.views.undo_desperado', name='undo_desperado'),
                       url(r'^mafia-powers/$', 'mafia.views.mafia_powers', name='mafia_powers'),
                       url(r'^items/$', 'mafia.views.items', name='items'),

                       url(r'^evict-player/(?P<pid>\d+)', 'mafia.views.evict_player', name='evict_player'),
                       url(r'^resurrect-player/(?P<pid>\d+)', 'mafia.views.resurrect_player', name='resurrect_player'),
                       url(r'^advance-day/$', 'mafia.views.advance_day', name='advance_day'),
                       url(r'^end-game/$', 'mafia.views.end_game', name='end_game'),

                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^form/', include(form_urls, namespace='forms')),
                       url(r'^accounts/', include(accounts_urls, namespace='accounts')),
) + ([] if PRODUCTION else static(settings.STATIC_URL, document_root=settings.STATIC_ROOT))

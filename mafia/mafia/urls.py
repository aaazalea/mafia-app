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
                       url(r'^item/(?P<id>\d+)/(?P<password>\d+)', 'mafia.views.item', name='item'),
                       url(r'^go-desperado/$', 'mafia.views.go_desperado', name='go_desperado'),
                       url(r'^player-intros/$', 'mafia.views.player_intros', name='player_intros'),
                       url(r'^mafia-powers/$', 'mafia.views.mafia_powers', name='mafia_powers'),

                       url(r'^end-game/$', 'mafia.views.end_game', name='end_game'),
                       url(r'^evict-player/(?P<pid>\d+)', 'mafia.views.evict_player', name='evict_player'),
                       url(r'^resurrect-player/(?P<pid>\d+)', 'mafia.views.resurrect_player', name='resurrect_player'),
                       url(r'^advance-day/$', 'mafia.views.advance_day', name='advance_day'),

                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^form/', include(form_urls)),
                       url(r'^accounts/', include(accounts_urls)),
) + (() if PRODUCTION else static(settings.STATIC_URL, document_root=settings.STATIC_ROOT))

from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin

urlpatterns = patterns('',
                       # Examples:
                       url(r'^$', 'mafia.views.index', name='index'),
                       url(r'^death-report/$', 'mafia.views.death_report', name='death_report'),
                       url(r'^kill-report/$', 'mafia.views.kill_report', name='kill_report'),
                       url(r'^recent-deaths/$', 'mafia.views.recent_deaths', name='recent_deaths'),
                       url(r'^investigation-form/$', 'mafia.views.investigation_form', name='investigation_form'),
                       url(r'^your-role/$', 'mafia.views.your_role', name='your_role'),
                       url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
                       url(r'^accounts/profile/$', 'mafia.views.index', name='index1'),
                       url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name='logout'),
                       url(r'^lynch/(?P<day>\d+)', 'mafia.views.daily_lynch', name='daily_lynch'),
                       url(r'^lynch-vote/$', 'mafia.views.lynch_vote', name='vote'),
                       url(r'^item/(?P<id>\d+)/(?P<password>\d+)', 'mafia.views.item', name='item'),
                       url(r'^go-desperado/$', 'mafia.views.go_desperado', name='go_desperado'),
                       url(r'^admin/', include(admin.site.urls)),
) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

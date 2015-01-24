from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'mafia.views.index', name='index'),
    url(r'^death-report/$', 'mafia.views.death_report', name='death_report'),
    url(r'^kill-report/$', 'mafia.views.death_report', name='death_report'),
    url(r'^recent-deaths/$', 'mafia.views.recent_deaths', name='recent_deaths'),
    url(r'^your-role/$', 'mafia.views.your_role', name='your_role'),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login'),

    url(r'^admin/', include(admin.site.urls)),
)

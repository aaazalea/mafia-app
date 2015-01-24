from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'mafia.views.index', name='index'),
    url(r'^death-report/$', 'mafia.views.death_report',name='death_report'),

    url(r'^admin/', include(admin.site.urls)),
)

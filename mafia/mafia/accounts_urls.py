from django.conf.urls import patterns, url

urlpatterns = patterns('',
                       url(r'^login/$', 'mafia.views.login'),
                       url(r'^profile/$', 'mafia.views.index', name='index1'),
                       url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name='logout'),
)

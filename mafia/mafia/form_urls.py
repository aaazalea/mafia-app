from django.conf.urls import patterns, url

urlpatterns = patterns('',
                       url(r'^death-report/$', 'mafia.views.death_report', name='death_report'),
                       url(r'^kill-report/$', 'mafia.views.kill_report', name='kill_report'),
                       url(r'^investigation/$', 'mafia.views.investigation_form', name='investigation_form'),
                       url(r'^lynch-vote/$', 'mafia.views.lynch_vote', name='vote'),
                       url(r'^mafia-power/$', 'mafia.views.mafia_power_form', name='mafia_power_form'),
                       url(r'^conspiracy_list/$', 'mafia.views.conspiracy_list_form', name='conspiracy_list_form'),
                       url(r'^sign-up/$', 'mafia.views.sign_up', name='sign_up_form')
)

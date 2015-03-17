from django.conf.urls import patterns, url

urlpatterns = patterns('',
                       url(r'^death-report/$', 'mafia.views.death_report', name='death'),
                       url(r'^kill-report/$', 'mafia.views.kill_report', name='kill'),
                       url(r'^investigation/$', 'mafia.views.investigation_form', name='investigation'),
                       url(r'^lynch-vote/$', 'mafia.views.lynch_vote', name='vote'),
                       url(r'^mafia-power/$', 'mafia.views.mafia_power_form', name='mafia_power'),
                       url(r'^conspiracy_list/$', 'mafia.views.conspiracy_list_form', name='conspiracy_list'),
                       url(r'^sign-up/$', 'mafia.views.sign_up', name='sign_up'),
                       url(r'^ic-reveal/$', 'mafia.views.ic_reveal', name='ic_reveal')
)

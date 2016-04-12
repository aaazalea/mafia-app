from django.conf.urls import patterns, url

urlpatterns = patterns('',
                       url(r'^death-report/$', 'mafia.views.death_report', name='death'),
                       url(r'^superhero/$', 'mafia.views.superhero_form', name='superhero'),
                       url(r'^kill-report/$', 'mafia.views.kill_report', name='kill'),
                       url(r'^investigation/$', 'mafia.views.investigation_form', name='investigation'),
                       url(r'^group_investigation/$', 'mafia.views.group_investigation_form', name='group_investigation'),
                       url(r'^lynch-vote/$', 'mafia.views.lynch_vote', name='vote'),
                       url(r'^mafia-power/$', 'mafia.views.mafia_power_form', name='mafia_power'),
                       url(r'^conspiracy_list/$', 'mafia.views.conspiracy_list_form', name='conspiracy_list'),
                       url(r'^cynic_list/$', 'mafia.views.cynic_list_form', name='cynic_list'),
                       url(r'^saint_list/$', 'mafia.views.saint_list_form', name='saint_list'),
                       url(r'^sinner_list/$', 'mafia.views.sinner_list_form', name='sinner_list'),
                       url(r'^stalk_target/$', 'mafia.views.stalk_target_form', name='stalk_target'),
                       url(r'^sign-up/$', 'mafia.views.sign_up', name='sign_up'),
                       url(r'^elect/$', 'mafia.views.election', name='elect'),
                       url(r'^ic-reveal/$', 'mafia.views.ic_reveal', name='ic_reveal'),
                       url(r'^hitman-success/$', 'mafia.views.hitman_success', name='hitman_success'),
                       url(r'^cctv-report/$', 'mafia.views.cctv_death_form', name='cctv_death'),
                       url(r'^watchlist/(?P<day>\d+)/$', 'mafia.views.modify_watch_list', name='watchlist')
)

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0013_auto_20150613_2050'),
    ]

    operations = [
        migrations.CreateModel(
            name='CynicList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('day', models.IntegerField()),
                ('backup1', models.ForeignKey(related_name='cynicisms_backup1', to='mafia.Player', null=True)),
                ('backup2', models.ForeignKey(related_name='cynicisms_backup2', to='mafia.Player', null=True)),
                ('backup3', models.ForeignKey(related_name='cynicisms_backup3', to='mafia.Player', null=True)),
                ('cynicized', models.ManyToManyField(related_name='cynicisms', to='mafia.Player')),
                ('drop', models.ForeignKey(related_name='cynicisms_drop', to='mafia.Player', null=True)),
                ('owner', models.ForeignKey(to='mafia.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0009_death_where'),
    ]

    operations = [
        migrations.CreateModel(
            name='LynchVote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time_made', models.DateTimeField()),
                ('day', models.IntegerField()),
                ('lynchee', models.ForeignKey(related_name='lynch_votes_received', to='mafia.Player')),
                ('voter', models.ForeignKey(related_name='lynch_votes_made', to='mafia.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='game',
            name='current_day',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]

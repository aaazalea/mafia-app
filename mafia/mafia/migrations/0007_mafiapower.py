# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0006_player_introduction'),
    ]

    operations = [
        migrations.CreateModel(
            name='MafiaPower',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('day_used', models.IntegerField(null=True)),
                ('power', models.IntegerField(
                    choices=[(1, b'KABOOM!'), (2, b'Scheme'), (3, b'Poison'), (4, b'Set a Trap'),
                             (5, b'Slaughter the Weak'), (6, b'Frame a Townsperson'), (7, b'Plant Evidence'),
                             (8, b'Manipulate the Press'), (9, b'Hire a Hitman'), (10, b'Conscription')])),
                ('other_info', models.IntegerField(null=True)),
                ('comment', models.CharField(max_length=50)),
                ('game', models.ForeignKey(to='mafia.Game')),
                ('target', models.ForeignKey(to='mafia.Player', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

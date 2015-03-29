# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0011_auto_20150329_1101'),
    ]

    operations = [
        migrations.CreateModel(
            name='WatchList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('day', models.IntegerField()),
                ('owner', models.ForeignKey(to='mafia.Player')),
                ('watched', models.ManyToManyField(related_name='watched_by', to='mafia.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0011_auto_20150220_2318'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConspiracyList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('day', models.IntegerField()),
                ('conspired', models.ManyToManyField(related_name='conspiracies', to='mafia.Player')),
                ('owner', models.OneToOneField(to='mafia.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

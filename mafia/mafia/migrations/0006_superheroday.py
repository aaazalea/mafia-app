# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0005_auto_20150325_1440'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuperheroDay',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('secret_identity', models.BooleanField(default=True)),
                ('day', models.IntegerField(null=True)),
                ('owner', models.ForeignKey(to='mafia.Player')),
                ('paranoia', models.ForeignKey(related_name='paranoid_superhero_days', to='mafia.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

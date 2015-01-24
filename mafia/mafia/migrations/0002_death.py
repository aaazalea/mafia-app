# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Death',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('when', models.DateTimeField()),
                ('kaboom', models.BooleanField(default=False)),
                ('murderee', models.OneToOneField(related_name='killer', to='mafia.Player')),
                ('murderer', models.ForeignKey(to='mafia.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

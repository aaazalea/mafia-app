# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0015_auto_20150222_1813'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.CharField(max_length=200)),
                ('anonymous_text', models.CharField(max_length=200, null=True)),
                ('mafia_can_view', models.BooleanField(default=False)),
                ('time', models.DateTimeField()),
                ('game', models.ForeignKey(to='mafia.Game')),
                ('users_can_view', models.ManyToManyField(to='mafia.Player', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

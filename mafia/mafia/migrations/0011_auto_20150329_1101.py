# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0010_auto_20150328_1810'),
    ]

    operations = [
        migrations.CreateModel(
            name='CluePile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('collected', models.BooleanField(default=True)),
                ('initial_size', models.IntegerField(default=0)),
                ('size', models.IntegerField(default=0)),
                ('last_checked', models.DateTimeField(null=True)),
                ('investigator', models.ForeignKey(related_name='clues_found', to='mafia.Player')),
                ('target', models.ForeignKey(related_name='clues_about', to='mafia.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='death',
            name='clue_destroyers',
            field=models.ManyToManyField(related_name='destroyed', to='mafia.Player', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='death',
            name='total_clues',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
    ]

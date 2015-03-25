# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0004_auto_20150323_1922'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='mafia_counts',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='item',
            name='result',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='item',
            name='owner',
            field=models.ForeignKey(blank=True, to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='item',
            name='target',
            field=models.ForeignKey(related_name='items_targeted_by', blank=True, to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='item',
            name='used',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0007_auto_20150325_2148'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='today_start',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='notification',
            name='content',
            field=models.CharField(max_length=200),
            preserve_default=True,
        ),
    ]

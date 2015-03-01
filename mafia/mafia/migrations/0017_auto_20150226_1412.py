# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0016_logitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='logitem',
            name='day_start',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='logitem',
            name='time',
            field=models.DateTimeField(auto_now_add=True),
            preserve_default=True,
        ),
    ]

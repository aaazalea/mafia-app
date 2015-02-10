# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0010_auto_20150201_0308'),
    ]

    operations = [
        migrations.AddField(
            model_name='investigation',
            name='day',
            field=models.IntegerField(default=2),
            preserve_default=False,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0008_auto_20150219_1759'),
    ]

    operations = [
        migrations.AddField(
            model_name='investigation',
            name='result',
            field=models.IntegerField(default=-1),
            preserve_default=True,
        ),
    ]

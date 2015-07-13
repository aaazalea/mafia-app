# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0012_watchlist'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cluepile',
            name='collected',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]

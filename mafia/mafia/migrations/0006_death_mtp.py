# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0005_investigation'),
    ]

    operations = [
        migrations.AddField(
            model_name='death',
            name='mtp',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]

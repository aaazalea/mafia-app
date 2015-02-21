# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0007_mafiapower'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='death',
            name='mtp',
        ),
        migrations.AddField(
            model_name='mafiapower',
            name='state',
            field=models.IntegerField(default=0, choices=[(0, b'Available'), (1, b'Set'), (2, b'Used')]),
            preserve_default=False,
        ),
    ]

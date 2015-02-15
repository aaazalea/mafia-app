# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0002_lynchvote_multiplier'),
    ]

    operations = [
        migrations.RenameField(
            model_name='lynchvote',
            old_name='multiplier',
            new_name='value',
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0004_game_rules_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='game',
            name='rules_url',
            field=models.URLField(),
            preserve_default=True,
        ),
    ]

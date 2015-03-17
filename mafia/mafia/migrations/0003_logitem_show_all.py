# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0002_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='logitem',
            name='show_all',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]

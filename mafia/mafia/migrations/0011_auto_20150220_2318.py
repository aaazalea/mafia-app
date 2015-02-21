# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0010_auto_20150220_2259'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forumusername',
            name='user',
        ),
        migrations.DeleteModel(
            name='ForumUsername',
        ),
    ]

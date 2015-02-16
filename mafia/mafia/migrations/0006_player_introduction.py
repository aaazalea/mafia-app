# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0005_auto_20150215_1354'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='introduction',
            field=models.TextField(
                default="Hello, I'm playing mafia and this is an example of an absolutely horrible introduction."),
            preserve_default=False,
        ),
    ]

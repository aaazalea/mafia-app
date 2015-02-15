# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0003_auto_20150214_2352'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='rules_url',
            field=models.TextField(
                default='https://docs.google.com/document/d/1eF6dkGREzLl_idu7-Xm4_6v3xNJnDTL1U9CZbV4txgY/edit#'),
            preserve_default=False,
        ),
    ]

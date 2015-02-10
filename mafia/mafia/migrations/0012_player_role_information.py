# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0011_investigation_day'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='role_information',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
    ]

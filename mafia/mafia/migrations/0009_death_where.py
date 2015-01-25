# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0008_investigation_guess'),
    ]

    operations = [
        migrations.AddField(
            model_name='death',
            name='where',
            field=models.CharField(default='Wonderland', max_length=100),
            preserve_default=False,
        ),
    ]

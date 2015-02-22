# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):
    dependencies = [
        ('mafia', '0012_conspiracylist'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conspiracylist',
            name='owner',
            field=models.ForeignKey(to='mafia.Player'),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0008_auto_20150327_1749'),
    ]

    operations = [
        migrations.AddField(
            model_name='death',
            name='made_by_don',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='player',
            name='role',
            field=models.ForeignKey(blank=True, to='mafia.Role', null=True),
            preserve_default=True,
        ),
    ]

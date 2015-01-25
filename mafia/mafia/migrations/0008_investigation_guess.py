# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0007_role_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='investigation',
            name='guess',
            field=models.ForeignKey(related_name='investigated', default=0, to='mafia.Player'),
            preserve_default=False,
        ),
    ]

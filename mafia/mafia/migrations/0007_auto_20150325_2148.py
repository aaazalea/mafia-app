# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0006_superheroday'),
    ]

    operations = [
        migrations.AlterField(
            model_name='superheroday',
            name='paranoia',
            field=models.ForeignKey(related_name='paranoid_superhero_days', to='mafia.Player', null=True),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0014_auto_20150222_1307'),
    ]

    operations = [
        migrations.AddField(
            model_name='mafiapower',
            name='user',
            field=models.ForeignKey(related_name='mafiapowers_used_set', to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='mafiapower',
            name='target',
            field=models.ForeignKey(related_name='mafiapowers_targeted_set', to='mafia.Player', null=True),
            preserve_default=True,
        ),
    ]

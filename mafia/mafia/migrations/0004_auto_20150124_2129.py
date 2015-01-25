# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0003_auto_20150124_2110'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gayknightpair',
            name='player1',
            field=models.ForeignKey(related_name='gnp1', to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='gayknightpair',
            name='player2',
            field=models.ForeignKey(related_name='gnp2', to='mafia.Player'),
            preserve_default=True,
        ),
    ]

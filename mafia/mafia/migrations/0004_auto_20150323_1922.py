# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0003_logitem_show_all'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='target',
            field=models.ForeignKey(related_name='items_targeted_by', to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='item',
            name='used',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='item',
            name='owner',
            field=models.ForeignKey(to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='lynchvote',
            name='lynchee',
            field=models.ForeignKey(related_name='lynch_votes_received', to='mafia.Player', null=True),
            preserve_default=True,
        ),
    ]

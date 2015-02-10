# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0012_player_role_information'),
    ]

    operations = [
        migrations.AddField(
            model_name='death',
            name='day',
            field=models.IntegerField(default=3),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='investigation',
            name='investigation_type',
            field=models.CharField(default=b'IN', max_length=2, choices=[(b'GN', b'Gay Knight'), (b'IN', b'Investigator'), (b'SH', b'Superhero'), (b'MY', b'Mayoral'), (b'PO', b'Police Officer'), (b'DE', b'Desperado')]),
            preserve_default=True,
        ),
    ]

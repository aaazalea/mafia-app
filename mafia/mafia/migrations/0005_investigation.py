# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0004_auto_20150124_2129'),
    ]

    operations = [
        migrations.CreateModel(
            name='Investigation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('investigation_type', models.CharField(default=b'IN', max_length=2, choices=[(b'GN', b'Gay Knight'), (b'IN', b'Investigator'), (b'SH', b'Superhero'), (b'MY', b'Mayoral'), (b'PO', b'Police Officer')])),
                ('death', models.ForeignKey(to='mafia.Death')),
                ('investigator', models.ForeignKey(to='mafia.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]

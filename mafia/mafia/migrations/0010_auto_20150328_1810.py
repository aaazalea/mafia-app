# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0009_auto_20150328_1138'),
    ]

    operations = [
        migrations.AddField(
            model_name='conspiracylist',
            name='backup1',
            field=models.ForeignKey(related_name='conspiracies_backup1', to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='conspiracylist',
            name='backup2',
            field=models.ForeignKey(related_name='conspiracies_backup2', to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='conspiracylist',
            name='backup3',
            field=models.ForeignKey(related_name='conspiracies_backup3', to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='conspiracylist',
            name='drop',
            field=models.ForeignKey(related_name='conspiracies_drop', to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='item',
            name='type',
            field=models.CharField(max_length=2, choices=[(b'TA', b'Taser'), (b'SH', b'Shovel'), (b'ME', b'Medkit'), (b'MI', b'Microphone'), (b'RE', b'Receiver'), (b'TV', b'CCTV'), (b'CM', b'Camera')]),
            preserve_default=True,
        ),
    ]

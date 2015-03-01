# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mafia', '0013_auto_20150221_1154'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='photo',
            field=models.TextField(default='https://upload.wikimedia.org/wikipedia/commons/3/37/No_person.jpg'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='player',
            unique_together=set([('game', 'user')]),
        ),
    ]

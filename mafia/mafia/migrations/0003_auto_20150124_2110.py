# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mafia', '0002_death'),
    ]

    operations = [
        migrations.CreateModel(
            name='GayKnightPair',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('player1', models.ForeignKey(related_name='gnp1', to=settings.AUTH_USER_MODEL)),
                ('player2', models.ForeignKey(related_name='gnp2', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='death',
            name='murderee',
            field=models.OneToOneField(to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='death',
            name='murderer',
            field=models.ForeignKey(related_name='kills', to='mafia.Player'),
            preserve_default=True,
        ),
    ]

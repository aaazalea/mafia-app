# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('mafia', '0013_auto_20150206_2047'),
    ]

    operations = [
        migrations.CreateModel(
            name='ForumUsername',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=100)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField()),
                ('type', models.CharField(max_length=2, choices=[(b'TA', b'Taser'), (b'SH', b'Shovel'), (b'ME', b'Medkit'), (b'MI', b'Microphone'), (b'RE', b'Receiver')])),
                ('game', models.ForeignKey(to='mafia.Game')),
                ('owner', models.ForeignKey(to='mafia.Player')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='game',
            name='archived',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='death',
            name='murderer',
            field=models.ForeignKey(related_name='kills', to='mafia.Player', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='game',
            name='active',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]

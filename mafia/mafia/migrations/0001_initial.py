# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Death',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('when', models.DateTimeField()),
                ('kaboom', models.BooleanField(default=False)),
                ('where', models.CharField(max_length=100)),
                ('mtp', models.BooleanField(default=False)),
                ('day', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ElectedRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
                ('description', models.TextField(blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
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
            name='Game',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('active', models.BooleanField(default=False)),
                ('archived', models.BooleanField(default=False)),
                ('name', models.CharField(max_length=30)),
                ('current_day', models.IntegerField(default=0)),
                ('god', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GayKnightPair',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Investigation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('day', models.IntegerField()),
                ('investigation_type', models.CharField(default=b'IN', max_length=2,
                                                        choices=[(b'GN', b'Gay Knight'), (b'IN', b'Investigator'),
                                                                 (b'SH', b'Superhero'), (b'MY', b'Mayoral'),
                                                                 (b'PO', b'Police Officer'), (b'DE', b'Desperado')])),
                ('death', models.ForeignKey(to='mafia.Death')),
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
                ('type', models.CharField(max_length=2,
                                          choices=[(b'TA', b'Taser'), (b'SH', b'Shovel'), (b'ME', b'Medkit'),
                                                   (b'MI', b'Microphone'), (b'RE', b'Receiver')])),
                ('game', models.ForeignKey(to='mafia.Game')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LynchVote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time_made', models.DateTimeField()),
                ('day', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('conscripted', models.BooleanField(default=False)),
                ('role_information', models.IntegerField(null=True, blank=True)),
                ('elected_roles', models.ManyToManyField(to='mafia.ElectedRole', blank=True)),
                ('game', models.ForeignKey(to='mafia.Game')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
                ('evil_by_default', models.BooleanField(default=False)),
                ('description', models.TextField(blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='player',
            name='role',
            field=models.ForeignKey(to='mafia.Role', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='player',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='lynchvote',
            name='lynchee',
            field=models.ForeignKey(related_name='lynch_votes_received', to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='lynchvote',
            name='voter',
            field=models.ForeignKey(related_name='lynch_votes_made', to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='item',
            name='owner',
            field=models.ForeignKey(to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='investigation',
            name='guess',
            field=models.ForeignKey(related_name='investigated', to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='investigation',
            name='investigator',
            field=models.ForeignKey(to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gayknightpair',
            name='player1',
            field=models.ForeignKey(related_name='gnp1', to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='gayknightpair',
            name='player2',
            field=models.ForeignKey(related_name='gnp2', to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='death',
            name='murderee',
            field=models.OneToOneField(to='mafia.Player'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='death',
            name='murderer',
            field=models.ForeignKey(related_name='kills', to='mafia.Player', null=True),
            preserve_default=True,
        ),
    ]

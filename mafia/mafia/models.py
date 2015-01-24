from django.db import models
from django.contrib.auth.models import User
class Game(models.Model):
    god = models.ForeignKey(User)
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=30)
    def __str__(self):
        return self.name

class Role(models.Model):
    name = models.CharField(max_length=20)
    evil_by_default = models.BooleanField(default=False)
    def __str__(self):
        return self.name

class Player(models.Model):
    user = models.ForeignKey(User)
    game = models.ForeignKey(Game)
    role = models.ForeignKey(Role,null=True)
    conscripted = models.BooleanField(default=False)
    def __str__(self):
        return self.user.username + " (" + self.game.name + ")"
    def is_alive(self):
        return self.death == null



class Death(models.Model):
    murderer = models.ForeignKey(Player)
    when = models.DateTimeField()
    kaboom = models.BooleanField(default=False)
    murderee = models.OneToOneField(Player,related_name='killer')

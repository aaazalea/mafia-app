from django.db import models
from django.contrib.auth.models import User
class Game(models.Model):
    god = models.ForeignKey(User)
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=30)
    def __str__(self):
        return self.name

    def get_number_of_players(self):
        return len(Player.objects.filter(game=self))
    number_of_players = property(get_number_of_players)

    def get_number_of_living_players(self):
        return len(Player.objects.filter(game=self, alive=True))
    number_of_living_players = property(get_number_of_living_players)
class Role(models.Model):
    name = models.CharField(max_length=20)
    evil_by_default = models.BooleanField(default=False)
    def __str__(self):
        return self.name

class Player(models.Model):
    user = models.ForeignKey(User)
    game = models.ForeignKey(Game)
    role = models.ForeignKey(Role, null=True)
    conscripted = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username + " (" + self.game.name + ")"

    def is_alive(self):
        if len(Death.objects.filter(murderee=self)):
            return False
        return True
    alive = property(is_alive)

    def get_gn_partner(self):
        a = GayKnightPair.objects.filter(player1=self)
        if len(a) == 0:
            a = GayKnightPair.objects.filter(player2=self)
            if len(a) == 0:
                return None
            return a.all()[0].player1
        else:
            return a.all()[0].player2

    gn_partner = property(get_gn_partner)

    def additional_info(self):
        if self.role == Role.objects.get(name__iexact='gay knight'):
            if self.gn_partner:
                return "Your Gay Knight partner is "+self.gn_partner.user.username + "."
            else:
                return "Your Gay Knight partner has not been assigned yet."
        elif self.role.name == 'Rogue':
            return "Your first kill day is not currently stored here."
        else:
            return ""

    def can_investigate(self, death):
        return True

class Death(models.Model):
    murderer = models.ForeignKey(Player, related_name='kills')
    when = models.DateTimeField()
    kaboom = models.BooleanField(default=False)
    murderee = models.OneToOneField(Player)

    #Manipulate The Press
    mtp = models.BooleanField(default=False)
    def __str__(self):
        return "%s killed %s (%s)" % (self.murderer.user.username,
                                      self.murderee.user.username,
                                      self.murderer.game)

class GayKnightPair(models.Model):
    player1 = models.ForeignKey(Player, related_name='gnp1')
    player2 = models.ForeignKey(Player, related_name='gnp2')
    def __str__(self):
        return self.player1.user.username + " <3 " + self.player2.user.username

class Investigation(models.Model):
    investigator = models.ForeignKey(Player)
    death = models.ForeignKey(Death)

    INVESTIGATOR = 'IN'
    GAY_KNIGHT = 'GN'
    SUPERHERO = 'SH'
    MAYORAL = 'MY'
    POLICE_OFFICER = 'PO'
    INVESTIGATION_KINDS = (
        (GAY_KNIGHT, "Gay Knight"),
        (INVESTIGATOR, "Investigator"),
        (SUPERHERO, "Superhero"),
        (MAYORAL, "Mayoral"),
        (POLICE_OFFICER,"Police Officer"),
    )

    investigation_type = models.CharField(max_length=2, choices=INVESTIGATION_KINDS, default=INVESTIGATOR)
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
    description = models.TextField(blank=True)
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
                return "Your Gay Knight partner is <b>"+self.gn_partner.user.username + "</b>."
            else:
                return "Your Gay Knight partner has not been assigned yet."
        elif self.role.name == 'Rogue':
            return "Your first kill day is not currently stored here."
        else:
            return ""

    is_evil = lambda self: self.role.evil_by_default or self.conscripted

    def can_investigate(self):
        return True

    def can_make_kills(self):
        if self.role == Role.objects.get(name__iexact='mafia'):
            return True
        elif self.role == Role.objects.get(name__iexact='rogue'):
            # TODO Implement rogue kill day
            return True
        elif self.role == Role.objects.get(name__iexact='vigilante'):
            for kill in self.kills:
                if not kill.murderee.is_evil():
                    return False
                # TODO implement game days
                # if kill.get_day() == Game.get_day():
                #     return False
            return True
        elif self.role == Role.objects.get(name__iexact='gay knight'):
            if not self.gn_partner.is_alive():
                investigations = Investigation.filter(investigator=self)






    def get_username(self):
        return self.user.username
    username = property(get_username)

class Death(models.Model):
    murderer = models.ForeignKey(Player, related_name='kills')
    when = models.DateTimeField()
    kaboom = models.BooleanField(default=False)
    murderee = models.OneToOneField(Player)
    where = models.CharField(max_length=100)
    #Manipulate The Press
    mtp = models.BooleanField(default=False)
    def __str__(self):
        return "%s killed %s (%s)" % (self.murderer.user.username,
                                      self.murderee.user.username,
                                      self.murderer.game)
    def is_investigable(self, investigation_type):
        if investigation_type == Investigation.GAY_KNIGHT:
            return True
        elif self.mtp:
            return True

class GayKnightPair(models.Model):
    player1 = models.ForeignKey(Player, related_name='gnp1')
    player2 = models.ForeignKey(Player, related_name='gnp2')
    def __str__(self):
        return self.player1.user.username + " <3 " + self.player2.user.username

class Investigation(models.Model):
    # TODO Clues
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
    guess = models.ForeignKey(Player,related_name='investigated')

    def is_correct(self):
        # TODO Manipulate the press
        # TODO Investigative powers
        return self.death.murderer == self.guess and self.death.is_investigable(self.investigation_type)
    correct = property(is_correct)
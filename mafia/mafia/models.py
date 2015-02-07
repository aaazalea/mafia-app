from django.db import models
from django.contrib.auth.models import User
from mafia.settings import ROGUE_KILL_WAIT


class Game(models.Model):
    god = models.ForeignKey(User)
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=30)
    current_day = models.IntegerField()

    def __str__(self):
        return self.name

    get_number_of_players = lambda self: len(Player.objects.filter(game=self))
    number_of_players = property(get_number_of_players)

    get_living_players = lambda self: Player.objects.filter(game=self, death=None)
    living_players = property(get_living_players)

    get_number_of_living_players = lambda self: len(self.living_players)
    number_of_living_players = property(get_number_of_living_players)

    def increment_day(self):
        if self.current_day == 0:
            #start the game
            self.active = True
        else:
            if Death.objects.exists(murderer__game=self):
                pass
                # TODO calculate a lynch
            for player in Player.filter(game=self):
                if player.dies_tonight():
                    pass
                    # TODO kill the player
                player.increment_day()






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

    # Nothing:
    #  - Innocent child
    #  - Mafia
    #  - Investigator
    #  - Vigilante

    # TODO conspiracy theorist list

    # Rogue: first kill day
    # Superhero: 1==secret identity, 0==superhero identity
    # Desperado: number of days since going desperado
    # Gay knight: id of partner (perhaps not since this is implemented separately)
    # TODO implement Vampire (not doing this yet because very likely to change -jakob)
    role_information = models.IntegerField(null=True)

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
        elif self.role == Role.objects.get(name__iexact="rogue"):
            next_kill_day = self.role_information
            if self.game.current_day >= self.role_information:
                if not self.kills.exists():
                    can_kill = True
                else:
                    most_recent_kill = self.kills.order_by('-when')[0]
                    last_kill_day = most_recent_kill.day
                    next_kill_day = last_kill_day + ROGUE_KILL_WAIT
                    if next_kill_day < self.game.current_day:
                        can_kill = False
                    else:
                        can_kill = True

            if can_kill:
                return "You are next allowed to kill on <b> day %d</b>." % next_kill_day
            else:
                return "You are currently permitted to make kills."
        else:
            return ""

    is_evil = lambda self: self.role.evil_by_default or self.conscripted

    def can_investigate(self):
        if self.role == Role.objects.get(name__iexact='investigator'):
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.INVESTIGATOR).exists():
                return True
        if self.role == Role.objects.get(name__iexact='superhero'):
            # TODO implement secret identity / superhero identity
            # return not Investigation.exists(day=self.game.current_day-1,
            #   investigator=self,investigation_type=Investigation.SH)
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.SUPERHERO).exists():
                return True
        if self.role == Role.objects.get(name__iexact='Gay knight'):
            #TODO check rules about gay knights - I think it's not actually one investigation per day
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.GAY_KNIGHT).exists():
                if not self.gn_partner.alive:
                    return True
        if self.role == Role.objects.get(name__iexact='Desperado'):
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.DESPERADO).exists():

                if self.role_information:
                    return True
        # TODO implement elected positions
        return False

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

    def lynch_votes_for(self, day):
        return [player for player in Player.objects.filter(game__active=True) if player.lynch_vote_made(day) == self]


    def lynch_vote_made(self, day):
        votes = LynchVote.objects.filter(voter=self, day=day).order_by('-time_made')
        if votes:
            return votes[0].lynchee
        else:
            return None


    def dies_tonight(self):
        # TODO implement poison

        if self.role == Role.objects.get(name__iexact="Desperado"):
            # TODO how many days do desperados live?
            if self.role_information == 2:
                return True
        elif self.role == Role.objects.get(name__iexact="Gay knight"):
            if not self.gn_partner.alive:
                return True
        # elif self.role == Role.objects.get(name__iexact="Prophet")

        return False
    def increment_day(self):
        """Called when the day ends by the Game object. Deaths are handled separately by dies_tonight()"""
        if self.role == Role.objects.get(name__iexact="Desperado"):
            if self.role_information:
                self.role_information += 1
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
    day = models.IntegerField()
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
    day = models.IntegerField()

    INVESTIGATOR = 'IN'
    GAY_KNIGHT = 'GN'
    SUPERHERO = 'SH'
    MAYORAL = 'MY'
    POLICE_OFFICER = 'PO'
    DESPERADO = "DE"
    INVESTIGATION_KINDS = (
        (GAY_KNIGHT, "Gay Knight"),
        (INVESTIGATOR, "Investigator"),
        (SUPERHERO, "Superhero"),
        (MAYORAL, "Mayoral"),
        (POLICE_OFFICER, "Police Officer"),
        (DESPERADO, "Desperado")
    )

    investigation_type = models.CharField(max_length=2, choices=INVESTIGATION_KINDS, default=INVESTIGATOR)
    guess = models.ForeignKey(Player,related_name='investigated')

    def is_correct(self):
        # TODO Manipulate the press
        # TODO Investigative powers
        return self.death.murderer == self.guess and self.death.is_investigable(self.investigation_type)
    correct = property(is_correct)

class LynchVote(models.Model):
    voter = models.ForeignKey(Player, related_name="lynch_votes_made")
    lynchee = models.ForeignKey(Player, related_name="lynch_votes_received")
    time_made = models.DateTimeField()
    day = models.IntegerField()
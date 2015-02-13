import random
from django.db import models
from django.contrib.auth.models import User
from mafia.settings import ROGUE_KILL_WAIT, DESPERADO_DAYS, GAY_KNIGHT_INVESTIGATIONS
from django.utils.datetime_safe import datetime


class Game(models.Model):
    god = models.ForeignKey(User)
    active = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    name = models.CharField(max_length=30)
    current_day = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    get_number_of_players = lambda self: len(self.player_set.all())
    number_of_players = property(get_number_of_players)

    get_living_players = lambda self: self.player_set.filter(game=self, death=None)
    living_players = property(get_living_players)

    get_number_of_living_players = lambda self: len(self.living_players)
    number_of_living_players = property(get_number_of_living_players)

    def increment_day(self):
        if self.current_day == 0:
            # start the game
            self.active = True
        else:
            # If anybody has been killed yet this game
            if Death.objects.filter(murderer__game=self).exists():
                lynches, choices = self.get_lynch(self.current_day)
                for lynched in lynches:
                    Death.objects.create(murderee=lynched, when=datetime.now(), day=self.current_day,
                                         where="Lynch (day %d)" % self.current_day)
            for player in self.living_players:
                why = player.dies_tonight()
                if why:
                    Death.objects.create(murderee=player, when=datetime.now(), where=why, day=self.current_day)
                player.increment_day()

        self.current_day += 1
        self.save()

    def get_lynch(self, day):
        """
        :param day: The day whose lynch is being found
        :return: tuple of actually lynched players,
                 list of tuples (lynchee, num votes)
        """
        # TODO tiebreaker logic
        # TODO mayoral x3
        choices = []
        for player in self.living_players:
            votes = player.lynch_votes_for(day)
            if votes:
                choices.append((player, votes))
        if choices:
            choices.sort(key=lambda c: -len(c[1]))
            lynches = (choices[0][0],)

            return lynches, choices
        else:
            return [], []


class Role(models.Model):
    name = models.CharField(max_length=20)
    evil_by_default = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ElectedRole(models.Model):
    name = models.CharField(max_length=20)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    user = models.ForeignKey(User)
    game = models.ForeignKey(Game)
    role = models.ForeignKey(Role, null=True)
    elected_roles = models.ManyToManyField(ElectedRole, blank=True)
    conscripted = models.BooleanField(default=False)

    # Nothing:
    # - Innocent child
    #  - Mafia
    #  - Investigator
    #  - Vigilante

    # TODO conspiracy theorist list

    # Rogue: first kill day
    # Superhero: 1==secret identity, 0==superhero identity
    # Desperado: number of days since going desperado
    # Gay knight: id of partner (perhaps not since this is implemented separately)
    # TODO implement Vampire (not doing this yet because very likely to change -jakob)
    role_information = models.IntegerField(null=True, blank=True)

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

    def cant_rogue_kill(self):
        """

        :return: False if the rogue can kill now, otherwise the next kill day
        """
        next_kill_day = self.role_information
        if self.game.current_day >= self.role_information:
            if not self.kills.exists():
                return False
            else:
                most_recent_kill = self.kills.order_by('-when')[0]
                last_kill_day = most_recent_kill.day
                next_kill_day = last_kill_day + ROGUE_KILL_WAIT
                if next_kill_day < self.game.current_day:
                    return next_kill_day
                else:
                    return False

    rogue_cant_kill = property(cant_rogue_kill)

    def additional_info(self):
        if self.role == Role.objects.get(name__iexact='gay knight'):
            if self.gn_partner:
                return "Your Gay Knight partner is <b>" + self.gn_partner.user.username + "</b>."
            else:
                return "Your Gay Knight partner has not been assigned yet."
        elif self.role == Role.objects.get(name__iexact="rogue"):
            if self.rogue_cant_kill:
                return "You are currently permitted to make kills."
            else:
                return "You are next allowed to kill on <b> day %d</b>." % self.rogue_cant_kill
        elif self.role == Role.objects.get(name__iexact="desperado"):
            if self.role_information == 0:
                return "You have not gone desperado yet."
            elif self.role_information == 1:
                return "You are going desperado <b>tonight</b>."
            else:
                return "You went desperado on day <b>%d</b>. You die at day end on day <b>%d</b>" % (
                    (self.game.current_day + 1 - self.role_information),
                    (self.game.current_day + 1 + DESPERADO_DAYS - self.role_information))

        else:
            return ""

    is_evil = lambda self: self.role.evil_by_default or self.conscripted

    def get_investigations(self):
        return Investigation.objects.filter(investigator=self)

    investigations = property(get_investigations)

    def can_investigate(self, kind=None, death=None):
        if self.elected_roles.filter(name__iexact='mayor').exists() and (kind == None or kind == Investigation.MAYORAL):
            if not Investigation.objects.filter(investigator=self,
                                                day__gte=self.game.current_day - 1,
                                                investigation_type=Investigation.MAYORAL).exists():
                return True
        if self.role == Role.objects.get(name__iexact='investigator') and (
                        kind == None or kind == Investigation.INVESTIGATOR):
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.INVESTIGATOR).exists():
                return True
        if self.role == Role.objects.get(name__iexact='superhero') and (
                        kind == None or kind == Investigation.SUPERHERO):
            # TODO implement secret identity / superhero identity
            # return not Investigation.exists(day=self.game.current_day-1,
            #   investigator=self,investigation_type=Investigation.SH)
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.SUPERHERO).exists():
                return True
        if self.role == Role.objects.get(name__iexact='Gay knight') and (
                        kind == None or kind == Investigation.GAY_KNIGHT):
            #TODO check rules about gay knights - I think it's not actually one investigation per day
            if not len(Investigation.objects.filter(investigator=self,
                                                    day=self.game.current_day,
                                                    investigation_type=Investigation.GAY_KNIGHT)) >= GAY_KNIGHT_INVESTIGATIONS:
                if not self.gn_partner.alive and death.murderee == self.gn_partner:
                    return True
        if self.role == Role.objects.get(name__iexact='Desperado') and (
                        kind == None or kind == Investigation.DESPERADO):
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.DESPERADO).exists():

                if self.role_information > 1:
                    return True
        # TODO implement police officer
        return False

    def can_make_kills(self):
        if self.role == Role.objects.get(name__iexact='mafia') or self.conscripted:
            return True
        elif self.role == Role.objects.get(name__iexact='rogue'):
            return not self.rogue_cant_kill
        elif self.role == Role.objects.get(name__iexact='vigilante'):
            for kill in self.kills:
                if not kill.murderee.is_evil():
                    return False
                    # TODO implement game days
                    # if kill.get_day() == Game.get_day():
                    # return False
            return True
        elif self.role == Role.objects.get(name__iexact='gay knight'):
            if not self.gn_partner.is_alive():
                investigations = Investigation.objects.filter(investigator=self)

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
            if self.role_information == DESPERADO_DAYS + 1:
                return "Desperation (day %d)" % self.game.current_day
        elif self.role == Role.objects.get(name__iexact="Gay knight"):
            if not self.gn_partner.alive:
                # TODO how many days do GNs live again?
                return "Lovesickness (day %d)" % self.game.current_day
        # elif self.role == Role.objects.get(name__iexact="Prophet")

        return False

    def increment_day(self):
        """Called when the day ends by the Game object. Deaths are handled separately by dies_tonight()"""
        if self.role == Role.objects.get(name__iexact="Desperado"):
            if self.role_information:
                self.role_information += 1

        self.save()

    def get_username(self):
        return self.user.username

    username = property(get_username)


class Death(models.Model):
    murderer = models.ForeignKey(Player, related_name='kills', null=True)
    when = models.DateTimeField()
    kaboom = models.BooleanField(default=False)
    murderee = models.OneToOneField(Player)
    where = models.CharField(max_length=100)

    # Manipulate The Press
    mtp = models.BooleanField(default=False)
    day = models.IntegerField()

    def __str__(self):
        if self.murderer:
            return "%s killed %s (%s)" % (self.murderer.username,
                                          self.murderee.username,
                                          self.murderer.game)
        else:
            return "%s died due to %s" % (self.murderee.username, self.where)

    def is_investigable(self, investigation_type):
        if investigation_type == Investigation.GAY_KNIGHT:
            return True
        elif self.mtp:
            return False
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
    guess = models.ForeignKey(Player, related_name='investigated')

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


class Item(models.Model):
    TASER = "TA"
    SHOVEL = "SH"
    MICROPHONE = "MI"
    RECEIVER = "RE"
    MEDKIT = "ME"

    ITEM_TYPE = (
        (TASER, "Taser"),
        (SHOVEL, "Shovel"),
        (MEDKIT, "Medkit"),
        (MICROPHONE, "Microphone"),
        (RECEIVER, "Receiver"),
    )

    game = models.ForeignKey(Game)
    owner = models.ForeignKey(Player)
    number = models.IntegerField()
    type = models.CharField(max_length=2, choices=ITEM_TYPE)

    def get_password(self):
        if not hasattr(self, "secret"):
            self.secret = "".join(random.choice("1234567890QWERTYUIOPASDFGHJKLZXCVBNM") for i in range(6))
        return self.secret

    password = property(get_password)

    def get_name(self):
        for a, b in Item.ITEM_TYPE:
            if a == self.type:
                return "%s %d" % (b, self.number)
        return "Mystery Item"

    name = property(get_name)

    def __str__(self):
        for a, b in Item.ITEM_TYPE:
            if a == self.type:
                return "%s %d (%s)" % (b, self.number, self.game.name)
        return "????? (Item)"


class ForumUsername(models.Model):
    username = models.CharField(max_length=100)
    user = models.OneToOneField(User)
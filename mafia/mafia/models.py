import random

from django import forms
from django.core.urlresolvers import reverse
from django.db import models
from django.contrib.auth.models import User
from settings import ROGUE_KILL_WAIT, DESPERADO_DAYS, GAY_KNIGHT_INVESTIGATIONS, GN_DAYS_LIVE
from django.utils.datetime_safe import datetime


class Game(models.Model):
    god = models.ForeignKey(User)
    active = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    name = models.CharField(max_length=30)
    current_day = models.IntegerField(default=0)
    rules_url = models.URLField()

    def log(self, message=None, anonymous_message=None, mafia_can_see=False, users_who_can_see=[]):
        if not message:
            message = anonymous_message
        if anonymous_message:
            item = LogItem.objects.create(game=self, text=message, anonymous_text=anonymous_message,
                                          mafia_can_view=mafia_can_see)
        else:
            item = LogItem.objects.create(text=message, mafia_can_view=mafia_can_see, game=self)
        for user in users_who_can_see:
            item.users_can_view.add(user)
        item.save()

    def log_notification(self, message=None, users_who_can_see=[]):
        item = LogItem.objects.create(text=message, mafia_can_view=False, game=self, show_all=False)
        for user in users_who_can_see:
            item.users_can_view.add(user)
        item.save()

    def __str__(self):
        return self.name

    get_number_of_players = lambda self: len(self.player_set.all())
    number_of_players = property(get_number_of_players)

    get_living_players = lambda self: self.player_set.filter(game=self, death=None)
    living_players = property(get_living_players)

    get_number_of_living_players = lambda self: len(self.living_players)
    number_of_living_players = property(get_number_of_living_players)

    def increment_day(self):
        if self.current_day == 0 and not self.active:
            # start the game
            self.active = True
        else:
            # If anybody has been killed yet this game
            if Death.objects.filter(murderer__game=self).exists():
                lynches, choices = self.get_lynch(self.current_day)
                for lynched in lynches:
                    self.kill_day_end(lynched, "Lynch (day %d)" % self.current_day)
                    self.log(anonymous_message="%s was lynched (end day %d)" % (lynched, self.current_day))

            # note that end-of-day deaths happen *after* lynches
            for player in self.living_players:
                why = player.dies_tonight()
                if why:
                    self.kill_day_end(player, why)

                player.increment_day()

            self.current_day += 1
            LogItem.objects.create(anonymous_text="Day %d start" % self.current_day,
                                   text="Day %d start" % self.current_day,
                                   game=self, day_start=self)
        self.save()


    def kill_day_end(self, player, why):
        Death.objects.create(murderee=player, when=datetime.now(), where=why, day=self.current_day)
        self.log(anonymous_message="%s dies of %s (end day %d)" % (player, why, self.current_day))

        # redistribute items
        for item in player.item_set.all():
            recipient = random.choice(self.living_players.all())
            item.owner = recipient
            self.log(anonymous_message="%s redistributed from %s to %s (end day %d)" %
                                       (item.get_name(), player, recipient, self.current_day))
            item.save()

    def has_user(self, user):
        return self.player_set.filter(user=user).exists()

    def get_lynch(self, day):
        """
        :param day: The day whose lynch is being found
        :return: tuple of actually lynched players,
                 list of tuples (lynchee, num votes)
        """
        # TODO tiebreaker logic
        choices = []
        for player in self.player_set.all():
            votes = player.lynch_votes_for(day)
            if votes:
                choices.append((player, votes, sum(v.value for v in votes)))
        if choices:
            choices.sort(key=lambda c: -c[2])
            lynches = (choices[0][0],)

            return lynches, choices
        else:
            return [], []

    def players_in_role_order(self):
        return self.player_set.order_by("role__name").all()


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
    introduction = models.TextField()
    photo = models.TextField()

    # Nothing:
    # - Innocent child
    # - Mafia
    # - Investigator
    # - Vigilante

    SUPERHERO_IDENTITY = 1
    SECRET_IDENTITY = 0
    DESPERADO_INACTIVE = -1
    DESPERADO_ACTIVATING = 0
    # Rogue: first kill day
    # Superhero: 0==secret identity, 1==superhero identity
    # Desperado: number of days since going desperado
    # Gay knight: id of partner (perhaps not since this is implemented separately)
    # TODO implement Vampire (not doing this yet because very likely to change -jakob)
    role_information = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = (('game', 'user'),)


    def __str__(self):
        return self.username

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
        if self.game.current_day >= next_kill_day:
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

    next_rogue_kill_day = property(cant_rogue_kill)

    def additional_info(self):
        if self.role == Role.objects.get(name__iexact='gay knight'):
            if self.gn_partner:
                return "Your Gay Knight partner is <b>" + self.gn_partner.user.username + "</b>."
            else:
                return "Your Gay Knight partner has not been assigned yet."
        elif self.role == Role.objects.get(name__iexact="rogue"):
            if not self.next_rogue_kill_day:
                return "You are currently permitted to make kills."
            else:
                return "You are next allowed to kill on <b> day %d</b>." % self.next_rogue_kill_day
        elif self.role == Role.objects.get(name__iexact="desperado"):
            if self.role_information == Player.DESPERADO_INACTIVE:
                return "You have not gone desperado yet."
            elif self.role_information == Player.DESPERADO_ACTIVATING:
                return "You are going desperado <b>tonight</b>."
            else:
                return "You decided to go desperado on day <b>%d</b>. You die at day end on day <b>%d</b>" % (
                    (self.game.current_day - self.role_information),
                    (self.game.current_day + DESPERADO_DAYS - self.role_information))
        elif self.role == Role.objects.get(name__iexact="mafia"):
            return "The mafia are: <ul>%s</ul>" % "".join(
                "<li>%s</li>" % m.username for m in Player.objects.filter(game=self.game) if m.is_evil())
        elif self.role == Role.objects.get(name__iexact='Conspiracy theorist'):
            today = self.conspiracylist_set.get_or_create(day=self.game.current_day)[0]
            tomorrow = self.conspiracylist_set.filter(day=self.game.current_day + 1)
            if tomorrow.exists():
                tomorrow = tomorrow[0]
            else:
                tomorrow = today
            tablify = lambda consp: ''.join(
                '<td>%s</td>' % d.username for d in
                consp.conspired.all()) if consp.conspired.exists() else "<td>(empty)</td>"
            return '<table class=\'table\'><tr><th colspan=\'100%%\'>Your conspiracy list</th></tr>' \
                   '<tr><th>Today</th>%s</tr><tr><th>Tomorrow</th>%s</tr></table>' % (
                       tablify(today), tablify(tomorrow))

        else:
            return ""

    is_evil = lambda self: self.role.evil_by_default or self.conscripted

    def get_investigations(self):
        return Investigation.objects.filter(investigator=self)

    investigations = property(get_investigations)

    def can_investigate(self, kind=None, death=None):
        if self.elected_roles.filter(name__iexact='mayor').exists() and (kind is None or kind == Investigation.MAYORAL):
            if not Investigation.objects.filter(investigator=self,
                                                day__gte=self.game.current_day - 1,
                                                investigation_type=Investigation.MAYORAL).exists():
                return True
        if self.role == Role.objects.get(name__iexact='investigator') and (
                        kind is None or kind == Investigation.INVESTIGATOR):
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.INVESTIGATOR).exists():
                return True
        if self.role == Role.objects.get(name__iexact='superhero') and (
                        kind is None or kind == Investigation.SUPERHERO):
            # TODO implement secret identity / superhero identity
            # return not Investigation.exists(day=self.game.current_day-1,
            # investigator=self,investigation_type=Investigation.SH)
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.SUPERHERO).exists():
                return True
        if self.role == Role.objects.get(name__iexact='Gay knight') and (
                        kind is None or kind == Investigation.GAY_KNIGHT):
            # TODO check rules about gay knights - I think it's not actually one investigation per day
            if not len(Investigation.objects.filter(investigator=self,
                                                    day=self.game.current_day,
                                                    investigation_type=Investigation.GAY_KNIGHT)) >= \
                    GAY_KNIGHT_INVESTIGATIONS:
                if not self.gn_partner.alive and self.gn_partner.death.murderee == self.gn_partner:
                    return True
        if self.role == Role.objects.get(name__iexact='Desperado') and (
                        kind is None or kind == Investigation.DESPERADO):
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.DESPERADO).exists():

                if self.role_information > Player.DESPERADO_ACTIVATING:
                    return True
        # TODO implement police officer
        return False

    def save(self, *args, **kwargs):
        if self.role_information is None:
            if self.role == Role.objects.get(name__iexact='rogue'):
                self.role_information = random.randint(1, ROGUE_KILL_WAIT + 1)
            if self.role == Role.objects.get(name__iexact='Superhero'):
                self.role_information = Player.SUPERHERO_IDENTITY
            if self.role == Role.objects.get(name__iexact='Desperado'):
                self.role_information = Player.DESPERADO_INACTIVE
        super(Player, self).save(*args, **kwargs)

    def can_make_kills(self):
        if self.role == Role.objects.get(name__iexact='mafia') or self.conscripted:
            return True
        elif self.role == Role.objects.get(name__iexact='rogue'):
            return not self.next_rogue_kill_day
        elif self.role == Role.objects.get(name__iexact='vigilante'):
            for kill in self.kills.all():
                if not (kill.murderee.is_evil() or kill.murderee.role == Role.objects.get(name__iexact='Rogue')):
                    return False
                elif kill.day == self.game.current_day:
                    # can't kill again today
                    return False
            return True
        elif self.role == Role.objects.get(name__iexact='gay knight'):
            if not self.gn_partner.is_alive():
                if Investigation.objects.filter(investigator=self, guess=self.gn_partner.death.murderer).exists():
                    return True
        return False

    def lynch_votes_for(self, day):
        votes = []
        for player in Player.objects.filter(game=self.game):
            pl_vote = player.lynch_vote_made(day)
            if pl_vote:
                if pl_vote.lynchee == self:
                    votes.append(pl_vote)
        return votes

    def lynch_vote_made(self, day):
        votes = LynchVote.objects.filter(voter=self, day=day).order_by('-time_made')
        if votes:
            return votes[0]
        else:
            return None

    def has_ever_lynched(self):
        return LynchVote.objects.filter(voter=self).exists()

    def dies_tonight(self):

        if self.role == Role.objects.get(name__iexact="Desperado"):
            if self.role_information == DESPERADO_DAYS:
                return "Desperation (day %d)" % self.game.current_day
        elif self.role == Role.objects.get(name__iexact="Gay knight"):
            if not self.gn_partner.alive and self.gn_partner.death.day + GN_DAYS_LIVE == self.game.current_day:
                return "Lovesickness (day %d)" % self.game.current_day
        # elif self.role == Role.objects.get(name__iexact="Prophet")

        poisons = MafiaPower.objects.filter(power=MafiaPower.POISON, target=self)
        if poisons.exists():
            poison = poisons[0]
            if poison.day_used == self.game.current_day - 2:
                return "Poisoned on day %d" % poison.day_used

        return False

    def increment_day(self):
        """Called when the day ends by the Game object. Deaths are handled separately by dies_tonight()"""
        if self.role == Role.objects.get(name__iexact="Desperado"):
            if self.role_information >= Player.DESPERADO_ACTIVATING:
                self.role_information += 1
        elif self.role == Role.objects.get(name__iexact="Gay knight"):
            if not self.gn_partner.alive:
                self.notify("Your gay knight partner died yesterday. You MUST attempt to avenge them!")
        poisons = MafiaPower.objects.filter(power=MafiaPower.POISON, target=self)
        if poisons.exists():
            poison = poisons[0]
            if poison.day_used == self.game.current_day:
                self.notify("You've been poisoned! You die at day end on day %d" % (poison.day_used + 2))
        self.save()

    def get_username(self):
        return self.user.username

    username = property(get_username)

    def get_links(self):
        links = [(reverse('forms:death'), "Report your death.")]
        if self.can_make_kills():
            links.append((reverse('forms:kill'), "Report a kill you made"))
        if self.can_investigate():
            links.append((reverse('forms:investigation'), "Make an investigation"))
        if self.role == Role.objects.get(name="Desperado") and self.role_information == Player.DESPERADO_INACTIVE:
            links.append((
                "javascript:if(confirm('Are you sure you want to go desperado?')"
                "==true){window.location.href='%s'}" % reverse(
                    'go_desperado'), "Go desperado"))
        if self.role == Role.objects.get(name__iexact="Conspiracy theorist"):
            links.append((reverse('forms:conspiracy_list'), 'Update your conspiracy list'))
        if self.is_evil():
            links.append((reverse('mafia_powers'), 'Mafia Powers'))
        if self.role == Role.objects.get(name="Rogue"):
            links.append((reverse('rogue_disarmed'), "Report that you were disarmed"))
        if self.role == Role.objects.get(name="Innocent Child"):
            links.append((reverse('forms:ic_reveal'), "Trust someone"))
        return links

    def get_unread_notifications(self):
        return Notification.objects.filter(user=self.user, game=self.game, seen=False).all()

    def get_notifications(self):
        return Notification.objects.filter(user=self.user, game=self.game).all()

    def notify(self, message, bad=True):
        Notification.objects.create(user=self.user, game=self.game, seen=False, content=message, is_bad=bad)
        self.game.log_notification(message="Notification for %s: '%s'" % (self, message), users_who_can_see=[self])


class Death(models.Model):
    murderer = models.ForeignKey(Player, related_name='kills', null=True)
    when = models.DateTimeField()
    kaboom = models.BooleanField(default=False)
    murderee = models.OneToOneField(Player)
    where = models.CharField(max_length=100)
    free = models.BooleanField(default=False)
    day = models.IntegerField()

    def save(self, *args, **kwargs):
        if not self.pk:
            # (if being created)
            traps = MafiaPower.objects.filter(target=self.murderee, state=MafiaPower.SET)
            if traps.exists():
                self.free = True
                for trap in traps:
                    trap.state = MafiaPower.AVAILABLE
                    trap.target = None
                    trap.save()
            if not (self.murderer and self.murderer.is_evil()):
                # TODO does not take into account conscripted innocents making kills with innocent powers
                self.free = True
            kaboom = None
            if self.kaboom and not self.murderer.elected_roles.filter(
                    name__iexact="Police officer").exists():
                if not self.murderer.is_evil():
                    raise Exception("Non-mafia attempt to use a kaboom without being police officer")
                kabooms = MafiaPower.objects.filter(power=MafiaPower.KABOOM, state=MafiaPower.AVAILABLE,
                                                    game__active=True)
                kaboom = kabooms[0]
                kaboom.target = self.murderee
                kaboom.day_used = self.murderee.game.current_day
                kaboom.state = MafiaPower.USED
                kaboom.user = self.murderer
                kaboom.save()
            scheme = None
            if (not self.free) and Death.objects.filter(day=self.day, free=False,
                                                        murderee__game=self.murderee.game).exists():
                schemes = MafiaPower.objects.filter(power=MafiaPower.SCHEME, state=MafiaPower.AVAILABLE)
                scheme = schemes[0]
                scheme.target = self.murderee
                scheme.day_used = self.murderee.game.current_day
                scheme.state = MafiaPower.USED
                scheme.user = self.murderer
                scheme.save()
            if self.murderer:

                if kaboom and scheme:
                    extra_message = " (KABOOM!, Scheme)"
                elif kaboom:
                    extra_message = " (KABOOM!)"
                elif scheme:
                    extra_message = " (Scheme used)"
                else:
                    extra_message = ""
                message = "%s killed %s%s" % (self.murderer, self.murderee, extra_message)
                anon_message = "%s was killed at %s" % (self.murderee, self.where)
                self.murderee.game.log(message=message, anonymous_message=anon_message,
                                       mafia_can_see=self.murderer.is_evil(),
                                       users_who_can_see=[self.murderer, self.murderee])

                if not self.kaboom and self.murderee.has_microphone():
                    # TODO Don
                    for mic in Item.objects.filter(owner=self.murderee, type=Item.MICROPHONE):
                        number = mic.number
                        # TODO should mics transfer upon death?
                        mic.used = self.when
                        if Item.objects.filter(type=Item.RECEIVER, number=number, owner__isnull=False).exists():
                            receiver = Item.objects.get(type=Item.RECEIVER, number=number)
                            Game.log(message="%s has heard from Receiver %d that %s killed %s." % (
                                receiver.owner, number, self.murderee, self.murderer),
                                     users_who_can_see=[receiver.owner])
                            receiver.owner.notify("You hear something from Receiver %d! %s killed %s!" % (
                            number, self.murderer, self.murderee))
                            receiver.used = self.when

        super(Death, self).save(*args, **kwargs)

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
        elif MafiaPower.objects.filter(power=MafiaPower.MANIPULATE_THE_PRESS, target=self.murderee).exists():
            return False
        return True

    def get_shovel_text(self):
        evidence = MafiaPower.objects.filter(power=MafiaPower.PLANT_EVIDENCE, target=self.murderee)
        if evidence.exists():
            return "%s%s" % (
                "Conscripted " if evidence[0].other_info < 0 else "",
                Role.objects.get(id=abs(evidence[0].other_info)).name)
        if self.murderee.conscripted:
            return "Conscripted %s" % self.murderee.role.name
        else:
            return self.murderee.role.name


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

    result = models.IntegerField(default=-1)

    def is_correct(self):
        if self.result == -1:
            self.result = (self.death.murderer == self.guess and self.death.is_investigable(self.investigation_type))

            if self.investigation_type != Investigation.GAY_KNIGHT:
                if MafiaPower.objects.filter(target=self.guess, other_info=self.death.murderee.id,
                                             game=self.death.murderee.game).exists():
                    self.result = True
        return self.result

    correct = property(is_correct)

    def type_name(self):
        for kind, name in Investigation.INVESTIGATION_KINDS:
            if kind == self.investigation_type:
                return name
        return "???????"


class LynchVote(models.Model):
    voter = models.ForeignKey(Player, related_name="lynch_votes_made")
    lynchee = models.ForeignKey(Player, related_name="lynch_votes_received")
    time_made = models.DateTimeField()
    day = models.IntegerField()
    value = models.IntegerField(default=1)

    def __str__(self):
        if self.value == 1:
            return "%s (day %d)" % (self.lynchee, self.day)
        else:
            return "%s x%d (day %d)" % (self.lynchee, self.value, self.day)


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
    owner = models.ForeignKey(Player, null=True)
    number = models.IntegerField()
    type = models.CharField(max_length=2, choices=ITEM_TYPE)
    used = models.DateTimeField(null=True)
    target = models.ForeignKey(Player, null=True, related_name="items_targeted_by")

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

    def use(self, target=None):
        if self.type == Item.SHOVEL and not target.is_alive():
            text = target.death.get_shovel_text()
            Game.log(message="%s shoveled %s and got a result of %s." % (self.owner, target, text),
                     users_who_can_see=[self.owner])
            self.used = datetime()
            self.target = target
            return text
        if self.type == Item.MEDKIT:
            Game.log(message="%s activated a medkit." % (self.owner), users_who_can_see=[self.owner])
            self.used = datetime()
        return None
        if self.type == Item.TASER:
            Game.log(message="%s tased %s." % (self.owner), users_who_can_see=[self.owner, self.target])
            self.used = datetime()
            self.target = target()
        return None


class MafiaPower(models.Model):
    KABOOM = 1
    SCHEME = 2
    POISON = 3
    SET_A_TRAP = 4
    SLAUGHTER_THE_WEAK = 5
    FRAME_A_TOWNSPERSON = 6
    PLANT_EVIDENCE = 7
    MANIPULATE_THE_PRESS = 8
    HIRE_A_HITMAN = 9
    CONSCRIPTION = 10
    MAFIA_POWER_TYPE = [
        (KABOOM, "KABOOM!"),
        (SCHEME, "Scheme"),
        (POISON, "Poison"),
        (SET_A_TRAP, "Set a Trap"),
        (SLAUGHTER_THE_WEAK, "Slaughter the Weak"),
        (FRAME_A_TOWNSPERSON, "Frame a Townsperson"),
        (PLANT_EVIDENCE, "Plant Evidence"),
        (MANIPULATE_THE_PRESS, "Manipulate the Press"),
        (HIRE_A_HITMAN, "Hire a Hitman"),
        (CONSCRIPTION, "Conscription")
    ]

    target = models.ForeignKey(Player, null=True, related_name="mafiapowers_targeted_set")
    day_used = models.IntegerField(null=True)
    power = models.IntegerField(choices=MAFIA_POWER_TYPE)
    user = models.ForeignKey(Player, null=True, related_name="mafiapowers_used_set")
    # No meaning except for:
    # - Poison: set to 1 once the user sees that they've been poisoned.
    # - Frame a townsperson: the id of the player whose death they are framed for
    # - Plant evidence: the id of the role for which evidence is being planted: negative indicates conscripted
    other_info = models.IntegerField(null=True)

    # hitman name for Hire a Hitman
    comment = models.CharField(max_length=50)

    game = models.ForeignKey(Game)

    AVAILABLE = 0
    SET = 1
    USED = 2
    STATES = [
        (AVAILABLE, "Available"),
        (SET, "Set"),
        (USED, "Used")
    ]

    state = models.IntegerField(choices=STATES, default=AVAILABLE)

    def get_power_name(self):
        for a, b in MafiaPower.MAFIA_POWER_TYPE:
            if a == self.power:
                return b

        return "???"

    available = property(lambda self: self.state == MafiaPower.AVAILABLE)

    def can_use_via_form(self):
        return self.power != MafiaPower.KABOOM and self.power != MafiaPower.SCHEME and self.available

    def needs_extra_field(self):
        if self.power == MafiaPower.FRAME_A_TOWNSPERSON:
            return forms.ModelChoiceField(queryset=Player.objects.filter(game__active=True),
                                          label="Whose death do you want to frame on the target?")
        elif self.power == MafiaPower.HIRE_A_HITMAN:
            return forms.CharField(max_length=40, label="Whom are you hiring as a hitman?")
        elif self.power == MafiaPower.PLANT_EVIDENCE:
            choices = []
            for role in Role.objects.all():
                if role.name != "Mafia":
                    choices.append((-role.id, "Conscripted %s" % role.name))
                choices.append((role.id, "%s" % role.name))

            return forms.ChoiceField(choices=choices, label="What role would you like to plant evidence for?")
        elif self.power == MafiaPower.SET_A_TRAP:
            return forms.ModelChoiceField(queryset=Role.objects.all(), label="What is your guess for a role?")
        else:
            return False

    def get_class(self):
        if self.state == MafiaPower.USED:
            return "danger"
        elif self.state == MafiaPower.AVAILABLE:
            return ""

    def __str__(self):
        return self.get_power_name()

    def extra(self):
        """

        :return: interpretation of other_info field
        """
        if self.state == MafiaPower.AVAILABLE:
            return ""
        if self.power == MafiaPower.FRAME_A_TOWNSPERSON:
            return "Framed for %s's death" % Player.objects.get(id=self.other_info)
        elif self.power == MafiaPower.PLANT_EVIDENCE:
            return "Evidence planted for %s%s" % (
                ("Conscripted " if self.other_info < 0 else ""), Role.objects.get(id=abs(self.other_info)))
        else:
            return ""

    def get_log_message(self):
        if self.power == MafiaPower.KABOOM:
            return "%s used a kaboom to kill %s." % (self.user, self.target.death.murderee)
        elif self.power == MafiaPower.SCHEME:
            return "%s used a scheme to kill %s." % (self.user, self.target)
        elif self.power == MafiaPower.POISON:
            return "The mafia poisoned %s." % self.target
        elif self.power == MafiaPower.SET_A_TRAP:
            if self.state == MafiaPower.SET:
                return "The mafia have successfully set a trap on %s." % self.target
            else:
                return "The mafia have failed to set a trap on %s." % self.target
        elif self.power == MafiaPower.SLAUGHTER_THE_WEAK:
            if self.state == MafiaPower.SET:
                return "The mafia have successfully slaughter the weak on %s." % self.target
            else:
                return "The mafia have failed to slaughter the weak on %s." % self.target
        elif self.power == MafiaPower.FRAME_A_TOWNSPERSON:
            return "The mafia frame %s for the death of %s." % (self.target, Player.objects.get(id=self.other_info))
        elif self.power == MafiaPower.PLANT_EVIDENCE:
            return "Mafia have planted evidence on %s as %s%s" % (
                (self.target, "Conscripted " if self.other_info < 0 else "",
                 Role.objects.get(id=abs(int(self.other_info)))))
        elif self.power == MafiaPower.MANIPULATE_THE_PRESS:
            return "The mafia are manipulating the press on the death of %s." % self.target
        elif self.power == MafiaPower.HIRE_A_HITMAN:
            return "The mafia have hired %s as a hitman to kill %s." % (self.comment, self.target)
        elif self.power == MafiaPower.CONSCRIPTION:
            return "%s made %s an offer they couldn't refuse. %s has been conscripted into the mafia." % (
                self.user, self.target, self.target)


class ConspiracyList(models.Model):
    owner = models.ForeignKey(Player)
    conspired = models.ManyToManyField(Player, related_name='conspiracies')
    day = models.IntegerField()


class LogItem(models.Model):
    game = models.ForeignKey(Game)
    text = models.CharField(blank=False, null=False, max_length=200)
    anonymous_text = models.CharField(null=True, max_length=200)
    mafia_can_view = models.BooleanField(default=False)
    users_can_view = models.ManyToManyField(Player, blank=True)
    time = models.DateTimeField(auto_now_add=True)
    day_start = models.BooleanField(default=False)
    show_all = models.BooleanField(default=True)

    def visible_to(self, user):
        if user == self.game.god:
            return self.show_all
        elif self.mafia_can_view and Player.objects.filter(game=self.game, user=user, role__name="Mafia").exists():
            return True
        elif Player.objects.filter(game=self.game, user=user, death__isnull=False).exists():
            return self.show_all
        else:
            return self.users_can_view.filter(user=user).exists()

    def get_text(self, user):
        if self.visible_to(user):
            return self.text
        else:
            return self.anonymous_text

    def is_day_start(self):
        return self.day_start


class Notification(models.Model):
    seen = models.BooleanField(default=False)
    user = models.ForeignKey(User)
    content = models.CharField(max_length=75)
    game = models.ForeignKey(Game)
    is_bad = models.BooleanField(default=True)

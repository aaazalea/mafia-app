import random
import math

from django import forms
from django.core.urlresolvers import reverse
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from settings import ROGUE_KILL_WAIT, DESPERADO_DAYS, GAY_KNIGHT_INVESTIGATIONS, GN_DAYS_LIVE, CLUES_IN_USE, \
    MAYOR_COUNT_MAFIA_TIMES, CONSPIRACY_LIST_SIZE, CONSPIRACY_LIST_SIZE_IS_PERCENT, KABOOMS_REGENERATE, \
    TRAPS_REGENERATE, CYNIC_LIST_SIZE, CYNIC_LIST_SIZE_IS_PERCENT, LYNCH_WORD, LYNCH_VERB
from django.utils.timezone import now

NO_LYNCH = "No " + LYNCH_WORD


class Game(models.Model):
    god = models.ForeignKey(User)
    active = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    name = models.CharField(max_length=30)
    current_day = models.IntegerField(default=0)
    mafia_counts = models.IntegerField(default=0)
    today_start = models.DateTimeField(null=True)

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

    def __str__(self):
        return self.name

    get_number_of_players = lambda self: len(self.player_set.all())
    number_of_players = property(get_number_of_players)

    get_living_players = lambda self: self.player_set.filter(game=self, death=None)
    living_players = property(get_living_players)

    get_number_of_living_players = lambda self: len(self.living_players)
    number_of_living_players = property(get_number_of_living_players)

    def increment_day(self):
        if not self.active and not self.archived:
            # start the game
            self.active = True
            for item in Item.objects.filter(game=self).order_by('type', 'number'):
                self.log(anonymous_message="%s was distributed to %s at game start" % (item.name, item.owner))
        else:
            # If anybody has been killed yet this game
            if Death.objects.filter(murderer__game=self).exists():
                lynches, choices = self.get_lynch(self.current_day)
                for lynched in lynches:
                    self.kill_day_end(lynched, "%s (day %d)" % (LYNCH_WORD, self.current_day), log_message=False)
                    self.log(anonymous_message="%s was %sed (end day %d)" % (lynched, LYNCH_VERB, self.current_day))

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

            if self.mafiapower_set.filter(power=MafiaPower.HIRE_A_HITMAN, state=MafiaPower.SET).exists():
                hitman = self.mafiapower_set.get(power=MafiaPower.HIRE_A_HITMAN, state=MafiaPower.SET)
                hitman.state = MafiaPower.USED
                hitman.save()

        self.today_start = now()
        self.save()

    def kill_day_end(self, player, why, log_message=True):
        Death.objects.create(murderee=player, when=now(), where=why, day=self.current_day)
        if log_message:
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
        # TODO mayor triple vote
        no_lynch_votes = [p.lynch_vote_made(day) for p in self.living_players if
                          p.lynch_vote_made(day) and not p.lynch_vote_made(day).lynchee]
        choices = [(NO_LYNCH, no_lynch_votes, sum(v.value for v in no_lynch_votes))]
        if not choices[0][2]:
            choices = []
        for player in self.player_set.all():
            votes = player.lynch_votes_for(day)
            if votes:
                choices.append((player, votes, sum(v.value for v in votes)))
        if choices:
            choices.sort(key=lambda c: -c[2])
            lynch_value = choices[0][2]
            lynches = tuple(ch[0] for ch in choices if ch[2]==lynch_value)
            if lynches[0] == NO_LYNCH:
                return [], choices
            return lynches, choices
        else:
            return [], []

    def players_in_role_order(self):
        return self.player_set.order_by("role__name").all()

    def elected_people(self):
        for person in self.living_players:
            for role in person.elected_roles.all():
                yield person, role


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
    role = models.ForeignKey(Role, null=True, blank=True)
    elected_roles = models.ManyToManyField(ElectedRole, blank=True)
    conscripted = models.BooleanField(default=False)
    introduction = models.TextField()
    photo = models.TextField()

    # Nothing:
    # - Innocent child
    # - Mafia
    # - Investigator
    # - Vigilante
    # - Superhero

    DESPERADO_INACTIVE = -1
    DESPERADO_ACTIVATING = 0
    # Rogue: first kill day
    # Desperado: number of days since going desperado
    # Gay knight: id of partner (perhaps not since this is implemented separately)
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

    def log(self, message):
        item = LogItem.objects.create(text=message, game=self.game)
        item.users_can_view.add(self)
        item.save()

    def log_notification(self, message=None):
        item = LogItem.objects.create(text=message, game=self.game, show_all=False)
        item.users_can_view.add(self)
        item.save()

    def get_extra_info_for_dead_people(self):
        if not self.is_alive():
            return "Dead"
        if self.role == Role.objects.get(name__iexact="Gay Knight"):
            return "Partner is %s" % self.gn_partner
        elif self.role == Role.objects.get(name__iexact="Rogue"):
            if not self.cant_rogue_kill():
                return "Can kill"
            return "Next kill: day %d" % self.next_rogue_kill_day
        elif self.role == Role.objects.get(name__iexact="desperado"):
            if self.role_information == Player.DESPERADO_ACTIVATING:
                return "Activating tonight"
            elif self.role_information == Player.DESPERADO_INACTIVE:
                return "Inactive desperado"
            else:
                return "Went desperado %d days ago" % self.role_information
        elif self.role == Role.objects.get(name__iexact="vigilante"):
            if self.can_make_kills():
                return "Can kill"
            else:
                return "Used up kill"
        elif self.role == Role.objects.get(name__iexact="Conspiracy theorist"):
            list1 = ", ".join(
                p.username for p in self.conspiracylist_set.get_or_create(day=self.game.current_day)[0].conspired.all())
            if list1:
                return "Conspiracy list: [%s]" % list1
            else:
                return "No conspiracy list"
        elif self.role == Role.objects.get(name__iexact="Cynic"):
            list1 = ", ".join(
                p.username for p in self.cyniclist_set.get_or_create(day=self.game.current_day)[0].cynicized.all())
            if list1:
                return "Cynic list: [%s]" % list1
            else:
                return "No cynic list"
        elif self.role == Role.objects.get(name="Superhero"):
            superhero_day = SuperheroDay.objects.get(owner=self, day=self.game.current_day)
            if superhero_day.superhero_identity:
                return "Superhero identity (paranoia: %s)" % superhero_day.paranoia
            else:
                return "Secret identity"
        else:
            # IC, Investigator
            return ""
            # TODO mafia don

    def item_string(self):
        if self.item_set.exists():
            return ", ".join(item.name for item in self.item_set.all())
        else:
            return ""

    def get_gn_partner(self):
        a = GayKnightPair.objects.filter(player1=self)
        if not a.exists():
            a = GayKnightPair.objects.filter(player2=self)
            if not a.exists():
                return None
            return a.all()[0].player1
        else:
            return a.all()[0].player2

    gn_partner = property(get_gn_partner)

    def cant_rogue_kill(self):
        """

        :return: False if the rogue can kill now, otherwise the next kill day
        """
        first_kill_day = self.role_information
        if self.game.current_day >= first_kill_day:
            if not self.kills.exists():
                return False
            else:
                most_recent_kill = self.kills.order_by('-when')[0]
                last_kill_day = most_recent_kill.day
                next_kill_day = last_kill_day + ROGUE_KILL_WAIT
                if next_kill_day > self.game.current_day:
                    return next_kill_day
                else:
                    return False
        else:
            return first_kill_day

    next_rogue_kill_day = property(cant_rogue_kill)

    def additional_info(self):
        if self.role == Role.objects.get(name__iexact='gay knight'):
            if self.gn_partner:
                return "Your Gay Knight partner is <b>" + self.gn_partner.user.username + "</b>."
            else:
                return "Your Gay Knight partner has not been assigned yet."
        elif self.role == Role.objects.get(name__iexact="rogue"):
            if self.can_make_kills():
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
                # make a copy of today
                tomorrow = ConspiracyList.objects.get(id=today.id)
                tomorrow.id = None
                tomorrow.day += 1
                tomorrow.save()
                for suspect in today.conspired.all():
                    tomorrow.conspired.add(suspect)
                tomorrow.save()

            tablify = lambda consp: ''.join(
                '<td>%s</td>' % d.username for d in
                consp.conspired.all()) if consp.conspired.exists() else "<td>(empty)</td>"
            return '<table class=\'table\'><tr><th colspan=\'100%%\'>Your conspiracy list</th></tr>' \
                   '<tr><th>Today</th>%s</tr><tr><th>Tomorrow</th>%s</tr></table>' % (
                       tablify(today), tablify(tomorrow))
        elif self.role == Role.objects.get(name__iexact='Cynic'):
            today = self.cyniclist_set.get_or_create(day=self.game.current_day)[0]
            tomorrow = self.cyniclist_set.filter(day=self.game.current_day + 1)
            if tomorrow.exists():
                tomorrow = tomorrow[0]
            else:
                # make a copy of today
                tomorrow = CynicList.objects.get(id=today.id)
                tomorrow.id = None
                tomorrow.day += 1
                tomorrow.save()
                for victim in today.cynicized.all():
                    tomorrow.cynicized.add(victim)
                tomorrow.save()
            tablify = lambda cyn: ''.join(
                '<td>%s</td>' % d.username for d in
                cyn.cynicized.all()) if cyn.cynicized.exists() else "<td>(empty)</td>"
            if self.cyniclist_set.filter(day=self.game.current_day - 1).exists() and self.cyniclist_set.get(
                    day=self.game.current_day - 1).cynicism_successful():
                return 'Your cynicism yesterday paid off, and you are invulnerable today.' \
                       '<table class=\'table\'><tr><th colspan=\'100%%\'>Your cynic list</th></tr>' \
                       '<tr><th>Today</th>%s</tr><tr><th>Tomorrow</th>%s</tr></table>' % (
                           tablify(today), tablify(tomorrow))
            else:
                return '<table class=\'table\'><tr><th colspan=\'100%%\'>Your cynic list</th></tr>' \
                       '<tr><th>Today</th>%s</tr><tr><th>Tomorrow</th>%s</tr></table>' % (
                           tablify(today), tablify(tomorrow))
        elif self.role == Role.objects.get(name="Superhero"):
            superhero_day = SuperheroDay.objects.get(owner=self, day=self.game.current_day)
            try:
                sup_yesterday = SuperheroDay.objects.get(owner=self, day=self.game.current_day - 1)
            except SuperheroDay.DoesNotExist:
                sup_yesterday = None
            if sup_yesterday and sup_yesterday.paranoia_successful():
                a = "Immune today by paranoia. "
            else:
                a = ""
            if superhero_day.superhero_identity:
                return a + "Today: superhero identity (paranoia: %s)." % superhero_day.paranoia
            else:
                return a + "Today: secret identity."
        else:
            return ""

    is_evil = lambda self: self.role.evil_by_default or self.conscripted

    is_mafia_don = lambda self: self.elected_roles.filter(name='Don').exists()

    def get_investigations(self):
        return Investigation.objects.filter(investigator=self)

    investigations = property(get_investigations)

    in_superhero_identity = property(
        lambda self: self.superheroday_set.filter(day=self.game.current_day).exists() and self.superheroday_set.get(
            day=self.game.current_day).superhero_identity)

    def killable_by_bang(self, killer=None):
        role_name = self.role.name
        if role_name == "Desperado":
            if self.role_information > Player.DESPERADO_ACTIVATING:
                return False
        elif role_name == "Gay Knight":
            if killer and self.gn_partner == killer and self.investigation_set.filter(guess=killer).exists():
                return False
        elif role_name == 'Superhero':
            try:
                sup_yesterday = SuperheroDay.objects.get(owner=self, day=self.game.current_day - 1)
            except SuperheroDay.DoesNotExist:
                sup_yesterday = None
            if sup_yesterday and sup_yesterday.paranoia_successful():
                return False
        elif role_name == "Conspiracy Theorist":
            if killer:
                if self.conspiracylist_set.filter(day=self.game.current_day, conspired=killer).exists():
                    return False
        elif role_name == 'Cynic':
            try:
                cyn_yesterday = CynicList.objects.get(owner=self, day=self.game.current_day - 1)
            except CynicList.DoesNotExist:
                cyn_yesterday = None
            if cyn_yesterday and cyn_yesterday.cynicism_successful():
                return False
        if Item.objects.filter(used__gt=self.game.today_start, type=Item.MEDKIT, owner=self):
            return False

        return True

    def mic_secured(self):
        for mic in Item.objects.filter(owner=self, type=Item.MICROPHONE, used__isnull=True):
            if Item.objects.filter(type=Item.RECEIVER, number=mic.number, owner__isnull=False, game=self.game).exists():
                receiver = Item.objects.get(type=Item.RECEIVER, number=mic.number, game=self.game)
                if not (receiver.owner.is_evil() or receiver.owner.role == Role.objects.get(name__iexact='Rogue')):
                    return True
        return False

    def can_collect_clues(self, target=None):
        if not CLUES_IN_USE:
            return False
        if target:
            relevant_clues = CluePile.objects.filter(investigator=self, target=target)
            if relevant_clues.exists() and relevant_clues[0].uncheckable():
                return False
            if target.is_alive() or (not MafiaPower.objects.filter(target=target,power=MafiaPower.HIRE_A_HITMAN).exists() and not target.death.murderer):
                return False
        if self.role == Role.objects.get(name__iexact='investigator'):
            return True
        if self.role == Role.objects.get(name__iexact='superhero'):
            if self.superheroday_set.filter(day=self.game.current_day).exists():
                return self.superheroday_set.get(day=self.game.current_day).secret_identity
        if self.role == Role.objects.get(
                name__iexact='Desperado') and self.role_information > Player.DESPERADO_ACTIVATING:
            return True
        return False

    def has_clues_to_investigate(self, target):
        # TODO check this behavior for non-clue games?
        if not CLUES_IN_USE:
            return True
        relevant_clues = CluePile.objects.filter(investigator=self, target=target)
        if relevant_clues.exists():
            return relevant_clues[0].size > 0
        else:
            return False

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
                return (not death) or self.has_clues_to_investigate(death.murderee)
        if self.role == Role.objects.get(name__iexact='superhero') and (
                        kind is None or kind == Investigation.SUPERHERO):
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.SUPERHERO).exists():
                return self.in_superhero_identity and (
                    (not death) or self.has_clues_to_investigate(death.murderee))
        if self.role == Role.objects.get(name__iexact='Gay knight') and (
                        kind is None or kind == Investigation.GAY_KNIGHT) and \
                (death is None or death.murderee == self.gn_partner):
            if not len(Investigation.objects.filter(investigator=self,
                                                    day=self.game.current_day,
                                                    investigation_type=Investigation.GAY_KNIGHT)) >= \
                    GAY_KNIGHT_INVESTIGATIONS:
                if not self.gn_partner.alive and ((not death) or (death.murderee == self.gn_partner)):
                    return True
        if self.role == Role.objects.get(name__iexact='Desperado') and (
                        kind is None or kind == Investigation.DESPERADO):
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.DESPERADO).exists():
                if self.role_information > Player.DESPERADO_ACTIVATING:
                    return (not death) or self.has_clues_to_investigate(death.murderee)
        if self.elected_roles.filter(name__iexact='police officer').exists() and (
                        kind is None or kind == Investigation.POLICE_OFFICER):
            if not Investigation.objects.filter(investigator=self,
                                                day=self.game.current_day,
                                                investigation_type=Investigation.POLICE_OFFICER).exists():
                return (not death) or self.has_clues_to_investigate(death.murderee)
        return False

    def save(self, *args, **kwargs):
        if self.role_information is None:
            if self.role == Role.objects.get(name__iexact='rogue'):
                self.role_information = random.randint(1, ROGUE_KILL_WAIT + 1)
            if self.role == Role.objects.get(name__iexact='Desperado'):
                self.role_information = Player.DESPERADO_INACTIVE
        super(Player, self).save(*args, **kwargs)

    def can_destroy_clue(self, death=None):
        return (self.is_evil() or self.role == Role.objects.get(name__iexact="Rogue")) and (
            not death or (not self in death.clue_destroyers.all()) and death.total_clues > 0)

    def can_make_kills(self):
        if Item.objects.filter(used__gt=self.game.today_start, type=Item.TASER, target=self).exists():
            return False
        if self.role == Role.objects.get(name__iexact='mafia') or self.conscripted:
            return True
        elif self.role == Role.objects.get(name__iexact='rogue'):
            if not self.cant_rogue_kill():
                return True

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
            if (not self.gn_partner.alive) and self.gn_partner.death.day + GN_DAYS_LIVE == self.game.current_day:
                return "Lovesickness (day %d)" % self.game.current_day

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
        elif self.role == Role.objects.get(name="Superhero"):
            if not SuperheroDay.objects.filter(owner=self, day=self.game.current_day + 1):
                SuperheroDay.objects.create(owner=self, day=self.game.current_day + 1, secret_identity=True)
        poisons = MafiaPower.objects.filter(power=MafiaPower.POISON, target=self)
        if poisons.exists():
            poison = poisons[0]
            if poison.day_used == self.game.current_day:
                self.notify("You've been poisoned! You die at day end on day %d" % (poison.day_used + 2))

        if self.role == Role.objects.get(name="Conspiracy Theorist"):
            try:
                consp_list = self.conspiracylist_set.get(day=self.game.current_day + 1)
            except ConspiracyList.DoesNotExist:
                today = self.conspiracylist_set.get_or_create(day=self.game.current_day)[0]
                tomorrow = ConspiracyList.objects.get(id=today.id)
                tomorrow.id = None
                tomorrow.day += 1
                tomorrow.save()
                for suspect in today.conspired.all():
                    tomorrow.conspired.add(suspect)
                tomorrow.save()
                consp_list = tomorrow


            count_dead = 0
            if CONSPIRACY_LIST_SIZE_IS_PERCENT:
                list_size = math.ceil(self.game.number_of_living_players * 0.01 * CONSPIRACY_LIST_SIZE)
            else:
                list_size = CONSPIRACY_LIST_SIZE

            if list_size < len(consp_list.conspired.all()):
                # TODO When too many people die in a day you may need to drop more than 1 person from your list
                consp_list.conspired.remove(consp_list.drop)
                # Gives the set of possible backups who are still alive
                backups = [person for person in
                           (consp_list.drop, consp_list.backup1, consp_list.backup2, consp_list.backup3) if
                           (person and person.is_alive())]
                consp_list.drop = None
            else:
                backups = [person for person in (consp_list.backup1, consp_list.backup2, consp_list.backup3) if
                           (person and person.is_alive())]

            conspiratees = list(consp_list.conspired.all())

            for conspiratee in conspiratees:
                if not conspiratee.is_alive():
                    consp_list.conspired.remove(conspiratee)
                    if count_dead < len(backups):
                        consp_list.conspired.add(backups[count_dead])
                        count_dead += 1

            if not (consp_list.drop and consp_list.drop.is_alive()):
                consp_list.drop = consp_list.conspired.first()
            (consp_list.backup1, consp_list.backup2, consp_list.backup3) = (backups + [None, None, None])[
                                                                           count_dead:count_dead + 3]

            consp_list.save()

        if self.role == Role.objects.get(name="Cynic"):
            try:
                cyn_list = self.cyniclist_set.get(day=self.game.current_day + 1)
            except CynicList.DoesNotExist:
                today = self.cyniclist_set.get_or_create(day=self.game.current_day)[0]
                tomorrow = CynicList.objects.get(id=today.id)
                tomorrow.id = None
                tomorrow.day += 1
                tomorrow.save()
                for victim in today.cynicized.all():
                    tomorrow.cynicized.add(victim)
                tomorrow.save()

                cyn_list = tomorrow

            count_dead = 0
            if CYNIC_LIST_SIZE_IS_PERCENT:
                list_size = math.ceil(self.game.number_of_living_players * 0.01 * CYNIC_LIST_SIZE)
            else:
                list_size = CYNIC_LIST_SIZE

            if list_size < len(cyn_list.cynicized.all()):
                # TODO When too many people die in a day you may need to drop more than 1 person from your list
                cyn_list.cynicized.remove(cyn_list.drop)
                # Gives the set of possible backups who are still alive
                backups = [person for person in
                           (cyn_list.drop, cyn_list.backup1, cyn_list.backup2, cyn_list.backup3) if
                           (person and person.is_alive())]
                cyn_list.drop = None
            else:
                backups = [person for person in (cyn_list.backup1, cyn_list.backup2, cyn_list.backup3) if
                           (person and person.is_alive())]

            cynees = list(cyn_list.cynicized.all())

            for cynee in cynees:
                if not cynee.is_alive():
                    cyn_list.cynicized.remove(cynee)
                    if count_dead < len(backups):
                        cyn_list.cynicized.add(backups[count_dead])
                        count_dead += 1

            if not (cyn_list.drop and cyn_list.drop.is_alive()):
                cyn_list.drop = cyn_list.cynicized.first()
            (cyn_list.backup1, cyn_list.backup2, cyn_list.backup3) = (backups + [None, None, None])[
                                                                           count_dead:count_dead + 3]

            cyn_list.save()

        self.save()

    def get_username(self):
        return self.user.username

    username = property(get_username)

    def get_links(self):
        links = [(reverse('items'), "Manage your items"), (reverse('forms:death'), "Report your death.")]
        if self.can_make_kills():
            links.append((reverse('forms:kill'), "Report a kill you made"))
            if self.role == Role.objects.get(name="Rogue"):
                links.append((reverse('rogue_disarmed'), "Report that you were disarmed"))

        if self.can_investigate():
            links.append((reverse('forms:investigation'), "Make an investigation"))
        if self.role == Role.objects.get(name="Desperado"):
            if self.role_information == Player.DESPERADO_INACTIVE:
                links.append((reverse('go_desperado'), "Go desperado"))
            elif self.role_information == Player.DESPERADO_ACTIVATING:
                links.append((reverse('undo_desperado'), "Cancel going desperado"))
        if self.role == Role.objects.get(name__iexact="Conspiracy theorist"):
            links.append((reverse('forms:conspiracy_list'), 'Update your conspiracy list'))
        if self.role == Role.objects.get(name__iexact="Cynic"):
            links.append((reverse('forms:cynic_list'), 'Update your cynic list'))
        if self.is_evil():
            links.append((reverse('mafia_powers'), 'Mafia Powers'))
            if MafiaPower.objects.filter(power=MafiaPower.HIRE_A_HITMAN, state=MafiaPower.SET,
                                         game__active=True).exists():
                links.append((reverse("cancel_hitman"), "Cancel your hired hitman."))
            elif MafiaPower.objects.filter(power=MafiaPower.HIRE_A_HITMAN, state=MafiaPower.USED, game__active=True,
                                           day_used=self.game.current_day - 1, other_info=0).exists():
                links.append((reverse("forms:hitman_success"), "Report a kill on behalf of your hitman."))
        if self.role == Role.objects.get(name="Innocent Child"):
            links.append((reverse('forms:ic_reveal'), "Trust someone"))
        elif self.role == Role.objects.get(name="Superhero"):
            links.append((reverse('forms:superhero'), "Choose identity"))
        if self.elected_roles.filter(name="Mayor").exists() and self.game.mafia_counts < MAYOR_COUNT_MAFIA_TIMES:
            links.append((reverse('count_the_mafia'), "Count the Mafia"))
        if self.can_collect_clues() or self.can_destroy_clue():
            links.append((reverse('recent_deaths'), "Collect or Destroy Clues"))
        if self.elected_roles.filter(name="Police Officer").exists():
            if (now() - self.game.today_start).seconds < 3600:
                links.append(
                    (reverse("forms:watchlist", kwargs={'day': self.game.current_day}), "Update today's watchlist"))
            links.append(
                (reverse("forms:watchlist", kwargs={'day': self.game.current_day + 1}), "Update tomorrow's watchlist"))
        return links

    def get_unread_notifications(self):
        return Notification.objects.filter(user=self.user, game=self.game, seen=False).all()

    def get_notifications(self):
        return Notification.objects.filter(user=self.user, game=self.game).all()

    def notify(self, message, bad=True):
        Notification.objects.create(user=self.user, game=self.game, seen=False, content=message, is_bad=bad)
        self.log_notification(message="Notification for %s: '%s'" % (self, message))

    def impeach(self, position):
        self.elected_roles.remove(position)
        self.notify("You've been impeached! You're no longer the %s." % position)

        self.save()
        self.game.log(anonymous_message="%s has been impeached from being %s" % (self, position))

    def elect(self, position):
        self.elected_roles.add(position)
        if position.name != "Don":
            self.game.log(anonymous_message="%s was elected to the position of %s." % (self, position))
        else:
            self.game.log(message="%s was elected to the position of %s." % (self, position), mafia_can_see=True)
        self.notify("You've been elected as the new %s" % position, bad=False)

        self.save()

    def conscript(self):
        self.conscripted = True
        self.notify("You've been conscripted into the mafia. "
                    "Congratulations on your excellent life choices.", bad=False)
        self.save()


class Death(models.Model):
    murderer = models.ForeignKey(Player, related_name='kills', null=True)
    when = models.DateTimeField()
    kaboom = models.BooleanField(default=False)
    murderee = models.OneToOneField(Player)
    where = models.CharField(max_length=100)
    free = models.BooleanField(default=False)
    day = models.IntegerField()
    made_by_don = models.BooleanField(default=False)

    # Clues stuff
    clue_destroyers = models.ManyToManyField(Player, blank=True, related_name='destroyed')
    total_clues = models.IntegerField(null=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            # (if being created)
            traps = MafiaPower.objects.filter(target=self.murderee, state=MafiaPower.SET)
            if traps.exists():
                self.free = True
                for trap in traps:
                    if TRAPS_REGENERATE:
                        trap.state = MafiaPower.AVAILABLE
                    else:
                        trap.state = MafiaPower.USED
                    trap.target = None
                    trap.save()
            if not (self.murderer and self.murderer.is_evil()):
                # TODO does not take into account conscripted innocents making kills with innocent powers
                self.free = True
            kaboom = None
            if self.kaboom and ((not self.murderer) or (not self.murderer.elected_roles.filter(
                    name__iexact="Police officer").exists() and not (
                                self.murderer.role.name == "Gay Knight"
                        and Death.objects.filter(murderee=self.murderer.gn_partner,
                                                 murderer=self.murderee).exists() and self.murderer.investigation_set.filter(
                        guess=self.murderee).exists()))):
                if self.murderer and not self.murderer.is_evil():
                    raise Exception("Non-mafia attempt to use a kaboom without being police officer or vengeful knight")

                if (not KABOOMS_REGENERATE) or (
                            self.murderee.killable_by_bang(self.murderer) and not self.murderee.mic_secured()):
                    kabooms = MafiaPower.objects.filter(power=MafiaPower.KABOOM, state=MafiaPower.AVAILABLE,
                                                        game__active=True)
                    kaboom = kabooms[0]
                    kaboom.target = self.murderee
                    kaboom.day_used = self.murderee.game.current_day
                    kaboom.state = MafiaPower.USED
                    kaboom.user = self.murderer
                    kaboom.save()
                elif KABOOMS_REGENERATE:
                    if not MafiaPower.objects.filter(power=MafiaPower.KABOOM, state=MafiaPower.AVAILABLE,
                                                     game__active=True).exists():
                        raise IndexError("No kabooms")
                    self.murderee.game.log("Kaboom regenerated on kill of %s." % self.murderee, mafia_can_see=True)
                    self.murderer.notify("Kaboom regenerated on kill of %s" % self.murderee, bad=False)
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

                microphones = Item.objects.filter(owner=self.murderee, type=Item.MICROPHONE, used__isnull=True)
                if self.kaboom:
                    for item in self.murderee.item_set.all():
                        # Discard items
                        item.owner = None
                        item.save()
                        self.murderee.log(message="%s, which %s was holding, was destroyed by KABOOM!" %
                                                  (item.get_name(), self.murderee))
                else:
                    if not self.murderer.is_mafia_don():
                        for mic in microphones:
                            number = mic.number
                            # TODO should mics transfer upon death?
                            mic.used = self.when
                            mic.result = "This microphone has been set off."
                            mic.save()
                            if Item.objects.filter(type=Item.RECEIVER, number=number, owner__isnull=False).exists():
                                receiver = Item.objects.get(type=Item.RECEIVER, number=number, game=self.murderee.game)
                                receiver.owner.log(message="%s has heard from Receiver %d that %s killed %s." % (
                                    receiver.owner, number, self.murderer, self.murderee))
                                receiver.owner.notify("You hear something from Receiver %d! %s killed %s!" % (
                                    number, self.murderer, self.murderee))
                                receiver.used = self.when
                                receiver.target = self.murderee
                                receiver.result = "%s killed %s!" % (self.murderer, self.murderee)
                                receiver.save()
                    # Transfer items to killer
                    for item in self.murderee.item_set.all():
                        # Discard item if used
                        if item.used:
                            item.owner = None
                            item.save()
                        else:
                            item.owner = self.murderer
                            self.murderee.game.log(message="%s transferred from %s to %s upon kill" %
                                                           (item.get_name(), self.murderee, self.murderer),
                                                   users_who_can_see=[self.murderer, self.murderee])
                            self.murderer.notify(
                                "Upon killing %s, you received their %s" % (self.murderee, item.get_name()), bad=False)
                            item.save()

                if self.murderer.is_mafia_don():
                    self.made_by_don = True
                    don_kills = Death.objects.filter(murderee__game=self.murderee.game, made_by_don=True,
                                                     murderer=self.murderer).order_by('-when')
                    mafia_kills = Death.objects.filter(Q(murderer__role__name="Mafia") | Q(murderer__conscripted=True),
                                                       murderee__game=self.murderer.game).order_by('-when')
                    if don_kills.exists() and mafia_kills.exists() and (
                                    don_kills[0] == mafia_kills[0] or (len(mafia_kills) > 1 and don_kills[0] == mafia_kills[1])):
                        self.murderer.elected_roles.remove(ElectedRole.objects.get(name="Don"))
                        self.murderer.notify("You made 2 of 3 kills in a row, so you're no longer the mafia don.")
                        self.murderer.game.log(
                            "%s made 2 of 3 kills in a row and has lost the power of being mafia don." % self.murderer,
                            mafia_can_see=True)
                        self.made_by_don = False
                        self.murderer.save()

                if CLUES_IN_USE:
                    if MafiaPower.objects.filter(power=MafiaPower.MANIPULATE_THE_PRESS, target=self.murderee).exists():
                        self.total_clues = 0
                    else:
                        self.total_clues = 2 #1 + sum(
                            #p.is_evil() or p.role == Role.objects.get(name__iexact="Rogue") for p in
                            #self.murderee.game.living_players)

                    for watchlist in self.murderer.watched_by.filter(day=self.murderer.game.current_day):
                        self.update_clue_pile(watchlist.owner, watchlist=True)
                        watchlist.owner.notify("You gain 3 clues from the death of %s" % self.murderee)
                        watchlist.owner.log("%s gains 3 clues from the death of %s" % (watchlist.owner, self.murderee))

            elif CLUES_IN_USE:
                self.total_clues = 0

        super(Death, self).save(*args, **kwargs)

    def destroy_clue(self, destroyer):
        self.clue_destroyers.add(destroyer)
        self.total_clues -= 1
        self.save()

    def update_clue_pile(self, investigator, watchlist=False):
        pile, created = CluePile.objects.get_or_create(investigator=investigator, target=self.murderee)

        if watchlist:
            if created:
                pile.clues = 3
            else:  # collected is True
                pile.size += 3  # TODO is watchlist clue size constant? Anyway, put log for this elsewhere.
        elif pile.collected:
            investigator.log(message="%s looked back over %s's kill site and found %d clues." % (
                investigator, self.murderee, self.total_clues))
            pile.last_checked = now()
        else:
            pile.initial_size = self.total_clues
            pile.size += self.total_clues
            pile.collected = True
            pile.last_checked = now()
            investigator.log(message="%s searched %s's kill site and found %d clues." % (
                investigator, self.murderee, self.total_clues))

        pile.save()

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
        elif (not CLUES_IN_USE) and MafiaPower.objects.filter(power=MafiaPower.MANIPULATE_THE_PRESS,
                                                              target=self.murderee).exists():
            return False
        elif self.made_by_don:
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


class CluePile(models.Model):
    investigator = models.ForeignKey(Player, related_name='clues_found')
    target = models.ForeignKey(Player, related_name='clues_about')
    collected = models.BooleanField(default=False)
    initial_size = models.IntegerField(default=0)
    size = models.IntegerField(default=0)
    last_checked = models.DateTimeField(null=True)

    def __str__(self):
        return "%s's %d clue(s) on %s's death" % (self.investigator, self.size, self.target)

    def uncheckable(self):
        # TODO fix time zone awareness issue
        if not self.collected:
            return False
        elapsed = now() - self.last_checked
        return elapsed.seconds < 3600

    def local_text(self):
        if self.collected:
            return "%d out of %d clues remaining" % (self.size, self.initial_size)
        else:
            return "%d Police Officer clues for this site. You have not yet collected clues yourself." % (self.size)

    def use(self):
        self.size -= 1
        self.save()


class GayKnightPair(models.Model):
    player1 = models.ForeignKey(Player, related_name='gnp1')
    player2 = models.ForeignKey(Player, related_name='gnp2')

    def __str__(self):
        return self.player1.user.username + " <3 " + self.player2.user.username


class Investigation(models.Model):
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
            if self.death.murderee.mafiapowers_targeted_set.filter(power=MafiaPower.HIRE_A_HITMAN).exists():
                self.death.murderer = self.death.murderee

            self.result = (self.death.murderer == self.guess and self.death.is_investigable(self.investigation_type))

            if self.investigation_type != Investigation.GAY_KNIGHT:
                if MafiaPower.objects.filter(target=self.guess, other_info=self.death.murderee.id,
                                             game=self.death.murderee.game,
                                             power=MafiaPower.FRAME_A_TOWNSPERSON).exists():
                    self.result = True
        return self.result

    correct = property(is_correct)

    def type_name(self):
        for kind, name in Investigation.INVESTIGATION_KINDS:
            if kind == self.investigation_type:
                return name
        return "???????"

    def uses_clue(self):
        return CLUES_IN_USE and self.investigation_type in [Investigation.INVESTIGATOR, Investigation.SUPERHERO,
                                                            Investigation.DESPERADO, Investigation.POLICE_OFFICER]


class LynchVote(models.Model):
    voter = models.ForeignKey(Player, related_name="lynch_votes_made")
    lynchee = models.ForeignKey(Player, related_name="lynch_votes_received", null=True)
    time_made = models.DateTimeField()
    day = models.IntegerField()
    value = models.IntegerField(default=1)

    def __str__(self):
        lynchee = (self.lynchee if self.lynchee else NO_LYNCH)
        if self.value == 1:
            return "%s (day %d)" % (lynchee, self.day)
        else:
            return "%s x%d (day %d)" % (lynchee, self.value, self.day)


class Item(models.Model):
    TASER = "TA"
    SHOVEL = "SH"
    MICROPHONE = "MI"
    RECEIVER = "RE"
    MEDKIT = "ME"
    CCTV = "TV"
    CAMERA = "CM"

    ITEM_TYPE = (
        (TASER, "Taser"),
        (SHOVEL, "Shovel"),
        (MEDKIT, "Medkit"),
        (MICROPHONE, "Microphone"),
        (RECEIVER, "Receiver"),
        (CCTV, "CCTV"),
        (CAMERA, "Camera"),
    )

    game = models.ForeignKey(Game)
    owner = models.ForeignKey(Player, null=True, blank=True)
    number = models.IntegerField()
    type = models.CharField(max_length=2, choices=ITEM_TYPE)
    used = models.DateTimeField(null=True, blank=True)
    target = models.ForeignKey(Player, null=True, related_name="items_targeted_by", blank=True)
    result = models.TextField(null=True, blank=True)

    def get_password(self):
        # password depends on item, game, and owner
        random.seed((self.type, self.number, self.owner_id, self.game_id))
        return "".join(random.choice("1234567890QWERTYUIPASDFGHJKLZXCVBNM") for i in xrange(3))

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

    def can_use_via_form(self):
        return self.type == Item.SHOVEL or self.type == Item.MEDKIT or self.type == Item.TASER or self.type == Item.CAMERA

    def use(self, target=None):
        self.used = now()

        if self.type == Item.SHOVEL and not target.is_alive():
            self.result = target.death.get_shovel_text()
            self.game.log(message="%s shoveled %s with Shovel %d and got a result of %s." % (
                self.owner, target, self.number, self.result),
                          users_who_can_see=[self.owner])
            self.target = target
            self.save()
            return self.result
        elif self.type == Item.MEDKIT:
            self.owner.log(message="%s activated Medkit %d." % (self.owner, self.number))
        elif self.type == Item.TASER:
            self.game.log(message="%s tased %s with Taser %d." % (self.owner, target, self.number),
                          users_who_can_see=[self.owner, target])
        elif self.type == Item.CAMERA:
            self.owner.log(message="%s placed Camera %d in location \"%s\"" % (self.owner, self.number, target))
            self.owner.notify("Because cameras cannot automatically notify CCTV holders (locations have many names),"
                              " please PM god(s) with the location of your camera.", bad=False)
            self.result = target
            cctv = Item.objects.get(type=Item.CCTV, number=self.number, game=self.game)
            cctv.owner.notify("Your CCTV's camera was placed at %s" % target)
        self.save()
        return None

    def get_use_form(self):
        from forms import ItemUseForm

        return ItemUseForm(self)

    def use_text(self):
        if self.type == Item.MEDKIT:
            return "Use medkit (works until day end)"
        elif self.type == Item.TASER:
            return "Report use of taser"
        elif self.type == Item.SHOVEL:
            return "Shovel"
        elif self.type == Item.CAMERA:
            return "Report camera placement"

    def get_result_text(self):
        if self.type == Item.MEDKIT:
            return self.used.strftime("Used medkit at %H:%M on %B %d")
        elif self.type == Item.TASER:
            return "Tased %s %s" % (self.target, self.used.strftime("at %H:%M on %B %d"))
        elif self.type == Item.SHOVEL:
            return "Shoveled %s. Result: %s" % (self.target, self.result)
        elif self.type == Item.CAMERA:
            return "Camera placed at location \"%s\"" % self.result
        elif self.type == Item.CCTV:
            return self.result


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
    ELECT_A_DON = 11
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
        (CONSCRIPTION, "Conscription"),
        (ELECT_A_DON, "Elect a Don")
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
        if self.power == MafiaPower.HIRE_A_HITMAN:
            return "%s hired to kill %s" % (self.comment, self.target)
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
        elif self.power == MafiaPower.HIRE_A_HITMAN:
            if self.game.current_day == self.day_used:
                return "%s hired as a hitman for tomorrow" % self.comment
            elif self.game.current_day > 1 + self.day_used and self.other_info == 0:
                return "%s was unsuccessful" % self.comment
            elif self.other_info == 0:
                return "Hitman %s has not killed yet today" % self.comment
            elif self.other_info == 1:
                return "Hitman %s was successful" % self.comment
            else:
                return self.comment
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
                return "The mafia have successfully used slaughter the weak on %s." % self.target
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
        elif self.power == MafiaPower.ELECT_A_DON:
            return "The mafia have elected %s as their don." % self.target


class ConspiracyList(models.Model):
    owner = models.ForeignKey(Player)
    conspired = models.ManyToManyField(Player, related_name='conspiracies')
    day = models.IntegerField()
    drop = models.ForeignKey(Player, related_name='conspiracies_drop', null=True)
    backup1 = models.ForeignKey(Player, related_name='conspiracies_backup1', null=True)
    backup2 = models.ForeignKey(Player, related_name='conspiracies_backup2', null=True)
    backup3 = models.ForeignKey(Player, related_name='conspiracies_backup3', null=True)


class CynicList(models.Model):
    owner = models.ForeignKey(Player)
    cynicized = models.ManyToManyField(Player, related_name='cynicisms')
    day = models.IntegerField()
    drop = models.ForeignKey(Player, related_name='cynicisms_drop', null=True)
    backup1 = models.ForeignKey(Player, related_name='cynicisms_backup1', null=True)
    backup2 = models.ForeignKey(Player, related_name='cynicisms_backup2', null=True)
    backup3 = models.ForeignKey(Player, related_name='cynicisms_backup3', null=True)

    def cynicism_successful(self):
        """

        :return: whether this cynic's cynicism worked yesterday
        """
        for cynee in list(self.cynicized.all()):
            if (not cynee.is_alive()) and cynee.death.day == self.owner.game.current_day - 1 and cynee.death.murderer:
                return True
        return False


class LogItem(models.Model):
    game = models.ForeignKey(Game)
    text = models.CharField(blank=False, null=False, max_length=200)
    anonymous_text = models.CharField(null=True, max_length=200)
    mafia_can_view = models.BooleanField(default=False)
    users_can_view = models.ManyToManyField(Player, blank=True)
    time = models.DateTimeField(auto_now_add=True)
    day_start = models.BooleanField(default=False)
    show_all = models.BooleanField(default=True)

    def visible_to_anon(self, user):
        if self.anonymous_text:
            return self.show_all
        else:
            return self.visible_to(user)

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
    content = models.CharField(max_length=200)
    game = models.ForeignKey(Game)
    is_bad = models.BooleanField(default=True)


class SuperheroDay(models.Model):
    owner = models.ForeignKey(Player)
    secret_identity = models.BooleanField(default=True)
    day = models.IntegerField(null=True)
    paranoia = models.ForeignKey(Player, related_name='paranoid_superhero_days', null=True)

    superhero_identity = property(lambda self: not self.secret_identity)

    def paranoia_successful(self):
        """

        :return: whether this superhero's paranoia worked yesterday
        """
        # TODO check if this actually works
        return self.paranoia and (
        not self.paranoia.is_alive()) and self.paranoia.death.day == self.owner.game.current_day - 1

    def __str__(self):
        if self.superhero_identity:
            return "%s's superhero identity (day %d)" % (self.owner, self.day)
        else:
            return "%s's secret identity (day %d)" % (self.owner, self.day)


class WatchList(models.Model):
    owner = models.ForeignKey(Player)
    day = models.IntegerField()
    watched = models.ManyToManyField(Player, related_name="watched_by")

    def __str__(self):
        return "%s's watch list on day %d: [%s]" % (
            self.owner, self.day, ", ".join(p.username for p in self.watched.all()))

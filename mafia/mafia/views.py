from datetime import timedelta
from operator import add
from random import shuffle

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, User
from django.db import IntegrityError
from django.db.models import Q
from django.forms import Form
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.shortcuts import resolve_url
from django.utils.timezone import now
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import (REDIRECT_FIELD_NAME, login as auth_login, logout)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from forms import DeathReportForm, InvestigationForm, KillReportForm, LynchVoteForm, MafiaPowerForm, \
    ConspiracyListForm, SignUpForm, InnocentChildRevealForm, SuperheroForm, ElectForm, HitmanSuccessForm, CCTVDeathForm, \
    WatchListForm
from django.shortcuts import render
from settings import ROGUE_KILL_WAIT, MAYOR_COUNT_MAFIA_TIMES, CLUES_IN_USE
from models import Player, Death, Game, Investigation, LynchVote, Item, Role, ConspiracyList, MafiaPower, Notification, \
    SuperheroDay, GayKnightPair, ElectedRole, CluePile
from django.core.urlresolvers import reverse


def notifier(function):
    def new_func(request, *args, **kwargs):
        if request.user.is_authenticated():

            unread = Notification.objects.filter(user=request.user, game__active=True, seen=False)
            for message in unread:
                if message.is_bad:
                    messages.error(request, message.content)
                else:
                    messages.info(request, message.content)
            if request.user.is_impersonate:
                messages.info(request,
                              "You are impersonating right now. "
                              "<a class='alert-link' href='%s?next=%s'>Click here to stop.</a> " %
                              (reverse('impersonate-stop'), reverse('player_intros')))
        return function(request, *args, **kwargs)

    return new_func


def message_seen(request, message):
    notifications = Notification.objects.filter(user=request.user, game__active=True, seen=False, content=message)
    for notification in notifications:
        notification.seen = True
        notification.save()
    return HttpResponse("Notified")


is_mafia = lambda u: Player.objects.filter(Q(role__name="Mafia") | Q(conscripted=True), user=u, game__active=True,
                                           death__isnull=True).exists()
request_is_god = lambda r: Game.objects.filter(god=r.user).exists()


@notifier
def index(request):
    params = {}
    if request.user.username == "admin":
        return HttpResponseRedirect("/admin/mafia/game")
    try:
        game = Game.objects.get(active=True)
    except Game.DoesNotExist:
        if request.user.is_authenticated():
            try:
                game = Game.objects.get(god=request.user, archived=False)
                return HttpResponseRedirect(reverse('configure_game'))
            except Game.DoesNotExist:
                messages.warning(request, "There is no current game; please log in as a mod or admin.")
                logout(request)
                return HttpResponseRedirect(reverse('past_games'))
        else:
            return HttpResponseRedirect(reverse('past_games'))

    if game.current_day == 0:
        messages.info(request,
                      "Game has not started yet, only pregame actions may be taken."
                      " Click on the top-right corner of the screen to find out your role.")
    try:
        u = request.user
        if not isinstance(u, AnonymousUser):
            player = Player.objects.get(game=game, user=u)
        else:
            player = False
            params['game'] = game
    except Player.DoesNotExist:
        player = False
        params['user'] = request.user
        params['game'] = game
        if game.god == request.user:
            params['investigations'] = Investigation.objects.filter(investigator__game=game).order_by('-id')
    if player:
        params['vote'] = player.lynch_vote_made(game.current_day)
        params['player'] = player

    params['recent_deaths'] = Death.objects.filter(murderee__game__active=True).order_by('-when', 'murderee')[:10]

    return render(request, 'index.html',
                  params)


@notifier
@login_required
@user_passes_test(
    lambda user: user.is_authenticated() and Player.objects.filter(user=user, death=None, game__active=True).exists(),
    login_url='/')
def death_report(request):
    game = Game.objects.get(active=True)
    if game.current_day == 0:
        messages.warning(request, "You're not allowed to die, game hasn't started yet!")
        return HttpResponseRedirect("/")
    form = DeathReportForm(request.POST or None)
    me = Player.objects.get(user=request.user, game__active=True)
    if form.is_valid():
        where = form.data['where']
        killer = Player.objects.get(id=form.data['killer'])
        killed = me

        when = now() - timedelta(minutes=int(form.data['when']))
        kaboom = 'kaboom' in form.data
        Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom, where=where,
                             day=Game.objects.get(active=True).current_day)
        return HttpResponseRedirect("/")

    else:
        return render(request, 'form.html', {'form': form, 'player': me, 'title': 'Report your own death',
                                             'url': reverse('forms:death')})


@notifier
@login_required
@user_passes_test(
    lambda user: user.is_authenticated() and Player.objects.filter(user=user, role__name__iexact="superhero",
                                                                   game__active=True).exists(),
    login_url='/')
def superhero_form(request):
    me = Player.objects.get(user=request.user, game__active=True)
    if request.POST:
        form = SuperheroForm(request.POST)
    else:
        today = me.game.current_day
        try:
            today_day = me.superheroday_set.get(day=today)
            form = SuperheroForm(initial={'superhero_identity': today_day.superhero_identity,
                                          'paranoia': today_day.paranoia or me})
        except SuperheroDay.DoesNotExist:
            form = SuperheroForm(initial={'superhero_identity': False, 'paranoia': me})
    if form.is_valid():
        superhero_identity = 'superhero_identity' in form.data
        paranoia = Player.objects.get(id=form.data['paranoia'])
        today = me.game.current_day
        if me.superheroday_set.filter(day=today + 1).exists():
            tomorrow_day = me.superheroday_set.get(day=today + 1)
            tomorrow_day.secret_identity = not superhero_identity
            if superhero_identity:
                tomorrow_day.paranoia = paranoia
            else:
                tomorrow_day.paranoia = None
            tomorrow_day.save()
        else:
            s = not superhero_identity
            if superhero_identity:
                p = paranoia
            else:
                p = None
            SuperheroDay.objects.create(day=today + 1, paranoia=p, secret_identity=s, owner=me)
        if superhero_identity:
            me.log("%s has set superhero identity for day %d, with paranoia target %s." % (me, today + 1, paranoia))
        else:
            me.log("%s has set secret identity for day %d" % (me, today + 1))

        messages.success(request, "Set superhero settings for day %d successfully" % (today + 1))
        return HttpResponseRedirect('/')
    else:
        return render(request, 'form.html', {'form': form, 'player': me, 'title': 'Superhero Form',
                                             'url': reverse('forms:superhero')})


@notifier
@login_required
def kill_report(request):
    game = Game.objects.get(active=True)
    if game.current_day == 0:
        messages.warning(request, "You're not allowed to kill anyone, game hasn't started yet!")
        return HttpResponseRedirect("/")

    if request.method == "POST":
        form = KillReportForm(request.POST)
        if form.is_valid():
            where = form.data['where']
            killed = Player.objects.get(id=form.data['killed'])
            killer = Player.objects.get(user=request.user, game__active=True)
            when = now() - timedelta(minutes=int(form.data['when']))
            kaboom = 'kaboom' in form.data
            try:
                Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom,
                                     day=Game.objects.get(active=True).current_day, where=where)
            except IndexError, e:
                player = Player.objects.get(user=request.user, game__active=True)
                messages.error(request,
                               "This kill is illegal (perhaps mafia have killed already"
                               " today or you're using a nonexistent kaboom?)")
                return render(request, 'form.html', {'form': form, 'player': player, 'url': reverse('forms:kill'),
                                                     'title': 'Report a Kill You Made'})
            except IntegrityError:
                player = Player.objects.get(user=request.user, game__active=True)
                messages.error(request,
                               "That player is already dead (they probably beat you to reporting the kill).")
                return render(request, 'form.html', {'form': form, 'player': player, 'url': reverse('forms:kill'),
                                                     'title': 'Report a Kill You Made'})
            return HttpResponseRedirect("/")

    else:
        player = Player.objects.get(user=request.user, game__active=True)
        if player.is_alive():
            form = KillReportForm()

            return render(request, 'form.html', {'form': form, 'player': player, 'url': reverse('forms:kill'),
                                                 'title': 'Report a Kill You Made'})
        else:
            messages.add_message(request, messages.ERROR, "You're dead already")
            return HttpResponseRedirect("/")


@notifier
def recent_deaths(request):
    game = Game.objects.get(active=True)
    is_god = request.user == game.god
    recents = Death.objects.filter(murderee__game__active=True).order_by('-when', 'murderee')
    can_destroy = False
    destructibles = []
    clue_piles = None
    gatherables = []
    if isinstance(request.user, AnonymousUser):
        return render(request, 'recent_deaths.html',
                      {'god': is_god, 'deaths': recents, 'game': game, 'user': request.user})
    elif game.has_user(request.user):
        player = Player.objects.get(user=request.user, game=game)
        if player.is_alive() and CLUES_IN_USE:
            if player.is_evil() or player.role.name == "Rogue":
                destructibles = Death.objects.filter(murderee__game__active=True, total_clues__gt=-1).exclude(
                    clue_destroyers=player)
            for death in Death.objects.filter(murderee__game__active=True):
                if player.can_collect_clues(death.murderee):
                    gatherables.append(death)
    else:
        player = {'god': is_god, 'game': game, 'username': request.user.username,
                  'role': {'name': "God" if is_god else "Guest"}}
    return render(request, 'recent_deaths.html',
                  {'god': is_god, 'deaths': recents, 'player': player, 'gatherables': gatherables,
                   'can_destroy': can_destroy, 'destructibles': destructibles})


@notifier
@login_required
def your_role(request):
    game = Game.objects.get(active=True)
    try:
        player = Player.objects.get(game=game, user=request.user)
    except Player.DoesNotExist:
        messages.add_message(request, messages.ERROR, "You aren't playing, so you can't go to your role page.")
        return HttpResponseRedirect("/")

    return render(request, 'your_role.html',
                  {'player': player})


@notifier
@login_required
def investigation_form(request):
    game = Game.objects.get(active=True)
    player = Player.objects.get(game=game, user=request.user)
    if request.method == "POST":
        form = InvestigationForm(request.POST)
        if form.is_valid():
            death = Death.objects.get(id=form.data["death"])
            print("try love")
            if player.can_investigate(form.data['investigation_type'], death):
                guess = Player.objects.get(id=form.data['guess'])
                investigation = Investigation.objects.create(investigator=player, death=death, guess=guess,
                                                             investigation_type=form.data['investigation_type'],
                                                             day=game.current_day)
                if investigation.uses_clue():
                    pile = CluePile.objects.get(investigator=player, target=death.murderee)
                    pile.use()
                player.log(message="%s investigates %s for the death of %s (answer: %s)" %
                                   (
                                   player, guess, death.murderee, "Correct" if investigation.is_correct() else "Wrong"))
                if investigation.is_correct():
                    messages.add_message(request, messages.SUCCESS, "Correct. <b>%s</b> killed <b>%s</b>."
                                         % (guess.user.username, death.murderee.user.username))
                else:
                    messages.add_message(request, messages.WARNING,
                                         "Your investigation turns up nothing. <b>%s</b> did not kill <b>%s</b>." % (
                                             guess.user.username, death.murderee.user.username))
                return HttpResponseRedirect("/")
            else:
                print("no love?")
                if player.can_investigate(form.data['investigation_type']):
                    messages.add_message(request, messages.ERROR, "You don't have clues for this death.")
                else:
                    messages.add_message(request, messages.ERROR, "You can't use that kind of investigation.")
        else:
            messages.add_message(request, messages.ERROR, "Invalid investigation.Please try again.")
    if Player.objects.get(user=request.user, game__active=True).is_alive():
        form = InvestigationForm()

        return render(request, 'form.html', {'form': form, 'player': player, 'title': "Make an Investigation",
                                             'url': reverse('forms:investigation')})
    else:
        messages.add_message(request, messages.ERROR, "Dead people can't make investigations.")

    return HttpResponseRedirect("/")


@notifier
@login_required
@user_passes_test(
    lambda user: user.is_authenticated() and Player.objects.filter(user=user, death=None, game__active=True,
                                                                   role__name="Rogue").exists(),
    login_url='/')
def rogue_disarmed(request):
    p = Player.objects.get(user=request.user, game__active=True)
    p.role_information = p.game.current_day + ROGUE_KILL_WAIT
    p.game.log(message="%s was disarmed by a mafia member." % p, users_who_can_see=[p], mafia_can_see=True)
    p.save()
    return HttpResponseRedirect("/")


@notifier
def daily_lynch(request, day):
    if request.user.is_authenticated():
        try:
            player = Player.objects.get(user=request.user, game__active=True)
        except Player.DoesNotExist:
            player = False
    else:
        player = False
    # TODO implement tiebreaker
    game = Game.objects.get(active=True)

    # parameters from URLs are *strings* by default
    day = int(day)

    if day >= game.current_day:
        messages.add_message(request, messages.ERROR,
                             "It's only day <b>%d</b>, you can't see day <b>%d</b>'s lynch yet." % (
                                 game.current_day, day))
        return HttpResponseRedirect('/')

    lynches, choices = game.get_lynch(day)

    if len(lynches) == 0:
        lynch_str = "No lynch"
    elif len(lynches) == 1:
        lynch_str = "%s is lynched." % lynches[0].username
    else:
        lynch_str = ", ".join(a.username for a in lynches) + " are lynched."

    return render(request, 'daily_lynch.html', {'lynch_str': lynch_str,
                                                'choices': choices,
                                                'game': game,
                                                'day': day,
                                                'player': player})


@notifier
@login_required
def lynch_vote(request):
    player = Player.objects.get(user=request.user, game__active=True)
    game = player.game

    # if not Death.objects.filter(murderer__game=game).exists():
    # messages.add_message(request, messages.INFO, "You can't lynch anyone yet - nobody has been killed.")
    # return HttpResponseRedirect("/")
    if player.is_alive():
        if request.method == "POST":
            form = LynchVoteForm(request.POST)
            if form.is_valid():
                vote_value = Player.objects.get(id=form.data["vote"]) if form.data["vote"] else None
                vote = LynchVote.objects.create(voter=player, lynchee=vote_value, time_made=now(),
                                                day=game.current_day)
                if vote_value:
                    vote_message = "%s voted to lynch %s" % (player, vote_value)
                else:
                    vote_message = "%s voted for no lynch" % player
                if player.elected_roles.filter(name="Mayor").exists():
                    vote.value = 3
                    vote.save()
                    vote_message += " (3x vote)"

                player.log(vote_message)

                return HttpResponseRedirect("/")
        else:
            form = LynchVoteForm()

            return render(request, 'form.html', {'form': form, 'player': player, 'title': 'Vote to Lynch Someone',
                                                 'url': reverse('forms:vote')})
    else:
        messages.add_message(request, messages.ERROR, "Dead people don't vote. :(")
        return HttpResponseRedirect("/")


@notifier
@login_required
def items(request):
    if request.POST:
        form = Form(request.POST)
        if form.is_valid():
            item_to_use = Item.objects.get(id=form.data['item'])
            if not item_to_use.used:
                if 'target' in form.data:
                    try:
                        target = Player.objects.get(id=form.data['target'])
                    except ValueError:
                        target = form.data['target']
                    messages.info(request, "Item used: %s. Target: %s" % (item_to_use, target))
                    item_to_use.use(target)
                else:
                    messages.info(request, "Item used successfully: %s." % item_to_use)
                    item_to_use.use()

    game = Game.objects.get(active=True)
    if request.user == game.god:
        messages.add_message(request, messages.WARNING,
                             "Sorry, this view has not been implemented for you. Check the game log instead.")
        return HttpResponseRedirect(reverse('logs'))
    player = Player.objects.get(user=request.user, game__active=True)
    if player.is_alive():
        return render(request, "items.html", {'player': player, 'game': game})
    else:
        messages.add_message(request, messages.WARNING,
                             "You're dead, so you can't use items. Check the game log instead.")
        return HttpResponseRedirect(reverse('logs'))


@login_required
@user_passes_test(lambda u: Player.objects.filter(user=u, game__active=True, death__isnull=True).exists())
def collect_clues(request, id):
    try:
        death = Death.objects.get(id=id)
    except Death.DoesNotExist:
        messages.add_message(request, messages.ERROR, "You're trying to collect clues from a nonexistent death.")
        return HttpResponseRedirect("/")
    player = Player.objects.get(user=request.user, game__active=True)
    if not player.can_collect_clues(death.murderee):
        messages.add_message(request, messages.ERROR, "You can't collect clues from this death at this time.")
        return HttpResponseRedirect("/")
    death.update_clue_pile(player)
    messages.add_message(request, messages.SUCCESS,
                         "You searched the kill site and found %d clues." % (death.total_clues))
    return HttpResponseRedirect(reverse('recent_deaths'))


@login_required
@user_passes_test(lambda u: Player.objects.filter(user=u, game__active=True, death__isnull=True).exists())
def destroy_clue(request, id):
    try:
        death = Death.objects.get(id=id)
    except Death.DoesNotExist:
        messages.add_message(request, messages.ERROR, "You're trying to destroy a clue from a nonexistent death.")
        return HttpResponseRedirect(reverse('recent_deaths'))

    player = Player.objects.get(user=request.user, game__active=True)

    if not player.can_destroy_clue():
        messages.add_message(request, messages.ERROR, "You're not evil. You can't destroy clues.")
        return HttpResponseRedirect(reverse('recent_deaths'))

    if not player.can_destroy_clue(death):
        messages.add_message(request, messages.ERROR, "You've already destroyed a clue here.")
        return HttpResponseRedirect(reverse('recent_deaths'))

    death.destroy_clue(player)
    player.log(message="%s destroyed a clue at %s's kill site." % (player, death.murderee))
    messages.add_message(request, messages.SUCCESS, "Clue successfully destroyed.")
    death.save()
    return HttpResponseRedirect(reverse('recent_deaths'))


@login_required
def destroy_item(request, id):
    current_item = Item.objects.get(id=id)
    player = Player.objects.get(user=request.user, game__active=True)
    if current_item.owner != player:
        messages.add_message(request, messages.WARNING, "That item does not belong to you.")
    else:
        current_item.owner = None
        player.log(message="%s has destroyed %s" % (player, current_item.get_name()))
        messages.add_message(request, messages.SUCCESS, "Item successfully destroyed.")
        current_item.save()

    return HttpResponseRedirect(reverse('items'))


@notifier
@login_required
def transfer_item(request, item_id, password):
    current_item = Item.objects.get(id=item_id)
    if current_item.password != password or current_item.used or not current_item.owner:
        return HttpResponseNotFound
    else:
        player = Player.objects.get(user=request.user, game__active=True)
        if player != current_item.owner:
            old_owner = current_item.owner
            current_item.owner = player
            current_item.save()
            messages.add_message(request, messages.SUCCESS,
                                 "You have successfully acquired <b>%s</b> from <b>%s</b>." % (
                                     current_item.name, old_owner.username))
            return HttpResponseRedirect(reverse('items'))

        else:
            return render(request, "transfer_item.html", {'item': current_item, 'player': player})


@notifier
@login_required
def count_the_mafia(request):
    if Game.objects.get(active=True).mafia_counts == MAYOR_COUNT_MAFIA_TIMES:
        messages.warning(request, "All mafia counts have been used.")
    try:
        player = Player.objects.get(user=request.user, game__active=True)
        if player.elected_roles.filter(name="Mayor").exists():
            mafia_count = sum(p.is_evil() for p in player.game.living_players)
            messages.info(request, "There are <b>%d</b> mafia remaining." % mafia_count)
            player.log("Mayor %s has counted the mafia and found that %d remain." % (player, mafia_count))
            player.game.mafia_counts += 1
            player.game.save()
    except Player.DoesNotExist:
        pass
    return HttpResponseRedirect("/")


@sensitive_post_parameters()
@csrf_protect
@never_cache
def sign_up(request):
    try:
        game = Game.objects.get(active=False, archived=False)
    except Game.DoesNotExist:
        game = None
    form = SignUpForm(request.POST or None)
    if form.is_valid():
        username = form.data['username']
        password = form.data['password']
        confirm_password = form.data['confirm_password']
        email = form.data['email']
        picture = form.data['picture']
        intro = form.data['introduction']
        try:
            user = User.objects.get(username=username)
            if not user.check_password(password):
                messages.error(request, "Wrong password.")
                return render(request, 'sign_up.html', {'form': form, 'game': game})
        except User.DoesNotExist:
            if password != confirm_password:
                messages.error(request, "Password must match confirmation.")
                return render(request, 'sign_up.html', {'form': form, 'game': game})
            else:
                user = User.objects.create(username=username)
                user.set_password(password)
                user.email = email
                user.save()
        try:
            if picture[:4].lower() != "http":
                picture = "http://" + picture
            Player.objects.create(user=user, game=game, introduction=intro, photo=picture)
        except IntegrityError:
            messages.warning(request, "You're already signed up for this game.")
            return HttpResponseRedirect(reverse("past_games"))
        messages.success(request, "You signed up for mafia game \"%s\" successfully" % game.name)
        return HttpResponseRedirect(reverse("past_games"))
    return render(request, 'sign_up.html', {'form': form, 'game': game})


@notifier
@login_required
def go_desperado(request):
    player = Player.objects.get(user=request.user, game__active=True, role__name__iexact="desperado")
    if player.role_information == Player.DESPERADO_INACTIVE:
        player.role_information = Player.DESPERADO_ACTIVATING
        player.log("%s  is going desperado tonight." % player)
        player.save()
    return HttpResponseRedirect("/")


@notifier
@login_required
def undo_desperado(request):
    player = Player.objects.get(user=request.user, game__active=True, role__name__iexact="desperado")
    if player.role_information == Player.DESPERADO_ACTIVATING:
        player.role_information = Player.DESPERADO_INACTIVE
        player.log("%s is no longer going desperado tonight." % player)
        player.save()
    return HttpResponseRedirect("/")


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login(request, template_name='registration/login.html',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))

    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            # Okay, security check complete. Log the user in.
            auth_login(request, form.get_user())

            return HttpResponseRedirect(redirect_to)
    else:
        form = authentication_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app=current_app)


@notifier
@login_required
def advance_day(request):
    game = Game.objects.get(active=True)
    if request.user == game.god:
        game.increment_day()
        messages.info(request, "Day advanced successfully")
    return HttpResponseRedirect("/")


@notifier
@login_required
def player_intros(request):
    game = Game.objects.get(active=True)
    try:
        player = game.player_set.get(user=request.user)
        return render(request, 'introductions.html', {'player': player, 'game': game})
    except Player.DoesNotExist:
        if game.god != request.user:
            return HttpResponse("You must be playing in this game.")
        else:
            return render(request, 'introductions.html', {'user': request.user, 'game': game})


@notifier
@login_required
@user_passes_test(is_mafia)
def mafia_power_form(request):
    form = MafiaPowerForm(request, request.POST or None)
    player = Player.objects.get(user=request.user, game__active=True)
    if form.is_valid():
        message = form.submit(player)
        messages.add_message(request, messages.SUCCESS, message)
        return HttpResponseRedirect(reverse('mafia_powers'))
    else:
        power = MafiaPower.objects.get(id=request.GET['power_id'])
        return render(request, "form.html",
                      {'form': form, 'player': player, "title": "Use a Mafia Power: %s" % power,
                       'url': reverse('forms:mafia_power')})


@notifier
@login_required
def mafia_powers(request):
    game = Game.objects.get(active=True)
    if not request.user == game.god:
        player = Player.objects.get(user=request.user, game__active=True)
    if request.user == game.god or not player.is_alive():
        return render(request, "mafia_powers.html", {'user': request.user, 'game': game, 'usable': False})
    elif player.is_evil():
        return render(request, "mafia_powers.html", {'player': player, 'game': game, 'usable': True})
    else:
        messages.add_message(request, messages.WARNING, "You're not mafia, you can't do mafia things!")
        return HttpResponseRedirect("/")


@notifier
@login_required
def end_game(request):
    # TODO make game over mean things
    game = Game.objects.get(active=True)
    if request.user == game.god:
        game.archived = True
        game.save()
        messages.info(request, "Game ended successfully")
        for player in game.player_set.all():
            player.notify("Game has ended - check forums to see who won.", bad=False)
    return HttpResponseRedirect("/")


@login_required
def evict_player(request, pid):
    game = Game.objects.get(active=True)
    if request.user == game.god:
        player = Player.objects.get(id=pid)
        Death.objects.create(murderee=player, day=player.game.current_day, when=now(),
                             where="Evicted (day %d)" % player.game.current_day)
        messages.success(request, "%s removed from game" % player.username)
        game.log("%s evicted from game" % player)
    return HttpResponseRedirect(reverse('player_intros'))


@login_required
def resurrect_player(request, pid):
    game = Game.objects.get(active=True)
    if request.user == game.god:
        player = Player.objects.get(id=pid)
        Death.objects.get(murderee=player).delete()
        messages.success(request, "%s resurrected" % player.username)
        game.log("%s resurrected by %s" % (player, game.god.username))
    return HttpResponseRedirect(reverse('player_intros'))


@notifier
@login_required
def conspiracy_list_form(request):
    form = ConspiracyListForm(request.POST or None)
    if form.is_valid():
        player = Player.objects.get(game__active=True, user=request.user)
        if player.role != Role.objects.get(name__iexact="Conspiracy theorist"):
            messages.warning(request, "You're not a conspiracy theorist!")
            return HttpResponseRedirect("/")
        conspiracy = ConspiracyList.objects.get_or_create(owner=player, day=player.game.current_day + 1)[0]
        conspiracy.conspired.clear()
        data = form.data['new_conspiracy_list']
        if isinstance(data, unicode):
            data = [data]
        consp_list = []
        for conspiree in data:
            c = Player.objects.get(id=int(conspiree))
            conspiracy.conspired.add(c)
            consp_list.append(c.username)

        conspiracy.drop = Player.objects.get(id=form.data['person_to_remove'])
        if conspiracy.drop.username not in consp_list:
            messages.error(request, "Your person-to-drop must be on your list.")
            player = Player.objects.get(user=request.user, game__active=True)
            return render(request, "form.html", {'form': form, 'player': player, "title": "Set up Your Conspiracy List",
                                                 'url': reverse('forms:conspiracy_list')})
        conspiracy.backup1 = Player.objects.get(id=form.data['backup1'])
        conspiracy.backup2 = Player.objects.get(id=form.data['backup2'])
        conspiracy.backup3 = Player.objects.get(id=form.data['backup3'])
        conspiracy.save()
        player.log("%s has updated their conspiracy list for day %d to: [%s]" % (player, player.game.current_day + 1,
                                                                                 ", ".join(consp_list)))
        messages.success(request, "Conspiracy list updated successfully")
        return HttpResponseRedirect(reverse('your_role'))
    else:
        player = Player.objects.get(user=request.user, game__active=True)
        return render(request, "form.html", {'form': form, 'player': player, "title": "Set up Your Conspiracy List",
                                             'url': reverse('forms:conspiracy_list')})


@notifier
def logs(request):
    game = Game.objects.get(active=True)
    game_logs = [(log_item.get_text(request.user), log_item.time, log_item.is_day_start()) for log_item in
                 game.logitem_set.all() if
                 log_item.visible_to_anon(request.user)]
    game_logs.sort(key=lambda a: a[1])
    try:
        player = Player.objects.get(game=game, user=request.user)
    except Player.DoesNotExist:
        player = None
    return render(request, "logs.html", {'player': player, 'user': request.user, 'logs': game_logs, 'game': game})


@notifier
@login_required
@user_passes_test(
    lambda user: user.is_authenticated() and Player.objects.filter(user=user, death=None, game__active=True,
                                                                   role__name="Innocent Child").exists(),
    login_url='/')
def ic_reveal(request):
    form = InnocentChildRevealForm(request.POST or None)
    if form.is_valid():
        data = form.data['players_revealed_to']
        if isinstance(data, unicode):
            data = [data]
        revealed_to = [Player.objects.get(id=int(p)) for p in data]
        if revealed_to:
            game = revealed_to[0].game
            revealer = Player.objects.get(game=game, user=request.user)
            for revelee in revealed_to:
                game.log(message="%s is an innocent child and trusts %s" % (revealer, revelee),
                         users_who_can_see=[revealer, revelee])
                revelee.notify("%s is an innocent child and trusts you." % revealer, bad=False)
            messages.success(request, "You have successfully revealed as an IC.")
        return HttpResponseRedirect("/")
    player = Player.objects.get(game__active=True, user=request.user)
    return render(request, "form.html", {'player': player, 'form': form, 'title': 'Reveal as an Innocent Child',
                                         'url': reverse('forms:ic_reveal')})


def old_logs(request, game_id):
    game = Game.objects.get(id=game_id)
    if not game.archived:
        return HttpResponseRedirect("/")
    game_logs = [(log_item.get_text(game.god), log_item.time, log_item.is_day_start()) for log_item in
                 game.logitem_set.all()]
    game_logs.sort(key=lambda a: a[1])
    try:
        current_game = Game.objects.get(active=True)
    except Game.DoesNotExist:
        current_game = False
    if current_game == game:
        return HttpResponseRedirect(reverse("logs"))
    try:
        next_game = Game.objects.get(active=False, archived=False)
    except Game.DoesNotExist:
        next_game = False
    return render(request, "old_logs.html",
                  {'logs': game_logs, 'game': game, 'current_game': current_game, 'next_game': next_game})


def past_games(request):
    try:
        current_game = Game.objects.get(active=True)
    except Game.DoesNotExist:
        current_game = False
    try:
        next_game = Game.objects.get(active=False, archived=False)
    except Game.DoesNotExist:
        next_game = False

    games = Game.objects.all()
    return render(request, "past_games.html",
                  {'games': games, 'current_game': current_game, 'next_game': next_game})


@login_required
def configure_game(request):
    try:
        game = Game.objects.get(active=False, archived=False, god=request.user)
    except Game.DoesNotExist:
        messages.error(request, "You may not configure a game at this time.")
        return HttpResponseRedirect("/")

    if request.POST and 'purpose' in request.POST and request.POST['purpose'] == 'roles':
        roles = [(r, int(request.POST['rolenum%d' % r.id])) for r in Role.objects.all()]
        num_roles = sum(b for a, b in roles)
        num_players = len(game.player_set.all())
        err = False
        if num_roles != num_players:
            messages.error(request, "There are %d players, but the total number of roles you have entered is %d." % (
                num_players, num_roles))
            err = True

        for role, count in roles:
            if role.name == "Mafia":
                if count <= 0:
                    messages.error(request, "Please enter a positive number of mafia")
                    err = True
            elif role.name == "Gay Knight":
                if count < 0 or count % 2 != 0:
                    messages.error(request, "Please enter a nonnegative even number of Gay Knights")
                    err = True
            else:
                if count < 0:
                    messages.error(request, "There are a negative number of players with the role %s" % role.name)
                    err = True

        if not err:
            roles_to_randomize = reduce(add, ([role] * count for role, count in roles), [])
            shuffle(roles_to_randomize)
            for player, role in zip(game.player_set.all(), roles_to_randomize):
                player.role = role
                player.save()
            GayKnightPair.objects.filter(player1__game=game).delete()
            messages.success(request, "Randomized roles successfully.")
    else:
        counts = dict((r, 0) for r in Role.objects.all())
        for player in game.player_set.all():
            if player.role:
                counts[player.role] += 1
        roles = [(a, counts[a]) for a in Role.objects.all()]

    if request.POST and 'purpose' in request.POST and request.POST['purpose'] == 'knights':
        GayKnightPair.objects.filter(player1__game=game).delete()
        gay_knights = list(game.player_set.filter(role__name="Gay Knight").all())
        shuffle(gay_knights)
        for i in xrange(len(gay_knights) / 2):
            GayKnightPair.objects.create(player1=gay_knights[i * 2],
                                         player2=gay_knights[i * 2 + 1])
        messages.success(request, "Paired GNs successfully.")

    if request.POST and 'purpose' in request.POST and request.POST['purpose'] == 'start':
        print "starting game"
        messages.success(request, "Game started successfully. Players "  # have been notified by e-mail and
                                  " can now log in.")
        # TODO email the players
        game.increment_day()
        return HttpResponseRedirect("/")

    if request.POST and 'purpose' in request.POST and request.POST['purpose'] == "items":
        items = [(it, int(request.POST['item_%s' % it[0]])) for it in Item.ITEM_TYPE]
        err = False
        num_items = sum(b for a, b in items)
        num_players = len(game.player_set.all())

        if num_players < num_items:
            messages.error(request,
                           "There are more items than players - %d items, %d players" % (num_items, num_players))
            err = True

        for it, count in items:
            if it[0] == Item.MICROPHONE:
                count_mics = count
            elif it[0] == Item.RECEIVER:
                count_recs = count
            elif it[0] == Item.CCTV:
                count_cctvs = count
            elif it[0] == Item.CAMERA:
                count_cams = count

            if count < 0:
                messages.error(request, "There is a negative number of %ss" % it[1])
                err = True

        if count_mics != count_recs:
            messages.error(request, "There should be the same number of microphones as receivers.")
            err = True

        if count_cams != count_cctvs:
            messages.error(request, "There should be the same number of cameras as CCTVs.")
            err = True

        if not err:
            game.item_set.all().delete()
            items_to_randomize = reduce(add, (zip([it] * count, xrange(1, count + 1)) for it, count in items),
                                        [None] * (num_players - num_items))
            shuffle(items_to_randomize)
            for player, item in zip(game.player_set.all(), items_to_randomize):
                if item:
                    itempair = item[0]
                    itemnum = item[1]
                    item_type = itempair[0]
                    Item.objects.create(game=game, owner=player, number=itemnum, type=item_type)
            messages.success(request, "Randomized items successfully.")

    else:
        counts = dict((it[0], 0) for it in Item.ITEM_TYPE)
        for item in game.item_set.all():
            counts[item.type] += 1
        items = [(item, counts[item[0]]) for item in Item.ITEM_TYPE]
    params = dict(game=game, roles=roles, items=items)
    return render(request, "configure_game.html", params)


@login_required
@user_passes_test(lambda u: Game.objects.filter(god=u, active=True).exists())
def election(request):
    form = ElectForm(request.POST or None)
    if form.is_valid():
        player_elected = Player.objects.get(id=form.data['player_elected'])
        game = player_elected.game
        position = ElectedRole.objects.get(id=form.data['position'])
        player_elected.elect(position)

        return HttpResponseRedirect(reverse('logs'))
    else:
        game = request.user.game_set.get(active=True)
        return render(request, "form.html",
                      {'user': request.user, 'game': game, 'form': form, 'title': "Submit a petition",
                       'url': reverse('forms:elect')})


@login_required
@user_passes_test(lambda u: Game.objects.filter(god=u, active=True).exists())
def impeach(request, player_id, electedrole_id):
    player = Player.objects.get(id=player_id)
    position = ElectedRole.objects.get(id=electedrole_id)
    player.impeach(position)
    return HttpResponseRedirect(reverse('logs'))


@login_required
@user_passes_test(is_mafia)
def cancel_hitman(request):
    hitman = MafiaPower.objects.get(power=MafiaPower.HIRE_A_HITMAN, state=MafiaPower.SET, game__active=True)
    hitman.state = MafiaPower.AVAILABLE
    hitman.target = None
    hitman.day_used = None
    hitman.comment = ""
    hitman.other_info = None
    hitman.user = None
    hitman.save()
    messages.info(request, "Cancelled hitman.")
    hitman.game.log(message="The mafia have gotten rid of their hitman. Who knows what they did with the body...",
                    mafia_can_see=True)
    return HttpResponseRedirect(reverse('mafia_powers'))


@login_required
@user_passes_test(is_mafia)
def hitman_success(request):
    game = Game.objects.get(active=True)

    if request.method == "POST":
        form = HitmanSuccessForm(request.POST)
        if form.is_valid():
            where = form.data['where']
            hitman = MafiaPower.objects.get(id=form.data['hitman'])
            killed = hitman.target
            when = now() - timedelta(minutes=int(form.data['when']))
            kaboom = 'kaboom' in form.data

            Death.objects.create(when=when, murderer=None, murderee=killed, kaboom=kaboom,
                                 day=killed.game.current_day, where=where)
            game.log(message="Hitman %s killed %s" % (hitman.comment, hitman.target),
                     anonymous_message="% was killed at %s" % (killed, where), mafia_can_see=True)
            hitman.other_info = 1
            hitman.save()
            return HttpResponseRedirect("/")

    else:
        player = Player.objects.get(user=request.user, game__active=True)
        form = HitmanSuccessForm()
        return render(request, 'form.html', {'form': form, 'player': player, 'url': reverse('forms:hitman_success'),
                                             'title': 'Report a Hitman Kill'})


@login_required
def cctv_death_form(request):
    try:
        game = Game.objects.get(active=True, archived=False, god=request.user)
    except Game.DoesNotExist:
        return HttpResponseRedirect("/")
    form = CCTVDeathForm(request.POST or None)
    if form.is_valid():
        cctv = Item.objects.get(id=form.data['cctv'])
        death = Death.objects.get(id=form.data['death'])
        if death.kaboom:
            cctv.owner.notify("Your CCTV has mysteriously gone blank. Perhaps this was caused by an explosion.")
            cctv.result = "Screen gone black"
            cctv.save()
        else:
            cctv.owner.notify(
                "You see something on your TV screen. It's a murder! %s killed %s." % (death.murderer, death.murderee))
        return HttpResponseRedirect("/")

    return render(request, 'form.html',
                  {'form': form, 'user': request.user, 'game': game, 'url': reverse('forms:cctv_death'),
                   'title': 'Notify CCTV Owner'})


@login_required
@user_passes_test(lambda u: Player.objects.filter(user=u, elected_roles__name="Police Officer", death__isnull=True,
                                                  game__active=True).exists())
def modify_watch_list(request, day=None):
    player = Player.objects.get(user=request.user, game__active=True)
    if day is None:
        day = player.game.current_day + 1
    watchlist = player.watchlist_set.get_or_create(day=day)[0]
    if request.POST:
        form = WatchListForm(request.POST)
        tomorrow = form.data['day'] > player.game.current_day  # could be after tomorrow, this is ok
        today = form.data['day'] == player.game.current_day and (now() - player.game.today_start).seconds < 3600

        # no idea why this is necessary, but I get strange bugs otherwise.
        data = dict(form.data)['watched']

        if isinstance(data, unicode):
            data = [form.data['watched']]
        if (tomorrow or today) and len(data) <= 3:
            watchlist.watched.clear()
            for pid in data:
                watchlist.watched.add(pid)
            watchlist.save()
            messages.success(request, "Watchlist updated.")
            return HttpResponseRedirect('/')
        elif len(data) <= 3:
            messages.error(request, "You can't update that day's watchlist anymore.")
        else:
            messages.error(request, "You can only put up to three people on your watchlist.")
    else:
        form = WatchListForm(initial={'day': day, 'watched': [watch.id for watch in watchlist.watched.all()]})

    return render(request, 'form.html',
                  {'form': form, 'player': player, 'url': reverse('forms:watchlist', kwargs={'day': day}),
                   'title': 'Update your watchlist'})

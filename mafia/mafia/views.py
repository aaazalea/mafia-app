from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, User
from django.db import IntegrityError
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.shortcuts import resolve_url
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import (REDIRECT_FIELD_NAME, login as auth_login, logout)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from forms import DeathReportForm, InvestigationForm, KillReportForm, LynchVoteForm, MafiaPowerForm, \
    ConspiracyListForm, SignUpForm, InnocentChildRevealForm, SuperheroForm
from django.shortcuts import render
from settings import ROGUE_KILL_WAIT, MAYOR_COUNT_MAFIA_TIMES
from models import Player, Death, Game, Investigation, LynchVote, Item, Role, ConspiracyList, MafiaPower, Notification, \
    SuperheroDay
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
        return function(request, *args, **kwargs)

    return new_func


def message_seen(request, message):
    try:
        notification = Notification.objects.get(user=request.user, game__active=True, seen=False, content=message)
        notification.seen = True
        notification.save()
        return HttpResponse("Notified")

    except Notification.DoesNotExist:
        return HttpResponse("Oops")


@notifier
def index(request):
    params = {}
    if request.user.username == "admin":
        return HttpResponseRedirect("/admin")
    try:
        game = Game.objects.get(active=True)
    except Game.DoesNotExist:
        try:  # try again
            game = Game.objects.get(god=request.user, archived=False)
            return HttpResponseRedirect(reverse('forms:configure_game'))
        except Game.DoesNotExist:
            logout(request)
            return HttpResponseRedirect("/accounts/login")

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

        when = datetime.now() - timedelta(minutes=int(form.data['when']))
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
        today_day = me.superheroday_set.get(day=today)
        form = SuperheroForm(initial={'superhero_identity': today_day.superhero_identity,
                                      'paranoia': today_day.paranoia or me})
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
            me.game.log("%s has set superhero identity for day %d, with paranoia target %s." % (me, today + 1, paranoia), users_who_can_see=[me])
        else:
            me.game.log("%s has set secret identity for day %d" % (me, today + 1), users_who_can_see=[me])

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
            when = datetime.now() - timedelta(minutes=int(form.data['when']))
            kaboom = 'kaboom' in form.data
            try:
                Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom,
                                     day=Game.objects.get(active=True).current_day, where=where)
            except IndexError:
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
    if isinstance(request.user, AnonymousUser):
        return render(request, 'recent_deaths.html',
                      {'god': is_god, 'deaths': recents, 'game': game, 'user': request.user})
    elif game.has_user(request.user):
        player = Player.objects.get(user=request.user, game=game)
    else:
        player = {'god': is_god, 'game': game, 'username': request.user.username,
                  'role': {'name': "God" if is_god else "Guest"}}
    return render(request, 'recent_deaths.html', {'god': is_god, 'deaths': recents, 'player': player})


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
            if player.can_investigate(form.data['investigation_type'], death):
                guess = Player.objects.get(id=form.data['guess'])
                investigation = Investigation.objects.create(investigator=player, death=death, guess=guess,
                                                             investigation_type=form.data['investigation_type'],
                                                             day=game.current_day)
                game.log(message="%s investigates %s for the death of %s (answer: %s)" %
                                 (player, guess, death.murderee, "Correct" if investigation.is_correct() else "Wrong"),
                         users_who_can_see=[player])
                if investigation.is_correct():
                    messages.add_message(request, messages.SUCCESS, "Correct. <b>%s</b> killed <b>%s</b>."
                                         % (guess.user.username, death.murderee.user.username))
                else:
                    messages.add_message(request, messages.WARNING,
                                         "Your investigation turns up nothing. <b>%s</b> did not kill <b>%s</b>." % (
                                             guess.user.username, death.murderee.user.username))
                return HttpResponseRedirect("/")
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
                vote = LynchVote.objects.create(voter=player, lynchee=vote_value, time_made=datetime.now(),
                                                day=game.current_day)
                if vote_value:
                    vote_message = "%s voted to lynch %s" % (player, vote_value)
                else:
                    vote_message = "%s voted for no lynch" % player
                if player.elected_roles.filter(name="Mayor").exists():
                    vote.value = 3
                    vote.save()
                    vote_message += " (3x vote)"

                game.log(message=vote_message, users_who_can_see=[player])

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
    # TODO is_evil ?
    game = Game.objects.get(active=True)
    if request.user == game.god:
        messages.add_message(request, messages.WARNING, "Sorry, this view has not been implemented for you. Check the game log instead.")
        return HttpResponseRedirect("/")
    player = Player.objects.get(user=request.user, game__active=True)
    if player.is_alive():
        return render(request, "items.html", {'player': player, 'game': game})
    else:
        messages.add_message(request, messages.WARNING, "You're dead, so you can't use items. Check the game log instead.")
        return HttpResponseRedirect("/")

@notifier
@login_required
def destroy_item(request, id):
    current_item = Item.objects.get(id=id)
    player = Player.objects.get(user=request.user, game__active=True)
    if current_item.owner != player:
        messages.add_message(request, messages.WARNING, "That item does not belong to you.")
        return HttpResponseRedirect("/")
    current_item.owner = None
    player.game.log(message="%s has destroyed %s" %(player, current_item.get_name()), users_who_can_see=[player])
    current_item.save()
    return HttpResponseRedirect(reverse('items'))

@notifier
@login_required
def item(request, item_id, password):
    current_item = Item.objects.get(id=item_id)
    if current_item.password != password:
        return HttpResponseNotFound
    else:
        player = Player.objects.get(user=request.user, game__active=True)
        if player != current_item.owner:
            old_owner = current_item.owner
            current_item.owner = player
            messages.add_message(request, messages.SUCCESS,
                                 "You have successfully acquired <b>%s</b> from <b>%s</b>. <a href='/'>Return.</a>" % (
                                     current_item.name, old_owner.username))

        # using the item
        return HttpResponse("Using items is not yet implemented.")

@notifier
@login_required
def count_the_mafia(request):
    if Game.get(active=True).mafia_counts == MAYOR_COUNT_MAFIA_TIMES:
        messages.warning(request, "All mafia counts have been used.")
    try:
        player = Player.objects.get(user=request.user, game__active=True)
        if player.elected_roles.filter(name="Mayor").exists():
            mafia_count = sum(p.is_evil() for p in player.game.living_players)
            messages.info(request, "There are <b>%d</b> mafia remaining." % mafia_count)
            player.game.log("Mayor %s has counted the mafia and found that %d remain." % (player, mafia_count))
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
        player.game.log("%s  is going desperado tonight." % player, users_who_can_see=[player])
        player.save()
    return HttpResponseRedirect("/")

@notifier
@login_required
def undo_desperado(request):
    player = Player.objects.get(user=request.user, game__active=True, role__name__iexact="desperado")
    if player.role_information == Player.DESPERADO_ACTIVATING:
        player.role_information = Player.DESPERADO_INACTIVE
        player.game.log("%s is no longer going desperado tonight." % player, users_who_can_see=[player])
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
    if not Game.objects.filter(active=True).exists():
        return HttpResponseRedirect(reverse('past_games'))
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
def mafia_power_form(request):
    form = MafiaPowerForm(request, request.POST or None)
    player = Player.objects.get(user=request.user, game__active=True)
    if form.is_valid():
        message = form.submit(player)
        messages.add_message(request, messages.SUCCESS, message)
        return HttpResponseRedirect(reverse('mafia_powers'))
    else:
        if player.is_evil and player.is_alive:
            power = MafiaPower.objects.get(id=request.GET['power_id'])
            return render(request, "form.html",
                          {'form': form, 'player': player, "title": "Use a Mafia Power: %s" % power,
                           'url': reverse('forms:mafia_power')})
        elif not player.is_alive:
            messages.add_message(request, messages.WARNING, "You're dead, you can't do mafia things!")
            return HttpResponseRedirect(reverse("mafia_powers"))
        else:
            messages.add_message(request, messages.WARNING, "You're not mafia, you can't do mafia things!")
            return HttpResponseRedirect("/")


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
        for player in game.player_set:
            player.notify("Game has ended - check forums to see who won.", bad=False)
    return HttpResponseRedirect("/")


@login_required
def evict_player(request, pid):
    game = Game.objects.get(active=True)
    if request.user == game.god:
        player = Player.objects.get(id=pid)
        Death.objects.create(murderee=player, day=player.game.current_day, when=datetime.now(),
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
        game.log("%s ressurected by %s" % (player, game.god.username))
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
        conspiracy.save()
        player.game.log(
            message="%s has updated their conspiracy list for day %d to: [%s]" % (player, player.game.current_day + 1,
                                                                                  ", ".join(consp_list)),
            users_who_can_see=[player])
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
                 log_item.visible_to(request.user)]
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
    return render(request, "form.html", {'player': player, 'form': form})


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

    return HttpResponse("Not implemented yet")


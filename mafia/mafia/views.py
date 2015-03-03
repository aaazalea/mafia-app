from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser, User
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.shortcuts import resolve_url
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import (REDIRECT_FIELD_NAME, login as auth_login, logout)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from forms import DeathReportForm, InvestigationForm, KillReportForm, LynchVoteForm, MafiaPowerForm, \
    ConspiracyListForm, SignUpForm
from django.shortcuts import render
from models import Player, Death, Game, Investigation, LynchVote, Item, Role, ConspiracyList, MafiaPower, Notification
from django.core.urlresolvers import reverse


def notifier(function):
    def new_func(request, *args, **kwargs):
        try:
            unread = Notification.objects.filter(user=request.user, game__active=True, seen=False)
            for message in unread:
                if message.is_bad:
                    messages.error(request, message.content)
                else:
                    messages.info(request, message.content)
                message.seen = True
                message.save()
        finally:
            return function(request, *args, **kwargs)

    return new_func


@notifier
def index(request):
    params = {}
    if request.user.username == "admin":
        return HttpResponseRedirect("/admin")
    try:
        game = Game.objects.get(active=True)
    except Game.DoesNotExist:
        logout(request)
        return HttpResponseRedirect("/accounts/login")
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

    params['recent_deaths'] = Death.objects.filter(murderee__game__active=True).order_by('-when')[:10]

    return render(request, 'index.html',
                  params)


@notifier
@login_required
def death_report(request):
    if request.method == "POST":
        form = DeathReportForm(request.POST)
        if form.is_valid():
            where = form.data['where']
            killer = Player.objects.get(id=form.data['killer'])
            killed = Player.objects.get(user=request.user, game__active=True)
            if not killed.alive:
                messages.add_message(request, messages.WARNING, "You're already dead.")
                return HttpResponseRedirect("/")
            when = datetime.now() - timedelta(minutes=int(form.data['when']))
            kaboom = 'kaboom' in form.data
            Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom, where=where,
                                 day=Game.objects.get(active=True).current_day)
            return HttpResponseRedirect("/")

    else:
        try:
            me = Player.objects.get(user=request.user, game__active=True)
        except Player.DoesNotExist:
            return HttpResponse("You don't have a role in any currently active game.")
        if me.is_alive():
            form = DeathReportForm()
            return render(request, 'form.html', {'form': form, 'player': me, 'title': 'Report your own death',
                                                 'url': reverse('forms:death')})
        else:
            messages.add_message(request, messages.ERROR, "You're dead already")
            return HttpResponseRedirect("/")


@notifier
@login_required
def kill_report(request):
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
    recents = Death.objects.filter(murderee__game__active=True).order_by('-when')
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
    if request.user == game.god:
        # TODO What should this page return?
        pass
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
def daily_lynch(request, day):
    try:
        player = Player.objects.get(user=request.user, game__active=True)
    except Player.DoesNotExist:
        player = False
    # TODO implement tiebreaker
    # TODO mayor triple vote
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

    if not Death.objects.filter(murderer__game=game).exists():
        messages.add_message(request, messages.INFO, "You can't lynch anyone yet - nobody has been killed.")
        return HttpResponseRedirect("/")
    if player.is_alive():
        if request.method == "POST":
            form = LynchVoteForm(request.POST)
            if form.is_valid():
                vote_value = Player.objects.get(id=form.data["vote"])
                vote = LynchVote.objects.create(voter=player, lynchee=vote_value, time_made=datetime.now(),
                                                day=game.current_day)
                vote_message = "%s voted to lynch %s" % (player, vote_value)
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
        if password != confirm_password:
            messages.error(request, "Password must match confirmation")
            return render('sign_up.html', {'form': form, 'game': game})

        if password == '':
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                messages.error(request, "You don't have an account; please set a password.")
                return render('sign_up.html', {'form': form, 'game': game})
        else:
            user = User.objects.create(username=username)
            user.set_password(password)
            user.email = email
            user.save()
        Player.objects.create(user=user, game=game, introduction=intro, photo=picture)

        return HttpResponse("You signed up for mafia game \"%s\" successfully" % game.name)

    return render(request, 'sign_up.html', {'form': form, 'game': game})


@notifier
@login_required
def go_desperado(request):
    player = Player.objects.get(user=request.user, game__active=True, role__name__iexact="desperado")
    if player.role_information == Player.DESPERADO_INACTIVE:
        player.role_information = Player.DESPERADO_ACTIVATING
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
        return HttpResponse("There is no active mafia game. <a href=\"/admin\">Log in as admin</a>.")
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
        if player.is_evil:
            power = MafiaPower.objects.get(id=request.GET['power_id'])
            return render(request, "form.html",
                          {'form': form, 'player': player, "title": "Use a Mafia Power: %s" % power,
                           'url': reverse('forms:mafia_power')})
        else:
            messages.add_message(request, messages.WARNING, "You're not mafia, you can't do mafia things!")
            return HttpResponseRedirect("/")


@notifier
@login_required
def mafia_powers(request):
    game = Game.objects.get(active=True)
    if request.user == game.god:
        return render(request, "mafia_powers.html", {'user': request.user, 'game': game})
    player = Player.objects.get(user=request.user, game__active=True)
    if player.is_evil:
        return render(request, "mafia_powers.html", {'player': player, 'game': game})
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
    return HttpResponseRedirect("/")


@login_required
def evict_player(request, pid):
    game = Game.objects.get(active=True)
    if request.user == game.god:
        player = Player.objects.get(id=pid)
        Death.objects.create(murderee=player, day=player.game.current_day, when=datetime.now(),
                             where="Evicted (day %d)" % player.game.current_day)
        messages.success(request, "%s removed from game" % player.username)
    return HttpResponseRedirect(reverse('player_intros'))


@login_required
def resurrect_player(request, pid):
    game = Game.objects.get(active=True)
    if request.user == game.god:
        player = Player.objects.get(id=pid)
        Death.objects.get(murderee=player).delete()
        messages.success(request, "%s resurrected" % player.username)
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

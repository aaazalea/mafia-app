from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
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
from forms import DeathReportForm, InvestigationForm, KillReportForm, LynchVoteForm
from django.shortcuts import render
from models import Player, Death, Game, Investigation, LynchVote, Item
from django.core.urlresolvers import reverse

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
            return render(request, 'death_report.html', {'form': form, 'player': me})
        else:
            messages.add_message(request, messages.ERROR, "You're dead already")
            return HttpResponseRedirect("/")


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
            Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom,
                                 day=Game.objects.get(active=True).current_day, where=where)
            return HttpResponseRedirect("/")

    else:
        player = Player.objects.get(user=request.user, game__active=True)
        if player.is_alive():
            form = KillReportForm()

            return render(request, 'kill_report.html', {'form': form, 'player': player})
        else:
            messages.add_message(request, messages.ERROR, "You're dead already")
            return HttpResponseRedirect("/")


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

    current_lynch_vote = player.lynch_vote_made(game.current_day)
    recents = Death.objects.filter(murderee__game__active=True).order_by('-when')[:10]

    return render(request, 'your_role.html',
                  {'player': player})


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

        return render(request, 'investigation_form.html', {'form': form})
    else:
        messages.add_message(request, messages.ERROR, "Dead people can't make investigations.")

    return HttpResponseRedirect("/")


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
                if player.elected_roles.filter(name="Mayor").exists():
                    vote.value = 3
                    vote.save()
                return HttpResponseRedirect("/")
        else:
            form = LynchVoteForm()

            return render(request, 'lynch_vote.html', {'form': form, 'player': player})
    else:
        messages.add_message(request, messages.ERROR, "Dead people don't vote. :(")
        return HttpResponseRedirect("/")


@login_required
def item(request, id, password):
    item = Item.objects.get(id=id)
    if item.password != password:
        return HttpResponseNotFound
    else:
        player = Player.objects.get(user=request.user, game__active=True)
        if player != item.owner:
            old_owner = item.owner
            item.owner = player
            messages.add_message(request, messages.SUCCESS,
                                 "You have successfully acquired <b>%s</b> from <b>%s</b>. <a href='/'>Return.</a>" % (
                                     item.name, old_owner.username))

        # using the item
        return HttpResponse("Using items is not yet implemented.")


def sign_up(request):
    pass


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


@login_required
def advance_day(request):
    game = Game.objects.get(active=True)
    if request.user == game.god:
        game.increment_day()
    return HttpResponseRedirect("/")


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

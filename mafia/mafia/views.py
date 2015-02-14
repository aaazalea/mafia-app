from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from forms import DeathReportForm, InvestigationForm, KillReportForm, LynchVoteForm
from django.shortcuts import render
from models import Player, Death, Game, Investigation, LynchVote, Item, Role
from django.core.urlresolvers import reverse


def index(request):
    return HttpResponseRedirect('/your-role')


@login_required
def death_report(request):
    if request.method == "POST":
        form = DeathReportForm(request.POST)
        if form.is_valid():
            where = form.data['where']
            killer = Player.objects.get(id=form.data['killer'])
            killed = Player.objects.get(user=request.user, game__active=True)
            when = datetime.now() - timedelta(minutes=int(form.data['when']))
            kaboom = 'kaboom' in form.data
            Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom, where=where,
                                 day=Game.objects.get(active=True).current_day)
            return HttpResponseRedirect("/")

    else:
        try:
            me = Player.objects.get(user=request.user, game__active=True)
            if me.is_alive():
                form = DeathReportForm()

                return render(request, 'death_report.html', {'form': form, 'player': me})
            else:
                return HttpResponse("You're dead already")
        except:
            return HttpResponse("You don't have a role in any currently active game.")


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
            mtp = 'mtp' in form.data
            Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom, mtp=mtp,
                                 day=Game.objects.get(active=True).current_day, where=where)
            return HttpResponseRedirect("/")

    else:
        if Player.objects.get(user=request.user, game__active=True).is_alive():
            form = KillReportForm()

            return render(request, 'kill_report.html', {'form': form})
        else:
            return HttpResponse("You're dead already")


@login_required
def recent_deaths(request):
    game = Game.objects.get(active=True)
    is_god = request.user == game.god
    recents = Death.objects.filter(murderee__game__active=True).order_by('-when')
    if game.has_user(request.user):
        player = Player.objects.get(user=request.user, game=game)
    else:
        player = {'game': game, 'username': request.user.username, 'role': {'name': "Guest"}}
    return render(request, 'recent_deaths.html', {'god': is_god, 'deaths': recents, 'player': player})

@login_required
def your_role(request):
    if request.user.username == "admin":
        return HttpResponseRedirect("/admin")
    game = Game.objects.get(active=True)
    try:
        player = Player.objects.get(game=game, user=request.user)
    except:
        return HttpResponse("You're not playing in this game. <a href='/logout'>Please log out and try again.</a>")
    additional_info = player.additional_info()
    links = [(reverse('death_report'), "I died.")]
    if player.can_make_kills():
        links.append((reverse('kill_report'), "Report a kill you made"))
    if player.can_investigate():
        links.append((reverse('investigation_form'), "Make an investigation"))
    if player.role == Role.objects.get(name="Desperado") and player.role_information == Player.DESPERADO_INACTIVE:
        links.append((
            "javascript:if(confirm('Are you sure you want to go desperado?')==true){window.location.href='%s'}" % reverse(
                'go_desperado'), "Go desperado"))
    current_lynch_vote = player.lynch_vote_made(game.current_day)

    recents = Death.objects.filter(murderee__game__active=True).order_by('-when')[:10]


    return render(request, 'your_role.html',
                  {'links': links,
                   'vote': current_lynch_vote,
                   'player': player,
                   'recent_deaths': recents})


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
                    return HttpResponse("Correct. <b>%s</b> killed <b>%s</b>. <a href='%s'>Return</a>"
                                        % (guess.user.username, death.murderee.user.username, reverse('index')))
                else:
                    return HttpResponse(
                        "Your investigation turns up nothing. <b>%s</b> did not kill <b>%s</b>. <a href='%s'>Return</a>" % (guess.user.username, death.murderee.user.username, reverse('index')))
            else:
                return HttpResponse("You can't use that kind of investigation.")
        else:
            return HttpResponse("Invalid investigation. <a href=\"%s\"> Try again</a>" % reverse('investigation_form'))
    else:
        if Player.objects.get(user=request.user, game__active=True).is_alive():
            form = InvestigationForm()

            return render(request, 'investigation_form.html', {'form': form})
        else:
            return HttpResponse("You're dead already")

@login_required
def daily_lynch(request, day):
    player = Player.objects.get(user=request.user, game__active=True)
    # TODO implement tiebreaker
    # TODO mayor triple vote
    game = Game.objects.get(active=True)

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
    if player.is_alive():
        if request.method == "POST":
            form = LynchVoteForm(request.POST)
            if form.is_valid():
                vote = Player.objects.get(id=form.data["vote"])
                LynchVote.objects.create(voter=player, lynchee=vote, time_made=datetime.now(), day=game.current_day)
                return HttpResponseRedirect("/")
        else:
            form = LynchVoteForm()

            return render(request, 'lynch_vote.html', {'form': form, 'player': player})
    else:
        return HttpResponse("Dead people don't vote. :(")

@login_required
def item(request, id, password):
    item = Item.objects.get(id=id)
    if item.password != password:
        return HttpResponseNotFound
    else:
        player = Player.objects.get(user=request.user, game__active=True)
        if player == item.owner:
            # Using the item
            return HttpResponse("Using items is not yet implemented.")
        else:
            old_owner = item.owner
            item.owner = player
            return HttpResponse("You have successfully acquired <b>%s</b> from <b>%s</b>. <a href='/'>Return.</a>" % (
                item.name, old_owner.username))

def sign_up(request):
    pass


@login_required
def go_desperado(request):
    player = Player.objects.get(user=request.user, game__active=True, role__name__iexact="desperado")
    if player.role_information == Player.DESPERADO_INACTIVE:
        player.role_information = Player.DESPERADO_ACTIVATING
        player.save()
    return HttpResponseRedirect("/")


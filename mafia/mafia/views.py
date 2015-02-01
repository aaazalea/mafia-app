from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from forms import DeathReportForm, InvestigationForm, KillReportForm
from django.shortcuts import render
from models import Player, Death, Game, Investigation
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
            death = Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom, where=where)
            return HttpResponseRedirect("/")

    else:
        try:
            if Player.objects.get(user=request.user, game__active=True).is_alive():
                form = DeathReportForm()

                return render(request, 'death_report.html', {'form': form})
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
            death = Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom, mtp=mtp,
                                         where=where)
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
    recents = Death.objects.filter(murderer__game__active=True).order_by('-when')
    return render(request, 'recent_deaths.html', {'god': is_god, 'deaths': recents})

@login_required
def your_role(request):
    if request.user.username == "admin":
        return HttpResponseRedirect("/admin")
    game = Game.objects.get(active=True)
    try:
        player = Player.objects.get(game=game, user=request.user)
    except:
        return HttpResponse("You're not playing in this game. <a href='/logout'>Please log out and try again.</a>")
    username = request.user.username
    role = player.role
    additional_info = player.additional_info()
    links = [(reverse('death_report'), "I died.")]
    if player.can_make_kills():
        links.append((reverse('kill_report'), "Report a kill you made"))
    if player.can_investigate():
        links.append((reverse('investigation_form'), "Make an investigation"))
    return render(request, 'your_role.html',
                  {'game': game,
                   'role': role,
                   'extra': additional_info,
                   'username': username,
                   'links': links,
                   'alive': player.is_alive()})

@login_required
def investigation_form(request):
    game = Game.objects.get(active=True)
    player = Player.objects.get(game=game, user=request.user)
    if request.method == "POST":
        form = InvestigationForm(request.POST)
        if form.is_valid():
            if player.can_investigate():
                death = Death.objects.get(id=form.data["death"])
                guess = Player.objects.get(id=form.data['guess'])
                investigation = Investigation.objects.create(investigator=player, death=death, guess=guess,
                                                             investigation_type=form.data['investigation_type'])
                if investigation.is_correct():
                    return HttpResponse("Correct. <b>%s</b> killed <b>%s</b>. <a href='%s'>Return</a>"
                                        % (guess.user.username,death.murderee.user.username, reverse('index')))
                else:
                    return HttpResponse(
                        "Your investigation turns up nothing. <b>%s</b> did not kill <b>%s</b>. <a href='%s'>Return</a>" % (guess.user.username, death.murderee.user.username, reverse('index')))
        else:
            return "Invalid investigation. <a href=\"%s\"> Try again</a>" % reverse('investigation_form')
    else:
        if Player.objects.get(user=request.user, game__active=True).is_alive():
            form = InvestigationForm()

            return render(request, 'investigation_form.html', {'form': form})
        else:
            return HttpResponse("You're dead already")

def daily_lynch(request, day):
    # TODO implement tiebreaker
    # TODO mayor triple vote
    game = Game.objects.get(active=True)

    choices = []
    for player in Player.objects.all():
        votes = player.lynch_votes_for(day)
        if votes:
            choices.append((len(votes), votes, player))

    choices.sort(key=lambda c: -c[0])

    lynchee = choices[0][2]

    return render(request, 'daily_lynch.html', {'lynchee': lynchee,
                                                'choices': choices,
                                                'game': game,
                                                'day': day})


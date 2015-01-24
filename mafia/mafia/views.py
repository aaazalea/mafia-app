from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect,HttpResponse
from forms import DeathReportForm
from django.shortcuts import render
from datetime import datetime,timedelta
from models import Player, Death, Game


def index(request):
    return HttpResponse("This is the main mafia page.")

@login_required
def death_report(request):
    if request.method == "POST":
        form = DeathReportForm(request.POST)
        if form.is_valid():
            killer = Player.objects.get(id=form.data['killer'])
            killed = Player.objects.get(user=request.user,game__active=True)
            when = datetime.now()-timedelta(minutes=int(form.data['when']))
            kaboom = 'kaboom' in form.data
            death = Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom)
            return HttpResponseRedirect("/")

    else:
        try:
            if Player.objects.get(user=request.user,game__active=True).is_alive():
                form = DeathReportForm()

                return render(request, 'death_report.html', {'form': form})
            else:
                return HttpResponse("You're dead already")
        except:
            return HttpResponse("You don't have a role in any currently active game.")

@login_required
def kill_report(request):
    if request.method == "POST":
        form = DeathReportForm(request.POST)
        if form.is_valid():
            killed = Player.objects.get(id=form.data['killed'])
            killer = Player.objects.get(user=request.user,game__active=True)
            when = datetime.now()-timedelta(minutes=int(form.data['when']))
            kaboom = 'kaboom' in form.data
            mtp = 'mtp' in form.data
            death = Death.objects.create(when=when, murderer=killer, murderee=killed, kaboom=kaboom, mtp=mtp)
            return HttpResponseRedirect("/")

    else:
        try:
            if Player.objects.get(user=request.user,game__active=True).is_alive():
                form = DeathReportForm()

                return render(request, 'death_report.html', {'form': form})
            else:
                return HttpResponse("You're dead already")
        except:
            return HttpResponse("You don't have a role in any currently active game.")


@login_required
def recent_deaths(request):
    game = Game.objects.get(active=True)
    is_god = request.user == game.god
    print request.user,game.god
    recents = Death.objects.filter(murderer__game__active=True).order_by('-when')
    return render(request,'recent_deaths.html',{'god': is_god, 'deaths': recents })

def your_role(request):
    game = Game.objects.get(active=True)
    player = Player.objects.get(game=game,user=request.user)
    username = request.user.username
    role = player.role
    additional_info = player.additional_info()
    return render(request, 'your_role.html',
                  {'game': game,
                   'role': role,
                   'extra': additional_info,
                   'username': username})
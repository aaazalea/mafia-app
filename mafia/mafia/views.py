from django.http import HttpResponseRedirect
from forms import DeathReportForm
from django.shortcuts import render


def index(request):
    return HttpResponse("This is the main mafia page.")

def death_report(request):
    if request.method == "POST":
        form  = DeathReportForm(request.POST)

        if form.is_valid():
            print form
            print dir(form)
            return HTTPResponseRedirect("/")

    else:
        form = DeathReportForm()

        return render(request, 'report.html', {'form': form})

from django import forms
from django.core.exceptions import ValidationError

from models import *


class DeathReportForm(forms.Form):
    killer = forms.ModelChoiceField(
        queryset=Player.objects.filter(game__active=True),
        label='Who killed you?')
    kaboom = forms.BooleanField(
        initial=False, required=False,
        label="Was a kaboom used?")
    when = forms.IntegerField(label="How many minutes ago were you killed?")

class KillReportForm(forms.Form):
    killed = forms.ModelChoiceField(
        queryset=Player.objects.filter(game__active=True),
        label='Who did you kill?')
    kaboom = forms.BooleanField(initial=False, required=False,
                                label="Was a kaboom used?")
    when = forms.IntegerField(label="How many minutes did this happen?")
    mtp = forms.BooleanField(initial=False, required=False,
                             label="Manipulate the press?")

class InvestigationForm(forms.Form):
    death = forms.ModelChoiceField(
        queryset=Death.objects.filter(murderer__game__active=True),
        label="Which death would you like to investigate?",
        to_field_name='murderee')
    guess = forms.ModelChoiceField(
        queryset=Player.objects.filter(game__active=True),
        label="Whom would you like to investigate?"
    )
    kind = forms.MultipleChoiceField(choices=Investigation.INVESTIGATION_KINDS,
                                     label="What kind of investigation are you using? [choose one you're allowed to]",
                                     )

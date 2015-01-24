from django import forms
from django.core.exceptions import ValidationError

from mafia.models import *


class DeathReportForm(forms.Form):
    killer = forms.ModelChoiceField(queryset=Player.objects.filter(game__active=True),label='Who killed you?')

from django import forms

from models import *


class PlayerModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.user.username


class DeathReportForm(forms.Form):
    killer = PlayerModelChoiceField(
        queryset=Player.objects.filter(game__active=True),
        label='Who killed you?')
    kaboom = forms.BooleanField(
        initial=False, required=False,
        label="Was a kaboom used?")
    when = forms.IntegerField(label="How many minutes ago were you killed?")
    where = forms.CharField(label='Where were you killed?')


class KillReportForm(forms.Form):
    killed = PlayerModelChoiceField(
        queryset=Player.objects.filter(game__active=True, death=None),
        label='Who did you kill?')
    kaboom = forms.BooleanField(initial=False, required=False,
                                label="Was a kaboom used?")
    when = forms.IntegerField(label="How many minutes ago did this happen?")

    where = forms.CharField(label='Where did this happen?')


class DeathModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.murderee.user.username


class InvestigationForm(forms.Form):
    death = DeathModelChoiceField(
        queryset=Death.objects.filter(murderer__game__active=True),
        label="Which death would you like to investigate?",
    )
    guess = PlayerModelChoiceField(
        queryset=Player.objects.filter(game__active=True),
        label="Whom would you like to investigate?"
    )
    investigation_type = forms.ChoiceField(choices=Investigation.INVESTIGATION_KINDS,
                                           label="What kind of investigation are you using? [choose one you're allowed to]"
    )


class LynchVoteForm(forms.Form):
    vote = PlayerModelChoiceField(
        queryset=Player.objects.filter(game__active=True, death=None),
        label="Whom do you want to lynch?"
    )


class SignUpForm(forms.Form):
    username = forms.CharField(max_length=30, label="Username (The same as on mafia.mit.edu, except for spaces)")
    password = forms.CharField(max_length=200, label="Password: ", widget=forms.PasswordInput())
    confirm_password = forms.CharField(max_length=200, label="Confirm password: ", widget=forms.PasswordInput())
    email = forms.EmailField(max_length=50, label="Email Address:")
    game = forms.ModelChoiceField(
        queryset=Game.objects.filter(archived=False),
        label="Choose a game to join:"
    )


class MafiaPowerForm(forms.Form):
    target = forms.ModelChoiceField(queryset=Player.objects.filter(game__active=True))

    def __init__(self, request, *args, **kwargs):
        super(MafiaPowerForm, self).__init__(*args, **kwargs)
        if 'power_id' in request.GET:
            power = MafiaPower.objects.get(id=request.GET['power_id'])
            need = power.needs_extra_field()
            if need:
                self.fields['extra_field'] = need
            self.fields['power_id'] = forms.IntegerField(widget=forms.HiddenInput(), initial=power.id)

    def submit(self):
        power = MafiaPower.objects.get(id=self.data['power_id'])
        if power.power == MafiaPower.POISON:
            person_poisoned = Player.objects.get(id=self.data['target'])
            pass
        if power.power == MafiaPower.SET_A_TRAP:
            person_trapped = Player.objects.get(id=self.data['target'])
            role_guess = Role.objects.get(id=self.data['extra_field'])
            pass
        if power.power == MafiaPower.SLAUGHTER_THE_WEAK:
            person_slaughtered = Player.objects.get(id=self.data['target'])
            pass
        if power.power == MafiaPower.FRAME_A_TOWNSPERSON:
            person_framed = Player.objects.get(id=self.data['target'])
            person_killed = Player.objects.get(id=self.data['extra_field'])
            pass
        if power.power == MafiaPower.PLANT_EVIDENCE:
            pass
        if power.power == MafiaPower.MANIPULATE_THE_PRESS:
            pass
        if power.power == MafiaPower.HIRE_A_HITMAN:
            pass
        if power.power == MafiaPower.CONSCRIPTION:
            pass

        return "Power executed successfully: %s" % power.get_power_name()

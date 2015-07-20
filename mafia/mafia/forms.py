from math import ceil

from django.core.exceptions import ValidationError
from django.forms import ModelMultipleChoiceField
from models import *
from settings import *


class PlayerModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.username


class DeathReportForm(forms.Form):
    killer = PlayerModelChoiceField(
        queryset=Player.objects.filter(game__active=True),
        label='Who killed you?')
    kaboom = forms.BooleanField(
        initial=False, required=False,
        label="Was a kaboom used?")
    when = forms.IntegerField(label="How many minutes ago were you killed?", min_value=0)
    where = forms.CharField(label='Where were you killed?')


class KillReportForm(forms.Form):
    killed = PlayerModelChoiceField(
        queryset=Player.objects.filter(game__active=True, death=None),
        label='Who did you kill?')
    kaboom = forms.BooleanField(initial=False, required=False,
                                label="Was a kaboom used?")
    when = forms.IntegerField(label="How many minutes ago did this happen?", min_value=0)

    where = forms.CharField(label='Where did this happen?')


class DeathModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.murderee.user.username


class InvestigationForm(forms.Form):
    death = DeathModelChoiceField(
        queryset=Death.objects.filter(Q(murderer__game__active=True)|Q(murderee__mafiapowers_targeted_set__power=MafiaPower.HIRE_A_HITMAN)).distinct(),
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
        label="Whom do you want to lynch?",
        empty_label="No Lynch",
        required=not NO_LYNCH_ALLOWED
    )


class SignUpForm(forms.Form):
    username = forms.CharField(max_length=30, label="Username")
    password = forms.CharField(max_length=200, label="Password: ",
                               widget=forms.PasswordInput(),
                               required=True)
    confirm_password = forms.CharField(max_length=200,
                                       label="Confirm password: ",
                                       widget=forms.PasswordInput(),
                                       required=False)
    email = forms.EmailField(max_length=50, label="Email Address:",
                             required=False)
    introduction = forms.CharField(label="Introduction:", )
    picture = forms.CharField(label="Picture URL")


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
            if power.power in [MafiaPower.SET_A_TRAP, MafiaPower.SLAUGHTER_THE_WEAK, MafiaPower.CONSCRIPTION]:
                self.fields['target'] = forms.ModelChoiceField(
                    queryset=Player.objects.filter(death=None, game__active=True))

    def submit(self, user):
        charge = MafiaPower.objects.get(id=self.data['power_id'])
        if charge.power == MafiaPower.SET_A_TRAP:
            if (not TRAPS_REGENERATE) and TRAPS_AT_A_TIME <= len(
                    MafiaPower.objects.filter(power=MafiaPower.SET_A_TRAP, state=MafiaPower.SET, game__active=True)):
                raise ValidationError(
                    "The maximum number of set a trap charges (%s) is already in use." % TRAPS_AT_A_TIME)
            if MafiaPower.objects.filter(power=MafiaPower.SET_A_TRAP, game__active=True, day_used=charge.game.current_day).exists():
                raise ValidationError(
                    "A trap has already been set today. Wait to set another one tomorrow.")
        response = "Power executed successfully: %s" % charge.get_power_name()
        charge.target = Player.objects.get(id=self.data['target'])
        charge.state = MafiaPower.USED
        charge.day_used = charge.target.game.current_day
        charge.user = user

        if charge.power == MafiaPower.SET_A_TRAP:
            role_guess = Role.objects.get(id=self.data['extra_field'])
            charge.user = None
            if charge.target.role == role_guess:
                charge.state = MafiaPower.SET
                response = "Trap set successfully on %s" % charge.target
            else:
                charge.comment = "Incorrect, %s is not a %s." % (charge.target, role_guess)
                response = "Incorrect guess - trap failed."

        elif charge.power == MafiaPower.SLAUGHTER_THE_WEAK:
            charge.user = None
            if charge.target.role == Role.objects.get(name__iexact="Innocent Child"):
                charge.state = MafiaPower.SET
                response = "Charge set successfully on %s" % charge.target
            else:
                charge.comment = "Incorrect, %s is not an innocent child." % charge.target
                response = "Incorrect guess - slaughter failed."
        elif charge.power == MafiaPower.FRAME_A_TOWNSPERSON or charge.power == MafiaPower.PLANT_EVIDENCE:
            charge.other_info = self.data['extra_field']
        elif charge.power == MafiaPower.HIRE_A_HITMAN:
            charge.comment = self.data['extra_field']
            charge.state = MafiaPower.SET
            charge.other_info = 0
        elif charge.power == MafiaPower.CONSCRIPTION:
            charge.target.conscript()
        elif charge.power == MafiaPower.MANIPULATE_THE_PRESS:
            a = Death.objects.filter(murderee=charge.target, murderer__isnull=False)
            if a.exists():
                death = a[0]
                death.total_clues = 0
                death.save()
        charge.save()

        charge.target.game.log(message=charge.get_log_message(), mafia_can_see=True)

        return response


class ConspiracyListForm(forms.Form):
    new_conspiracy_list = forms.ModelMultipleChoiceField(queryset=Player.objects.filter(game__active=True, death=None))
    person_to_remove = forms.ModelChoiceField(Player.objects.filter(game__active=True, death=None),
                                              label="Who would you remove if game got smaller?")
    backup1 = forms.ModelChoiceField(Player.objects.filter(game__active=True, death=None),
                                     label="Backup 1, in case someone dies", required=False)
    backup2 = forms.ModelChoiceField(Player.objects.filter(game__active=True, death=None),
                                     label="Backup 2, in case someone dies", required=False)
    backup3 = forms.ModelChoiceField(Player.objects.filter(game__active=True, death=None),
                                     label="Backup 3, in case someone dies", required=False)

    def clean_new_conspiracy_list(self):
        conspiracy_size = len(self.cleaned_data['new_conspiracy_list'])
        if CONSPIRACY_LIST_SIZE_IS_PERCENT:
            if conspiracy_size > ceil(Game.objects.get(
                    active=True).number_of_living_players * 0.01 * CONSPIRACY_LIST_SIZE):
                raise ValidationError(
                    "You may only have %d%% of game on your conspiracy list (rounded up)." % CONSPIRACY_LIST_SIZE)
        else:
            if conspiracy_size > CONSPIRACY_LIST_SIZE:
                raise ValidationError("You may only have %d people on your conspiracy list." % CONSPIRACY_LIST_SIZE)
        return self.cleaned_data['new_conspiracy_list']

    def clean(self):
        if self.cleaned_data['backup1'] and (self.cleaned_data['backup1'] == self.cleaned_data['backup2'] or self.cleaned_data['backup3'] == self.cleaned_data['backup1']) or (self.cleaned_data['backup2'] and self.cleaned_data['backup2'] == self.cleaned_data['backup3']):
            raise ValidationError(
                    "You should not have multiple identical backups")


class CynicListForm(forms.Form):
    new_cynic_list = forms.ModelMultipleChoiceField(queryset=Player.objects.filter(game__active=True, death=None))
    person_to_remove = forms.ModelChoiceField(Player.objects.filter(game__active=True, death=None),
                                              label="Who would you remove if game got smaller?")
    backup1 = forms.ModelChoiceField(Player.objects.filter(game__active=True, death=None),
                                     label="Backup 1, in case someone dies", required=False)
    backup2 = forms.ModelChoiceField(Player.objects.filter(game__active=True, death=None),
                                     label="Backup 2, in case someone dies", required=False)
    backup3 = forms.ModelChoiceField(Player.objects.filter(game__active=True, death=None),
                                     label="Backup 3, in case someone dies", required=False)

    def clean_new_cynic_list(self):
        cynicism_size = len(self.cleaned_data['new_cynic_list'])
        if CYNIC_LIST_SIZE_IS_PERCENT:
            if cynicism_size > ceil(Game.objects.get(
                    active=True).number_of_living_players * 0.01 * CYNIC_LIST_SIZE):
                raise ValidationError(
                    "You may only have %d%% of game on your cynic list (rounded up)." % CYNIC_LIST_SIZE)
        else:
            if cynicism_size > CYNIC_LIST_SIZE:
                raise ValidationError("You may only have %d people on your cynic list." % CYNIC_LIST_SIZE)
        return self.cleaned_data['new_cynic_list']

    def clean(self):
        if self.cleaned_data['backup1'] and (self.cleaned_data['backup1'] == self.cleaned_data['backup2'] or self.cleaned_data['backup3'] == self.cleaned_data['backup1']) or (self.cleaned_data['backup2'] and self.cleaned_data['backup2'] == self.cleaned_data['backup3']):
            raise ValidationError(
                    "You should not have multiple identical backups")



class InnocentChildRevealForm(forms.Form):
    players_revealed_to = ModelMultipleChoiceField(Player.objects.filter(game__active=True, death=None),
                                                   label="Reveal to whom?")


class SuperheroForm(forms.Form):
    superhero_identity = forms.BooleanField(label="Will you be in superhero identity tomorrow?", required=False)
    paranoia = forms.ModelChoiceField(Player.objects.filter(death__isnull=True, game__active=True),
                                      label="Please choose a person for paranoia tomorrow "
                                            "(if you are going to be in secret identity, this will be ignored)",
                                      empty_label=None)


class ElectForm(forms.Form):
    player_elected = forms.ModelChoiceField(Player.objects.filter(death__isnull=True, game__active=True),
                                            label="Who is being elected?")
    position = forms.ModelChoiceField(ElectedRole.objects.all(),
        label="What position are they being elected to?")


class HitmanSuccessForm(forms.Form):
    hitman = forms.ModelChoiceField(
        queryset=MafiaPower.objects.filter(power=MafiaPower.HIRE_A_HITMAN, state=MafiaPower.USED, game__active=True),
        label='Which hitman?', empty_label=None)
    kaboom = forms.BooleanField(initial=False, required=False,
                                label="Was a kaboom used?")
    when = forms.IntegerField(label="How many minutes ago did this happen?", min_value=0)

    where = forms.CharField(label='Where did this happen?')


class ItemUseForm(forms.Form):
    def __init__(self, item, *args, **kwargs):
        super(ItemUseForm, self).__init__(*args, initial={'item': item.id}, **kwargs)
        if item.type == Item.SHOVEL:
            self.fields['target'] = forms.ModelChoiceField(Player.objects.filter(death__isnull=False, game=item.game),
                                                           label="Shovel whom?")
        elif item.type == Item.TASER:
            self.fields['target'] = forms.ModelChoiceField(Player.objects.filter(death__isnull=True, game=item.game),
                                                           label="Whom did you taser?")
        elif item.type == Item.CAMERA:
            self.fields['target'] = forms.CharField(max_length=100, label="Where did you place the camera?")

    item = forms.IntegerField(widget=forms.HiddenInput())


class CCTVModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, cctv):
        camera = Item.objects.get(type=Item.CAMERA, number=cctv.number, game=cctv.game)
        broken = "Broken " if cctv.result else ""
        return "%sCCTV %d (camera in \"%s\", CCTV held by %s)" % (broken, cctv.number, camera.result, cctv.owner)


class CCTVDeathModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, death):
        return "%s (killed in %s)" % (death.murderee, death.where)


class CCTVDeathForm(forms.Form):
    cctv = CCTVModelChoiceField(Item.objects.filter(type=Item.CCTV, game__active=True), empty_label=None,
                                label="Which CCTV?")
    death = CCTVDeathModelChoiceField(Death.objects.filter(murderee__game__active=True, murderer__isnull=False))


class WatchListForm(forms.Form):
    day = forms.IntegerField(min_value=1, widget=forms.HiddenInput())
    watched = forms.ModelMultipleChoiceField(queryset=Player.objects.filter(game__active=True, death__isnull=True))

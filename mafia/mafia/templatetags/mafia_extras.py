from django import template
from mafia.models import NO_LYNCH, Player
from mafia.settings import HIDE_WHY, LYNCH_WORD
from django.contrib.auth.models import AnonymousUser

register = template.Library()


@register.filter
def get_vote(value, arg):
    """Gets the vote made by a given player on a given day"""
    vote = value.lynch_vote_made(arg)
    if vote:
        if vote.lynchee:
            return vote.lynchee
        else:
            return NO_LYNCH
    else:
        return "n/a"


@register.filter
def get_lynch(value, arg):
    choices = value.get_lynch(arg)[0]
    if choices:
        return ", ".join(a.username for a in choices)
    else:
        return "No " + LYNCH_WORD.lower()


@register.filter
def get_xrange1(value):
    """
        Filter - returns a list containing range made from given value
        Usage (in template):

        <ul>{% for i in 3|get_range %}
          <li>{{ i }}. Do something</li>
        {% endfor %}</ul>

        Results with the HTML:
        <ul>
          <li>0. Do something</li>
          <li>1. Do something</li>
          <li>2. Do something</li>
        </ul>

        Instead of 3 one may use the variable set in the views
    """
    return xrange(1, value + 1)

@register.filter
def locationfor(death, user):
    game = death.murderee.game
    if any((
        user == game.god,  # full permissions
        death.murderer,  # it's a murder
        not HIDE_WHY,  # everyone can see why
        death.where[:len(LYNCH_WORD)] == LYNCH_WORD  # Lynches are public
    )):
        return death.where
    # If user is dead
    if (not isinstance(user, AnonymousUser)) and Player.objects.filter(death__isnull=False, user=user, game=game).exists():
        return death.where
    else:
        return ""
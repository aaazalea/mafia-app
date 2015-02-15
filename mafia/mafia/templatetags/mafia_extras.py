from django import template


register = template.Library()


@register.filter
def get_vote(value, arg):
    """Gets the vote made by a given player on a given day"""
    vote = value.lynch_vote_made(arg)
    if vote:
        return vote.lynchee.username
    else:
        return "n/a"


@register.filter
def get_lynch(value, arg):
    choices = value.get_lynch(arg)[0]
    if choices:
        return ", ".join(a.username for a in choices)
    else:
        return "No lynch"


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

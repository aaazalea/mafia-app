mafia-app
=========

A django application to make live-action mafia games easier.

A planning trello board for this project is found at https://trello.com/b/2GcWonh3/mafia-webapp

This document is incomplete - if you would like to contribute, send me an email at jakobw@mit.edu or a pull request.

# Eye candy
####Moderator setting up a game


# A tutorial for users



# Installation

 - Install pip and virtualenv
 - Create a virtual environment in the mafia-app directory with `virtualenv venv`
 - Activate the virtual environment `source venv/bin/activate`
 - Install dependencies - `pip install -r requirements.txt`
 - Set up the database - `./manage.py migrate`
 - Install the initial data with `./manage.py loaddata fixtures/initial_data.json`
 
 
# Random Explanations

 - There is a field called `role_information` in the model `Player`. It carries different information depending on that person's role. Explanation is found in `models.py`.
 - Both the killer and the person killed have a mechanism through which they can report a death; they must decide upon the occurrence of the death who will report it.
mafia-app
=========

A django application to make live-action mafia games easier.

A planning trello board for this project is found at https://trello.com/b/2GcWonh3/mafia-webapp


# Installation

 - Install pip and virtualenv
 - Create a virtual environment in the mafia-app directory with `virtualenv venv`
 - Activate the virtual environment `source venv/bin/activate`
 - Install dependencies - `pip install -r requirements.txt`
 - Set up the database - `./manage.py migrate
 
 
# Random Explanations

 - There is a field called `role_information` in the model `Player`. It carries different information depending on that person's role. Explanation is found in `models.py`.
 - Both the killer and the person killed have a mechanism through which they can report a death; they must decide upon the occurrence of the death who will report it.
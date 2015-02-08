# Commands #
############

# Import #
##########

import praw
import logging
import comments
import token
from settings import config
from pprint import pprint

# Variables #
#############

# Functions #
#############

# Starts the commands module
def start(data,r):
	logging.debug("Starting Module: Commands")
	check_mailbox(data,r)

# Checking the mailbox for mail
def check_mailbox(data,r):
	logging.debug("Checking Mailbox")
	try:
		mailbox = r.get_unread(unset_has_mail=True,update_user=True)
	except:
		logging.warning("Failed to get unread messages. Retrying.")
		check_mailbox(data,r)
	for mail in mailbox:
		if type(mail) == praw.objects.Message: # Bot received mail
			logging.info("I've got mail.")
			read_mail(data,r,mail)
		if type(mail) == praw.objects.Comment: # Someone replied to bot
			logging.info("Someone replied to me.")
			read_comment_reply(data,r,mail)
		mail.mark_as_read() # Marks mail as read

# Reads the mail
def read_mail(data,r,mail):
	logging.info("Reading mail from %s" % mail.author.name)
	command = mail.subject.lower()
	logging.info("Subject: %s" % command)
	if command == "remind": # Useful for reminding redditors about tokens
		remind(data,r,mail)
	elif command == "add": # The same as if the bot found the comment itself
		add(data,r,mail)
	elif command == "rescan": # Same functionality as add
		add(data,r,mail)
	elif is_moderator(data,r,mail.author.name): 
		if command == "force add": # Force add skips token check
			force_add(data,r,mail)
		elif command == "reset": # Resets bot's scanned comments
			reset(data)
		elif command == "remove": # Removes token from user
			remove(data,r,mail)
		elif command == "stop": # Stops bot
			stop(data,r,mail)

# Reminds users how to use the token system
def remind(data,r,mail):
	logging.debug("Remind Command")
	reminder = True
	lines = separate_mail(mail.body)
	for line in lines:
		try:
			links = r.get_submission(line).comments
		except:
			logging.error("Failed to get comments. Retrying.")
			remind(data,r,mail)
		for comment in links:
			is_match,is_reply = comments.remind_already_replied(data,data["msg_remind"],comment.replies,
									str(data["running_username"]).lower())
			if is_match == "match":
				logging.info("Found reminder. Ignoring request.")
				reminder = False
			elif is_match == "confirm":
				logging.info("Found a confirmation. Reminder not needed.")
				reminder = False
			elif is_match == "error":
				logging.info("Found an error. Reminder not needed.")
				reminder = False
			elif is_match:
				logging.info("Found an old comment I can edit.")
				reminder = False
				is_reply.edit(data["msg_remind"])
				logging.info("Edited comment and left the reminder.")
	if reminder:
		for comment in links:
			if comment.author:
				if str(comment.author.name).lower() != str(data["running_username"]).lower():
					logging.info("User has been sent a reminder.")
					comment.reply(data["msg_remind"])
				else:
					logging.info("Silly person tried to remind me how to do my job.")

# Checks comment for token - Same functionality as if bot found the token itself
def add(data,r,mail):
	logging.debug("Add Command")
	lines = separate_mail(mail.body)
	for line in lines:
		try:
			links = r.get_submission(line).comments
		except:
			logging.warning("Failed to get comments. Retrying.")
			add(data,r,mail)
		comments.process_comments(data,r,links)

# Checks to see if user is a moderator
def is_moderator(data,r,name):
	logging.debug("Comparing User to Moderators")
	name = str(name).lower()
	try:
		moderators = r.get_moderators(data["running_subreddit"])
	except:
		logging.warning("Failed to get moderators for sub. Retrying.")
		is_moderator(data,r,name)
	for mod in moderators:
		mod = str(mod).lower()
		if mod == name:
			return True

# Forces award (skips token check and length check)
def force_add(data,r,mail):
	logging.warning("Force Add Command")
	lines = separate_mail(mail.body)
	for line in lines:
		links = r.get_submission(line).comments
		for comment in links:
			token_found = "force"
			comments.start_checks(data,r,comment,token_found)

# Resets last scanned comment
def reset(data):
	logging.debug("Reset Command")
	data["last_scanned"] = ""
	config.write_json(data)

# Removes token from flair, wiki, scoreboard, and removes confirmation comment
def remove(data,r,mail):
	logging.warning("Remove Command")
	lines = separate_mail(mail.body)
	username = str(data["running_username"]).lower()
	for line in lines:
		links = r.get_submission(line).comments
		for comment in links:
			if comments.check_already_replied(data,data["msg_confirmation"],comment.replies,username):
				for reply in comment.replies:
					if reply.author:
						if str(reply.author.name).lower() == username:
							reply.delete()
				awardee_comment = r.get_info(thing_id=comment.parent_id)
				if awardee_comment.author:
					awardee = str(awardee_comment.author.name).lower()
					flair_count = token.start_decrement(data,r,awardee)
				comment.reply(data["msg_removal"] % (data["running_subreddit"],data["running_username"]))
				comment.remove(spam=False)
				print("Placeholder: Remove text from wiki and scoreboard")
			else:
				logging.warning("No token to remove.")

# Stops bot
def stop(data,r,mail):
	logging.warning(data["stop_warning"])
	r.send_message("/r/" + data["running_subreddit"],data["stop_subject"],data["stop_body"])
	mail.mark_as_read()
	raise SystemExit(0)

# Separates the mail for processing
def separate_mail(body):
	logging.debug("Separating Mail")
	return body.split("\n")

# Reads the comment replies
def read_comment_reply(data,r,mail):
	logging.debug("Reading the reply to my comment.")
	bots_comment = r.get_info(thing_id=mail.parent_id)
	orig_comment = r.get_info(thing_id=bots_comment.parent_id)
	link = r.get_submission(orig_comment.permalink).comments
	comments.process_comments(data,r,link)
	if str(data["msg_confirmation"]).lower()[0:15] not in str(bots_comment.body).lower():
		logging.debug("Removing old comment.")
		bots_comment.remove(spam=False)
		

# EOF

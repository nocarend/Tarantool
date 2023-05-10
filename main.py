# imports
import os

import redis
from dotenv import load_dotenv
from jwt import decode, encode
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, filters,\
	MessageHandler

# Config
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))
SECRET_KEY = os.environ.get('secret_key')
user_service_data = redis.StrictRedis(host='redis', port=6379, db=0,
                                      decode_responses=True)
EXPIRING_TIME = 60


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""
	Shows hi message with all necessary commands.
	"""
	await update.message.reply_text("Hi!\n"
	                                "Service is removed 60 seconds after "
	                                "being added.\n"
	                                "Get command shows data for 10 seconds.\n"
	                                f"Your get/set/del commands expires in "
	                                f"{EXPIRING_TIME} "
	                                "seconds because of security\n"
	                                "Usage:\n"
	                                "/set <service_name> <login> <password>\n"
	                                "/get <service_name>\n"
	                                "/del <service_name>\n"
	                                "/start")


async def set_login_password(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
	"""
	Set login and password for service.
	Example: /set 1 1 1
	Instead of just storing pure data, I hash it with some technique.
	Setting expires in TIME seconds for security reasons.
	"""
	chat_id = str(update.message.chat_id)
	hashed_chat_id = encode({'chat_id': chat_id}, SECRET_KEY,
	                        algorithm='HS512')
	await delete_message(chat_id, update.message.message_id, context)

	try:
		service = str(context.args[0])
		login = str(context.args[1])
		password = str(context.args[2])
		hashed_service = encode({'service': service}, chat_id,
		                        algorithm='HS512')
		hashed_data = encode({
			'login':    login,
			'password': password
			}, str(chat_id) + service, algorithm='HS512')
		user_service_data.set(
			hashed_chat_id + hashed_service,
			hashed_data,
			ex=EXPIRING_TIME)
		message = await context.bot.send_message(chat_id,
		                                         "Successfully added!")
		message_id = message.message_id
		await delete_message(chat_id, message_id, context)
	except IndexError:
		await update.effective_message.reply_text(
			"Usage: /set <service_name> <login> <password>")


async def get_login_password(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
	"""
	Get login and password by service name.
	Example: /get 1
	"""
	chat_id = str(update.message.chat_id)
	await delete_message(chat_id, update.message.message_id, context)
	hashed_chat_id = encode({'chat_id': chat_id}, SECRET_KEY,
	                        algorithm='HS512')
	try:
		service = str(context.args[0])
		hashed_service = encode({'service': service}, chat_id,
		                        algorithm='HS512')
		hashed_key = hashed_chat_id + hashed_service
		if hashed_key not in user_service_data.keys():
			await update.message.reply_text("Given service is not found.\n"
			                                "Possibly it was deleted.")
			return
		data = decode(user_service_data.get(hashed_key),
		              str(chat_id) + service, algorithms='HS512')
		message = await context.bot.send_message(chat_id,
		                                         f"Service: {service}\n"
		                                         f"Login: {data['login']}\n"
		                                         f"Password: "
		                                         f"{data['password']}")
		message_id = message.message_id
		await delete_message(chat_id, message_id, context)
	except IndexError:
		await update.effective_message.reply_text(
			"Usage: /get <service_name>")


async def del_service_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""
	Delete service by its name.
	Example: /del 1
	"""
	chat_id = str(update.message.chat_id)
	await delete_message(chat_id, update.message.message_id, context)
	hashed_chat_id = encode({'chat_id': chat_id}, SECRET_KEY,
	                        algorithm='HS512')
	try:
		service = str(context.args[0])
		hashed_service = encode({'service': service}, chat_id,
		                        algorithm='HS512')
		hashed_key = hashed_chat_id + hashed_service
		if hashed_key not in user_service_data.keys():
			await update.message.reply_text("Given service is not found.\n"
			                                "Possibly it was deleted.")
			return
		user_service_data.delete(hashed_key)
		message = await context.bot.send_message(chat_id,
		                                         "Successfully deleted!")
		message_id = message.message_id
		await delete_message(chat_id, message_id, context)
	except IndexError:
		await update.effective_message.reply_text(
			"Usage: /del <service_name>")


async def delete_message(chat_id, message_id,
                         context: ContextTypes.DEFAULT_TYPE):
	"""
	Delete bot message by chat_id & message_id
	Message expires in TIME seconds for security reasons.
	"""
	TIME = 10
	context.job_queue.run_once(
		lambda _: context.bot.delete_message(chat_id, message_id), TIME)


async def wrong_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await update.effective_message.reply_text("You wrote wrong command!\n"
	                                          "Type /start for showing "
	                                          "command list.")


def main():
	app = ApplicationBuilder().token(os.environ.get('token')).build()

	from telegram.ext import CommandHandler
	app.add_handler(CommandHandler('start', start))
	app.add_handler(CommandHandler('get', get_login_password))
	app.add_handler(CommandHandler('set', set_login_password))
	app.add_handler(CommandHandler('del', del_service_data))
	app.add_handler(MessageHandler(filters.ALL, wrong_command))

	app.run_polling()


if __name__ == '__main__':
	main()

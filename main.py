import os

import redis
from dotenv import load_dotenv
from jwt import decode, encode
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes

# Config
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))
SECRET_KEY = os.environ.get('secret_key')
user_service_data = redis.StrictRedis(host='redis', port=6379, db=0,
                                      decode_responses=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await update.message.reply_text("Hi!\n"
	                                "Service is removed 60 seconds after "
	                                "being added.\n"
	                                "Get command shows data for 10 seconds.\n"
	                                "Your get/set/del commands expires in 10 "
	                                "seconds because of security\n"
	                                "Usage:\n"
	                                "/set <service_name> <login> <password>\n"
	                                "/get <service_name>\n"
	                                "/del <service_name>\n"
	                                "/start")


async def set_login_password(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
	chat_id = str(update.message.chat_id)
	delete_message(chat_id, update.message.message_id, context)
	hashed_chat_id = encode({'chat_id': chat_id}, SECRET_KEY,
	                        algorithm='HS512')
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
			ex=60)
		await update.effective_message.reply_text("Successfully added!")
	except IndexError:
		await update.effective_message.reply_text(
			"Usage: /set <service_name> <login> <password>")


async def get_login_password(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
	chat_id = str(update.message.chat_id)
	delete_message(chat_id, update.message.message_id, context)
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
		delete_message(chat_id, message_id, context)
	except IndexError:
		await update.effective_message.reply_text(
			"Usage: /get <service_name>")


async def del_service_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat_id = str(update.message.chat_id)
	delete_message(chat_id, update.message.message_id, context)
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
		await update.effective_message.reply_text("Successfully deleted!")
	except IndexError:
		await update.effective_message.reply_text(
			"Usage: /del <service_name>")


async def delete_message(chat_id, message_id,
                         context: ContextTypes.DEFAULT_TYPE):
	context.job_queue.run_once(
		lambda n: context.bot.delete_message(chat_id,
		                                     message_id),
		10)


def main():
	app = ApplicationBuilder().token(os.environ.get('token')).build()

	from telegram.ext import CommandHandler
	app.add_handler(CommandHandler('start', start))
	app.add_handler(CommandHandler('get', get_login_password))
	app.add_handler(CommandHandler('set', set_login_password))
	app.add_handler(CommandHandler('del', del_service_data))

	app.run_polling()


if __name__ == '__main__':
	main()

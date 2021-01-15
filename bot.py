#!/usr/bin/env python3
from classes import BotHandler, InstaPostParser, MongoHandler
import threading
from time import sleep

help_message = 'Use the /add command to add the name of the Instagram user.\
\nuse this format: <b>cristiano</b>, <b>davidbeckham</b>.\
\nnot this: @cristiano or https://www.instagram.com/davidbeckham/\
\n\nUse the /list command to see the names of the users you follow.\
\n\nUse /delete to remove username.\
\n\nmaximum users count: 10.'

def replace_dots_in_insta_username(insta_username):
	'''mongodb не принимает в key символы . $ '''
	symbols = '🎱', '💰'
	if any(symbol in insta_username for symbol in symbols):
		with_dots = insta_username.replace('🎱', '.')
		correct_username = with_dots.replace('💰', '$')
	else:
		without_dots = insta_username.replace('.', '🎱')
		correct_username = without_dots.replace('$', '💰')

	return correct_username

def get_message_info(bot_obj, update):
	'''собрать переменные от сообщения'''
	update_id = update['update_id']
	chat_id = bot_obj.get_chat_id(update)
	message = bot_obj.get_message(update)
	return update_id, chat_id, message

def bot_message_update(bot_obj, offset_count, update_id):
	'''получить новые сообщения боту'''
	offset_count = update_id + 1
	bot_obj.get_updates(offset_count)
	last_update = bot_obj.get_last_update()
	message = bot_obj.get_message(last_update)
	return message

def add_command(bot_obj, mongo_obj, chat_id, offset_count, update_id):
	bot_obj.send_message(chat_id,
		'Enter the Instagram username\n(format example: davidbeckham, lilpump)')
	try:
		new_page = bot_message_update(bot_obj, offset_count, update_id)
		if new_page:
			new_page = replace_dots_in_insta_username(new_page)
			answer = mongo_obj.add_page(new_page)
			return answer
		else:
			return 'Incorrect format'

	except Exception:
		return 'Timeout.Command was canceled'

def list_command(mongo_obj):
	user_data = mongo_obj.find_user_data()
	if user_data:
		if len(user_data) > 1:
			list_str = ''
			for i in user_data:
				if i != '_id':
					i = replace_dots_in_insta_username(i)
					list_str +=f'<b>{i}</b>\n\n'
			return list_str

	return 'The list is empty'

def delete_command(bot_obj, mongo_obj, chat_id, offset_count, update_id):
	bot_obj.send_message(chat_id,'Enter the username to delete')
	user_data = mongo_obj.find_user_data()
	try:
		del_element = bot_message_update(bot_obj, offset_count, update_id)
		if del_element:
			del_element = replace_dots_in_insta_username(del_element)
			answer = mongo_obj.delete_page(del_element)
			return answer
		return 'Incorrect format'

	except Exception:
		return 'Timeout.Command was canceled'

def generate_media_answer(media_links):
	'''создать ссылки на медиа'''
	media_str = ''
	for link in media_links:
		media_str += f'<a href="{link}"><b>link{media_links.index(link)+1}</b></a>  '
	return media_str

def generate_answer(*data):
	'''проверки на закрытый акк
	coздание ссылки'''
	if data[3]:
		media_str = generate_media_answer(data[3])
	else:
		media_str = ''

	if data[0] and data[1]:
		answer_str = f'<a href="{data[0]}"><b>{data[2]}</b></a>\n{data[1]}'
		answer_str += '\n\n<b>media:</b>\n' + media_str
	elif data[0] and data[2]:
		answer_str = f'<a href="{data[0]}"><b>{data[2]}</b></a>'
		answer_str += '\n\n<b>media:</b>\n' + media_str
	elif data[0]:
		answer_str = f'<a href="{data[0]}"><b>post</b></a>'
		answer_str += '\n\n<b>media:</b>\n' + media_str
	else:
		answer_str = None
	return answer_str

def send_insta_post_data(mongo_obj, username, user_data):
	'''отправить данные с постов'''
	check_for_new_posts = False
	check_for_first_mailing = 0
	inst_obj = InstaPostParser(username)
	inst_obj.get_to_url(inst_obj.insta_id_url)
	post_ids = inst_obj.get_first_10_post_ids()
	username = replace_dots_in_insta_username(username)

	if len(user_data[username]) == 0:
		check_for_first_mailing = -1

	if post_ids:
		post_ids.reverse()
		for post_id in post_ids[check_for_first_mailing:]:
			if post_id not in user_data[username]:
				check_for_new_posts = True
				inst_post_link = f'https://www.instagram.com/p/{post_id}/'
				bibl_post_link = f'https://www.bibliogram.art/p/{post_id}/'
				inst_obj.get_to_url(bibl_post_link)
				name = inst_obj.get_name()
				text = inst_obj.get_text()
				media_links = inst_obj.get_media_links()
				new_post = generate_answer(inst_post_link, text, name, media_links)
				bot_obj.send_message(chat_id, new_post)
					
		if check_for_new_posts:
			mongo_obj.update_posts_list(username, post_ids)

	inst_obj.close_browser()

def send_insta_data(mongo_obj, bot_obj, chat_id):
	'''достать данные с каждого	username'''
	user_data = mongo_obj.find_user_data()
	if user_data:
		for username in user_data:
			if username != '_id':
				username = replace_dots_in_insta_username(username)
				send_insta_post_data(mongo_obj, username, user_data)
				
def thread_mailing(bot_obj):
	'''рассылка постов'''
	def run():
		while True:
			if chat_id and mongo_obj:
				send_insta_data(mongo_obj, bot_obj, chat_id)
				sleep(1200)# 20минут

	thread = threading.Thread(target=run)
	thread.start()

mongo_obj = None
chat_id = None
bot_obj = BotHandler()

def main():
	offset_count = None

	while True:
		
		try:
			bot_obj.get_updates(offset_count)
		except KeyError:
			sleep(3)
			continue
			
		last_update = bot_obj.get_last_update()
		
		# проверка на новые сообщения
		if last_update:
			global chat_id
			update_id, chat_id, message = get_message_info(bot_obj, last_update)
			# проверка сообщений на содержание только текста
			if message:
				global mongo_obj
				mongo_obj = MongoHandler(chat_id)		
				
				if message == '/help':
					bot_obj.send_message(chat_id, help_message)

				elif message == '/add':
					add_answer = add_command(bot_obj,mongo_obj,chat_id,
										offset_count,update_id)
					if not add_answer.startswith('Timeout'):
						update_id += 1
					bot_obj.send_message(chat_id, add_answer)
					
				elif message == '/list':
					list_answer = list_command(mongo_obj)
					bot_obj.send_message(chat_id, list_answer)

				elif message == '/delete':
					delete_answer = delete_command(bot_obj,mongo_obj,chat_id,
											offset_count,update_id)
					if not delete_answer.startswith('Timeout'):
						update_id += 1
					bot_obj.send_message(chat_id, delete_answer)

			offset_count = update_id + 1
	
		sleep(10)

if __name__ == '__main__':
	try:
		thread_mailing(bot_obj)
		main()
		
	except KeyboardInterrupt:
		exit()
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from pymongo import MongoClient
import requests
import os

# mongodb
cluster = MongoClient("mongodb+srv://telegrambotmaker:tj1324Ip5Kmnh76@cluster0.lhzjo.mongodb.net/telegrambot?retryWrites=true&w=majority")
db = cluster['instagrambot']
channels_collection = db['instagram_page_ids']

def cut_post_id_from_url(post_link):
	'''достать post_id из ссылки'''
	post_url_index = post_link.find('/p/')
	post_id = ''
	for letter in post_link[post_url_index+3:]:
		if letter != '/':
			post_id += letter
	return post_id

class MongoHandler:
	
	def __init__(self, chat_id):
		self.channels_collection = channels_collection
		# номер пользователя в телеграм чате с ботом
		self.chat_id = chat_id

	def find_user_data(self):
		'''получить данные юзера по _id'''
		return self.channels_collection.find_one({'_id': self.chat_id})

	def add_page(self, page_id):
		''' добавить page_id или создать юзера и его первый page_id'''
		user_data = self.find_user_data()
		if user_data:
			if (len(user_data) - 1) < 10:
				data_id = {'_id': self.chat_id}
				data = {
				'$set': {page_id : []}
				}
				self.channels_collection.update_one(data_id, data)
				return 'Username added'
			else:
				return 'Limit exceeded (10)'
		else:
			data = {
			'_id': self.chat_id,
			page_id: []
			}
			self.channels_collection.insert_one(data)
			return 'Username added'

	def update_posts_list(self, page_id, last_post):
		'''добавить последний пост к page_id'''
		data_id = {'_id': self.chat_id}
		data = {'$set':{page_id : last_post}}
		return self.channels_collection.update_one(data_id, data)

	def delete_page(self, page_id):
		'''удаляет 1 page_id из списка'''
		user_data = self.find_user_data()
		if user_data:
			if page_id in user_data:
				data_id = {'_id': self.chat_id}
				data = {'$unset':{page_id : ''}}
				self.channels_collection.update_one(data_id, data)
				return 'Username deleted'
			else:
				return 'Incorrect data'
		else:
			return 'The list is empty'

class InstaPostParser:

	def __init__(self, insta_id):
		self.op = webdriver.ChromeOptions()
		self.op.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
		self.op.add_argument("--headless")
		self.op.add_argument("--no-sandbox")
		self.op.add_argument("--disable-dev-sh-usage")
		self.driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=self.op)
		#self.PATH = '/home/sergei/code/test/instatest/app/chromedriver'
		#self.driver = webdriver.Chrome(self.PATH)
		self.insta_id = insta_id
		self.insta_id_url = f'https://bibliogram.art/u/{self.insta_id}'

	def get_to_url(self, link):
		self.driver.get(link)

	def get_first_7_post_ids(self):
		'''вытаскиваем 7 последних post_id'''
		post_ids = []
		try:
			get_post_div = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.CSS_SELECTOR, ".timeline > section > div")))
			for post_url in get_post_div.find_elements_by_tag_name('a')[:7]:
				post_id = cut_post_id_from_url(post_url.get_attribute('href'))
				post_ids.append(post_id)
			return post_ids 
		except:
			return None

	def get_media(self, media_type):
		media_list = []
		try:
			get_media = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.CSS_SELECTOR, '._97aPb.wKWK0')))
			for element in get_media.find_elements_by_tag_name(media_type):
				media_link = element.get_attribute('src')
				media_list.append(media_link)
		except:
			return [None]

		return media_list

	def click_button(self):
		'''переключить вложения поста'''
		try:
			button_next = WebDriverWait(self.driver, 20).until(
				EC.element_to_be_clickable((By.CSS_SELECTOR, ".EcJQs > ._6CZji")))
			button_next.click()

			return button_next
		except:
			return None

	def get_media_links(self):
		media_links_list = []

		button = self.click_button()
		if button:

			while button:
				images = self.get_media('img')
				videos = self.get_media('video')
				media_links_list.extend(images)
				media_links_list.extend(videos)
				button = self.click_button()

		else:
			images = self.get_media('img')
			videos = self.get_media('video')
			media_links_list.extend(images)
			media_links_list.extend(videos)

		link_list = []
		for link in media_links_list:
			if (link not in link_list) and (link != None):
				link_list.append(link)

		return sorted(link_list, reverse=True)

	def get_name(self):
		try:
			get_name = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.CSS_SELECTOR, ".C4VMK > h2")))
			return get_name.find_element_by_tag_name('a').text
		except:
			return None

	def get_text(self):
		try:
			get_post_text = WebDriverWait(self.driver, 20).until(
				EC.presence_of_element_located((By.CSS_SELECTOR, ".C4VMK > span")))
			return get_post_text.text
		except:
			return None

	def close_browser(self):
		self.driver.quit()

class BotHandler:

	def __init__(self):
		# telegram bot token
		self.token = '1437349746:AAGzwB1DoMJzXA8c3vRi9Xmh2d6v6MO8x20'
		# telegram bot api
		self.telegram_api_url = f"https://api.telegram.org/bot{self.token}/"

	def get_updates(self, offset=None, timeout=30):
		'''получаем json с последними сообщениями по offset'''
		method = 'getUpdates'
		params = {'timeout': timeout, 'offset': offset}
		response = requests.get(self.telegram_api_url + method, params)
		result_json = response.json()['result']
		return result_json

	def get_last_update(self):
		'''получаем последнее сообщение боту или None'''
		get_result = self.get_updates()
		
		if len(get_result) > 0:
			last_update = get_result[-1]
		else:
			return None
		return last_update

	def get_chat_id(self, last_update):
		'''получить chat_id последнего сообщение'''
		chat_id = last_update['message']['chat']['id']
		return chat_id

	def get_message(self, last_update):
		'''получить текст последнего сообщение'''
		message = last_update.get('message').get('text')
		return message

	def send_message(self, chat_id, message):
		'''отправить сообщение'''
		params = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
		method = 'sendMessage'
		response = requests.post(self.telegram_api_url + method, params)
		return response
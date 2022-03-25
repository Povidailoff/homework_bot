import json
import os
import logging
import time
from http import HTTPStatus

from dotenv import load_dotenv
import telegram
import requests

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Функция проверяет доступность переменных окружения."""
    required_tokens = ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'PRACTICUM_TOKEN']
    missed_tokens = []

    for token in required_tokens:
        if globals()[token] is None:
            logger.critical(f'Missed required token:{token}')
            missed_tokens.append(token)

    if len(missed_tokens) > 0:
        return False
    return True


def send_message(bot, message):
    """Функция отправляет сообщение в чат.
    Чат определяется переменной TELEGRAM_CHAT_ID
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Message received!')
    except telegram.TelegramError as error:
        logger.error(f'Something wrong with TG {error}')
    except Exception as error:
        logger.error(f'Message don`t received! {error}')


def get_api_answer(current_timestamp):
    """Функция делает запрос к практикуму."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise ConnectionError('Wrong response status.')

    except requests.exceptions.HTTPError as error:
        logger.error(f'Http Error: {error}')
        raise requests.exceptions.HTTPError(f'Http Error: {error}')

    except requests.exceptions.ConnectionError as error:
        logger.error(f'Error Connecting: {error}')
        raise requests.exceptions.ConnectionError(f'Error Connecting: {error}')

    except requests.exceptions.Timeout as error:
        logger.error(f'Timeout Error: {error}')
        raise requests.exceptions.Timeout(f'Timeout Error: {error}')

    except requests.exceptions.RequestException as error:
        logger.error(f'Something wrong {error}')
        raise requests.exceptions.RequestException(f'Something wrong {error}')

    except json.JSONDecodeError as error:
        logger.error(f'Something wrong {error}')
        raise json.JSONDecodeError('JSON decoding failure.')


def check_response(response):
    """Функция проверяет корректность данных.
    Если данные корректны, функция вернёт список
    домашних работ.
    """
    sample_set = {'homeworks', 'current_date'}
    missed_data = sample_set - set(response)
    if missed_data:
        logger.error(f'Not enough data in the API response:{missed_data}')
        raise KeyError('There is not enough data in the API response.')
    if type(response['homeworks']) is not list:
        logger.error('Wrong type of API homeworks')
        raise TypeError('Type homeworks is not list')
    return response['homeworks']


def parse_status(homework):
    """Функция извлекает статус конкретной домашней работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        logger.error(f'In homework missed key {error}')
        raise KeyError(f'Missed key in homework {error}.')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        raise KeyError(f'Unkown homework status {error}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise exceptions.VariableError()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            response = check_response(response)
            homework = response[0]
            response = parse_status(homework)

        except IndexError:
            logger.debug('0 Updates in homeworks')
            response = None

        except Exception as error:
            response = f'Сбой в работе программы: {error}'
            logger.error(response)

        if last_message != response and response is not None:
            send_message(bot, response)
            last_message = response
        current_timestamp = int(time.time())
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

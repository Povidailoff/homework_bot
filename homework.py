import logging
import time
from http import HTTPStatus


import telegram
import requests

import exceptions


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
            logging.critical(f'Missed required token:{token}')
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
        logging.info('Message received!')
    except Exception as error:
        logging.error(f'Message don`t received! {error}')


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
            logging.info('exit get_api_answer')
            return response.json()
        else:
            raise ConnectionError('Wrong response status')

    except Exception as error:
        logging.error(f'Error when requesting to API: {error}')
        raise ConnectionError(error)


def check_response(response):
    """Функция проверяет корректность данных.
    Если данные корректны, функция вернёт список
    домашних работ.
    """
    sample_set = {'homeworks', 'current_date'}
    missed_data = sample_set - set(response)
    if type(response['homeworks']) != list:
        logging.error('Wrong type of API homeworks')
        raise TypeError('Type homeworks is not list')
    if not missed_data:
        return response['homeworks']
    logging.error(f'Not enough data in the API response:{missed_data}')
    raise ValueError('There is not enough data in the API response.')


def parse_status(homework):
    """Функция извлекает статус конкретной домашней работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        logging.error(f'In homework missed key {error}')
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
            logging.debug('0 Updates in homeworks')
            response = ''

        except Exception as error:
            response = f'Сбой в работе программы: {error}'
            logging.error(response)

        if last_message != response and response is not None:
            send_message(bot, response)
            last_message = response
        current_timestamp = int(time.time())
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()

VARIABLES = ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'PRACTICUM_TOKEN']


class VariableError(Exception):
    """Класс для ошибки переменных, нужных для старта программы."""

    def __str__(self):
        """Возвращает сообщение для разработчика."""
        return 'Не все переменные окружения доступны.'

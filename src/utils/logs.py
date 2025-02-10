import logging
import os

def parse_args(**kwargs) -> str:
    return ' '.join(f'{key}:{value}' for key, value in kwargs.items() if value)

# Ensure the logs directory exists
log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.path.isdir(log_dir) or os.mkdir(log_dir)

commands_logger = logging.getLogger('commands')
formatter = logging.Formatter(
    '{asctime} | G: {guild} | A: {author} | Command: /{funcName} {message}',
    style='{',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler = logging.FileHandler(os.path.join(log_dir, 'commands.log'), 'a', encoding='utf-8')
file_handler.setFormatter(formatter)
commands_logger.addHandler(file_handler)
commands_logger.setLevel(logging.INFO)

database_logger = logging.getLogger('database')
formatter = logging.Formatter(
    '{asctime} | {message}',
    style='{',
)
file_handler = logging.FileHandler(os.path.join(log_dir, 'database.log'), 'a', encoding='utf-8')
file_handler.setFormatter(formatter)
database_logger.addHandler(file_handler)
database_logger.setLevel(logging.INFO)
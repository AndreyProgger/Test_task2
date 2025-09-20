import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Test_task.settings')
app = Celery('publish', broker_connection_retry=False,
             broker_connection_retry_on_startup=True, )
app.config_from_object('django.conf:settings')

app.autodiscover_tasks()
app.conf.beat_schedule = {
    'delete-cancelled_orders-every-day': {
        # Запускаем периодическую задачу для очистки БД от удаленных заказов
        'task': 'orders.tasks.delete_cancelled_orders',
        'schedule': crontab(minute=0, hour=0),  # Задача будет выполняться каждый день в полночь
    },
}

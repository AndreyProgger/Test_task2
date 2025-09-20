import requests
from celery import shared_task

from django.core.cache import cache
from reportlab.pdfgen import canvas
from django.core.mail import send_mail

from Test_task.celery import app
from orders.models import Order


def generate_pdf(order):
    """ Функция для генерации PDF отчета на основе данных заказа """
    pdf_file = canvas.Canvas(f"order-{order.id}.pdf")  # Создаем объект Canvas

    pdf_file.setFont("Helvetica", 12)  # Устанавливаем шрифт и размер
    text = (f'Заказ № {order.id}'
            f'Содержимое заказа - {order.products}'
            f'Дата создания заказа - {order.created_at}'
            f'Итоговая сумма к оплате: {order.total_price}')
    pdf_file.drawString(100, 700, text)  # Добавляем текст на страницу

    pdf_file.save()
    return pdf_file


@app.task
def send_order_email(order_id):
    """ Задача для отправки деталей заказа на почту его создателя """
    order = Order.objects.get(id=order_id)
    pdf_file = generate_pdf(order)
    send_mail(
        f'Детали заказа №{order.pk}',
        f'Вы можете ознакомиться с деталями вашего заказа в следующем pdf файле {pdf_file}(будем считать здесь ссылка:))',
        'admin2@localhost.ru',
        [order.user.email],
        fail_silently=False,
    )


@shared_task(bind=True, max_retries=3)
def call_remote_api(url: str, cache_key: str, timeout: int = 300):
    """ Задача имитирующая вызов внешнего API """
    data = cache.get(cache_key)
    if data is None:
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            cache.set(cache_key, data, timeout=timeout)
            return data
        except requests.exceptions.RequestException as e:
            print(f'Error: {e}')
            return None
    return data


@app.task
def delete_cancelled_orders():
    """ Периодическая задача удаляющая из БД все заказы со статусом (cancelled) """
    orders = Order.objects.all()
    for order in orders:
        if order.status == 'cancelled':
            order.delete()

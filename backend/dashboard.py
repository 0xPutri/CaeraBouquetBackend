import json
from datetime import timedelta

from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from orders.models import Order
from products.models import Product
from users.models import User


def dashboard_callback(request, context):
    """
    Menyajikan data penting untuk dashboard admin.

    Fungsi ini mengumpulkan berbagai metrik bisnis dan data visualisasi grafik
    agar administrator dapat memantau performa aplikasi dengan mudah.

    Args:
        request (HttpRequest): Objek request HTTP saat ini.
        context (dict): Kamus konteks yang akan diperbarui dengan data dashboard.

    Returns:
        dict: Konteks yang telah diperbarui dengan statistik dan data grafik.
    """
    now = timezone.now()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    completed_orders_this_month = Order.objects.filter(
        status='completed', 
        created_at__gte=this_month_start
    )
    total_sales = completed_orders_this_month.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_sales_formatted = f"Rp {total_sales:,.0f}".replace(",", ".")

    new_orders_count = Order.objects.filter(status='created').count()
    products_count = Product.objects.filter(stock__gt=0).count()
    users_count = User.objects.filter(is_active=True, is_staff=False).count()

    seven_days_ago = now.date() - timedelta(days=6)
    
    daily_sales_query = Order.objects.filter(
        status='completed',
        created_at__date__gte=seven_days_ago
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total_price')
    ).order_by('date')

    sales_data_dict = {
        (seven_days_ago + timedelta(days=i)).strftime('%d %b'): 0 
        for i in range(7)
    }
    
    for item in daily_sales_query:
        day_str = item['date'].strftime('%d %b')
        if day_str in sales_data_dict:
            sales_data_dict[day_str] = float(item['total'])

    sales_chart_labels = list(sales_data_dict.keys())
    sales_chart_data = list(sales_data_dict.values())

    status_counts = Order.objects.values('status').annotate(count=Count('id'))
    status_dict = {'created': 0, 'processing': 0, 'completed': 0, 'cancelled': 0}
    
    for item in status_counts:
        status_dict[item['status']] = item['count']

    status_chart_labels = ['Menunggu', 'Diproses', 'Selesai', 'Dibatalkan']
    status_chart_data = [
        status_dict['created'], 
        status_dict['processing'], 
        status_dict['completed'], 
        status_dict['cancelled']
    ]

    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]

    context.update({
        "dashboard_stats": {
            "total_sales": total_sales_formatted,
            "new_orders_count": new_orders_count,
            "products_count": products_count,
            "users_count": users_count,
        },
        "chart_data": {
            "sales_labels": sales_chart_labels,
            "sales_data": sales_chart_data,
            "status_labels": status_chart_labels,
            "status_data": status_chart_data,
        },
        "recent_orders": recent_orders,
    })
    
    return context
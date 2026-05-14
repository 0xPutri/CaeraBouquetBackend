from django.utils import timezone
from django.db.models import Sum
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_sales_report_pdf(queryset, response):
    """
    Membangun dokumen PDF untuk laporan penjualan.

    Fungsi ini menyusun dan memformat data transaksi menjadi sebuah file PDF
    dengan sentuhan visual manis khas identitas Caera Bouquet.

    Args:
        queryset (QuerySet): Kumpulan data pesanan yang akan dimuat dalam laporan.
        response (HttpResponse): Objek respons HTTP sebagai penampung output PDF.

    Returns:
        None: Fungsi ini langsung menulis hasil render ke dalam objek respons.
    """

    doc = SimpleDocTemplate(
        response, 
        pagesize=A4, 
        rightMargin=30, 
        leftMargin=30, 
        topMargin=30, 
        bottomMargin=30
    )
    elements = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#d63384'),
        alignment=1,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontName='Helvetica',
        fontSize=14,
        textColor=colors.dimgrey,
        alignment=1,
        spaceAfter=20
    )
    
    normal_style = styles['Normal']
    
    elements.append(Paragraph("CaeraBouquet", title_style))
    elements.append(Paragraph("Sales Report", subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    total_orders = queryset.count()
    total_revenue = queryset.aggregate(Sum('total_price'))['total_price__sum'] or 0
    generated_at = timezone.localtime().strftime('%d %B %Y %H:%M')
    
    summary_text = f"""
    <b>Tanggal Cetak:</b> {generated_at}<br/>
    <b>Total Transaksi:</b> {total_orders}<br/>
    <b>Total Pendapatan:</b> Rp {total_revenue:,.2f}
    """
    elements.append(Paragraph(summary_text, normal_style))
    elements.append(Spacer(1, 0.3 * inch))
    
    data = [['ID', 'Pelanggan', 'Status', 'Tanggal Pesanan', 'Total Harga']]
    
    for order in queryset.select_related('user'):
        data.append([
            str(order.id), 
            order.user.name, 
            order.get_status_display(), 
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            f"Rp {order.total_price:,.2f}"
        ])
        
    table = Table(data, colWidths=[40, 150, 80, 120, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d63384')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    
    elements.append(table)
    
    elements.append(Spacer(1, 0.5 * inch))
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Italic'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    elements.append(Paragraph("Generated automatically by CaeraBouquet System", footer_style))
    
    doc.build(elements)
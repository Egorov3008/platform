"""
Генерация PDF файла с правилами использования.
Запуск: python3 tools/generate_rules_pdf.py
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def create_rules_pdf(output_path: str = "usage_rules.pdf"):
    """Создаёт PDF файл с правилами использования."""
    
    # Создаем документ
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    
    # Стили
    styles = getSampleStyleSheet()
    
    # Заголовок документа
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )
    
    # Подзаголовок
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica',
    )
    
    # Заголовок раздела
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold',
    )
    
    # Основной текст
    text_style = ParagraphStyle(
        'CustomText',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#374151'),
        spaceAfter=8,
        leading=16,
        fontName='Helvetica',
    )
    
    # Выделенный текст (важное)
    highlight_style = ParagraphStyle(
        'CustomHighlight',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=10,
        spaceBefore=10,
        leftIndent=10,
        rightIndent=10,
        backColor=colors.HexColor('#eff6ff'),
        borderPadding=10,
        leading=16,
        fontName='Helvetica',
    )
    
    # Элементы документа
    story = []
    
    # Заголовок
    story.append(Paragraph("📋 Правила использования VPN", title_style))
    story.append(Paragraph(
        "Публичная оферта на предоставление услуг доступа к сервису «Бот только для своих»",
        subtitle_style
    ))
    story.append(Spacer(1, 1*cm))
    
    # Раздел 1
    story.append(Paragraph("1. Общие положения", heading_style))
    story.append(Paragraph(
        "1.1. Настоящий документ является официальным предложением заключить договор "
        "на предоставление услуг доступа к сервису «Бот только для своих» (далее — «Сервис») "
        "на условиях, изложенных ниже.",
        text_style
    ))
    story.append(Paragraph(
        "1.2. Сервис предоставляет услуги подключения к защищенным сетям для обеспечения "
        "безопасности передаваемых данных и повышения конфиденциальности при использовании "
        "общедоступных и иных сетей.",
        text_style
    ))
    story.append(Paragraph(
        "1.3. В соответствии с пунктом 2 статьи 437 Гражданского кодекса Российской Федерации "
        "(ГК РФ), данный документ является публичной офертой. Полное и безоговорочное согласие "
        "(акцепт) с условиями настоящей оферты считается совершенным в момент оплаты услуг Сервиса.",
        text_style
    ))
    story.append(Paragraph(
        "1.4. Если Вы не согласны с условиями настоящей оферты, Вам следует прекратить использование Сервиса.",
        text_style
    ))
    
    # Раздел 2
    story.append(Paragraph("2. Предмет договора", heading_style))
    story.append(Paragraph(
        "2.1. Администрация предоставляет Пользователю доступ к сервису в соответствии "
        "с выбранным тарифным планом.",
        text_style
    ))
    story.append(Paragraph(
        "2.2. Пользователь обязуется оплатить и использовать услуги в соответствии "
        "с условиями настоящей оферты.",
        text_style
    ))
    
    # Раздел 3
    story.append(Paragraph("3. Оформление заказа и доступ", heading_style))
    story.append(Paragraph(
        "3.1. Заказ услуги осуществляется через Телеграм-бот «Бот только для своих».",
        text_style
    ))
    story.append(Paragraph(
        "3.2. Моментом предоставления услуги считается активация учетной записи Пользователя "
        "и предоставление данных для подключения.",
        text_style
    ))
    
    # Раздел 4
    story.append(Paragraph("4. Оплата", heading_style))
    story.append(Paragraph(
        "4.1. Оплата услуг производится безналичным способом через предоставленные в боте платежные шлюзы.",
        text_style
    ))
    story.append(Paragraph(
        "4.2. Стоимость услуг определяется тарифами, действующими на момент оплаты.",
        text_style
    ))
    
    # Раздел 5
    story.append(Paragraph("5. Возврат средств", heading_style))
    story.append(Paragraph(
        "5.1. Пользователь вправе потребовать возврата уплаченных денежных средств, если услуга "
        "была полностью недоступна (не функционировала) по вине Администрации бота непрерывно "
        "более 7 (семи) календарных дней.",
        text_style
    ))
    story.append(Paragraph(
        "5.2. Под неработоспособностью понимается полная невозможность подключения к серверам "
        "Сервиса или передачи через них данных.",
        text_style
    ))
    story.append(Paragraph(
        "<b>5.3. Технические сбои, вызванные действиями государственных органов, провайдеров связи, "
        "блокировками сетевых адресов или иными обстоятельствами, не зависящими от Администрации, "
        "не являются основанием для возврата средств.</b>",
        highlight_style
    ))
    story.append(Paragraph(
        "5.4. Возврат осуществляется в сумме, пропорциональной оставшемуся неиспользованному периоду подписки.",
        text_style
    ))
    
    # Раздел 6
    story.append(Paragraph("6. Права и обязанности сторон", heading_style))
    story.append(Paragraph(
        "6.1. Администрация обязуется предпринимать все разумные меры для поддержания работоспособности Сервиса.",
        text_style
    ))
    story.append(Paragraph(
        "6.2. Пользователь обязуется использовать Сервис исключительно в законных целях, "
        "не нарушая законодательство Российской Федерации.",
        text_style
    ))
    story.append(Paragraph(
        "<b>6.3. Запрещается использование Сервиса для:</b>",
        text_style
    ))
    story.append(Paragraph(
        "• Доступа к информации и материалам, распространение которых запрещено на территории "
        "Российской Федерации, в том числе к информации, внесенной в реестр запрещенных материалов "
        "Министерства юстиции РФ.",
        text_style
    ))
    story.append(Paragraph(
        "• Совершения мошеннических действий, распространения спама, вредоносных программ "
        "и иной противоправной деятельности.",
        text_style
    ))
    story.append(Paragraph(
        "6.4. В случае нарушения Пользователем пункта 6.3. настоящей оферты, Администрация вправе "
        "в одностороннем порядке прекратить доступ к Сервису без возмещения уплаченных средств.",
        text_style
    ))
    
    # Раздел 7
    story.append(Paragraph("7. Ответственность сторон", heading_style))
    story.append(Paragraph(
        "7.1. Администрация не несет ответственности за убытки Пользователя, возникшие в результате "
        "использования или невозможности использования Сервиса.",
        text_style
    ))
    story.append(Paragraph(
        "7.2. Администрация не несет ответственности за действия государственных органов, "
        "провайдеров связи, а также за блокировки, вызванные изменениями в законодательстве РФ.",
        text_style
    ))
    story.append(Paragraph(
        "7.3. Вся ответственность за контент и действия, совершаемые с использованием Сервиса, "
        "лежит на Пользователе.",
        text_style
    ))
    
    # Раздел 8
    story.append(Paragraph("8. Форс-мажор", heading_style))
    story.append(Paragraph(
        "8.1. Стороны освобождаются от ответственности за неисполнение обязательств по настоящему "
        "договору, если оно вызвано обстоятельствами непреодолимой силы (форс-мажор), включая, "
        "но не ограничиваясь:",
        text_style
    ))
    story.append(Paragraph(
        "<b>действиями государственных органов, введением санкций, блокировками со стороны "
        "провайдеров связи, изменениями в законодательстве Российской Федерации, которые стороны "
        "не могли ни предвидеть, ни предотвратить.</b>",
        highlight_style
    ))
    
    # Раздел 9
    story.append(Paragraph("9. Заключительные положения", heading_style))
    story.append(Paragraph(
        "9.1. Настоящая оферта может быть изменена Администрацией в одностороннем порядке. "
        "Изменения вступают в силу с момента их публикации в Телеграм-боте Сервиса.",
        text_style
    ))
    story.append(Paragraph(
        "9.2. Актуальная версия оферты всегда доступна в соответствующем разделе бота.",
        text_style
    ))
    
    # Футер
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph(
        "© 2026 Бот только для своих. Все права защищены.",
        subtitle_style
    ))
    
    # Build PDF
    doc.build(story)
    print(f"✅ PDF создан: {output_path}")
    return output_path


if __name__ == "__main__":
    create_rules_pdf()

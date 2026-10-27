import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def build_session_pdf(session):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 72
    c.setFont('Helvetica-Bold', 16)
    c.drawString(72, y, 'SmartBoard Session Report')
    y -= 30
    c.setFont('Helvetica', 12)
    c.drawString(72, y, 'Course: %s - %s' % (getattr(session.course, 'code', ''), getattr(session.course, 'name', '')))
    y -= 18
    c.drawString(72, y, 'Session: %s' % session.title)
    y -= 18
    c.drawString(72, y, 'Date: %s' % session.date)
    y -= 18
    c.drawString(72, y, 'Status: %s' % session.status)
    y -= 40

    captures = session.captures.all().order_by('created_at')
    for cap in captures:
        if y < 200:
            c.showPage()
            y = height - 72
        try:
            cleaned = getattr(cap, 'cleaned_image', None)
            img_path = None
            caption = 'Original image (not cleaned)'
            if cleaned:
                try:
                    cleaned_path = cleaned.path
                except Exception:
                    cleaned_path = None
                if cleaned_path and os.path.exists(cleaned_path):
                    img_path = cleaned_path
                    caption = 'Cleaned image (gentle)'
            if img_path is None:
                img_path = cap.image.path
                caption = 'Original image (not cleaned)'
            if os.path.exists(img_path):
                img = ImageReader(img_path)
                img_w, img_h = img.getSize()
                max_w = width - 144
                available_h = y - 72 - 40
                scale = min(max_w / img_w if img_w > 0 else 1, available_h / img_h if img_h > 0 else 1)
                draw_w = img_w * scale
                draw_h = img_h * scale
                if y - draw_h < 72:
                    c.showPage()
                    y = height - 72
                    available_h = y - 72 - 40
                    scale = min(max_w / img_w if img_w > 0 else 1, available_h / img_h if img_h > 0 else 1)
                    draw_w = img_w * scale
                    draw_h = img_h * scale
                c.drawImage(img, 72, y - draw_h, width=draw_w, height=draw_h)
                y -= draw_h + 10
                c.setFont('Helvetica-Oblique', 9)
                c.drawString(72, y, caption)
                y -= 16
            else:
                c.setFont('Helvetica-Oblique', 10)
                c.drawString(72, y, '(Image file not found)')
                y -= 18
        except Exception:
            c.setFont('Helvetica-Oblique', 10)
            c.drawString(72, y, '(Image file not found)')
            y -= 18
        c.setFont('Helvetica', 10)
        text = cap.extracted_text if cap.extracted_text and cap.extracted_text.strip() else '(No text extracted)'
        text_obj = c.beginText(72, y)
        text_obj.setFont('Helvetica', 10)
        for line in text.splitlines() or ['']:
            if len(line) > 90:
                words = line.split(' ')
                cur = ''
                for w in words:
                    if len(cur) + len(w) + 1 > 90 and cur:
                        text_obj.textLine(cur)
                        y -= 12
                        cur = w
                    else:
                        cur = (cur + ' ' + w).strip() if cur else w
                if cur:
                    text_obj.textLine(cur)
                    y -= 12
            else:
                text_obj.textLine(line)
                y -= 12
            if y < 72:
                c.drawText(text_obj)
                c.showPage()
                text_obj = c.beginText(72, height - 72)
                y = height - 72
        c.drawText(text_obj)
        y -= 24

    page_count = c.getPageNumber()
    for p in range(1, page_count + 1):
        c.setFont('Helvetica', 8)
        c.drawRightString(width - 72, 36, 'Page %d' % p)

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def build_capture_pdf(capture):
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    import os
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 72
    c.setFont('Helvetica-Bold', 16)
    c.drawString(72, y, 'SmartBoard Capture Report')
    y -= 30
    c.setFont('Helvetica', 12)
    session = capture.session
    c.drawString(72, y, 'Course: %s - %s' % (getattr(session.course, 'code', ''), getattr(session.course, 'name', '')))
    y -= 18
    c.drawString(72, y, 'Session: %s' % session.title)
    y -= 18
    c.drawString(72, y, 'Date: %s' % session.date)
    y -= 40
    try:
        cleaned = getattr(capture, 'cleaned_image', None)
        img_path = None
        if cleaned:
            try:
                cleaned_path = cleaned.path
            except Exception:
                cleaned_path = None
            if cleaned_path and os.path.exists(cleaned_path):
                img_path = cleaned_path
        if img_path is None and capture.image:
            img_path = capture.image.path
        if img_path and os.path.exists(img_path):
            img = ImageReader(img_path)
            img_w, img_h = img.getSize()
            max_w = width - 144
            scale = min(max_w / img_w if img_w > 0 else 1, 1.0)
            draw_w = img_w * scale
            draw_h = img_h * scale
            c.drawImage(img, 72, y - draw_h, width=draw_w, height=draw_h)
            y -= draw_h + 16
    except Exception:
        pass
    c.setFont('Helvetica', 10)
    text = capture.extracted_text if capture.extracted_text and capture.extracted_text.strip() else '(No text extracted)'
    text_obj = c.beginText(72, y)
    text_obj.setFont('Helvetica', 10)
    for line in text.splitlines() or ['']:
        text_obj.textLine(line)
        y -= 12
        if y < 72:
            c.drawText(text_obj)
            c.showPage()
            text_obj = c.beginText(72, height - 72)
            y = height - 72
    c.drawText(text_obj)
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

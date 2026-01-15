# Prashayan Email Templates

This directory contains HTML email templates for Prashayan's transactional emails, designed to match the frontend branding and optimized for Gmail and Zoho Mail compatibility.

## Templates

### 1. OTP Email (`otp_email.html`)
**Purpose:** Email verification and OTP delivery

**Placeholders:**
- `{{user_name}}` - Customer's name
- `{{otp_code}}` - 6-digit OTP code

**Features:**
- Prominent OTP code display with gold accent
- 10-minute expiration notice
- Security warning
- Clean, centered layout

---

### 2. Order Success Email (`order_success_email.html`)
**Purpose:** Order confirmation after successful purchase

**Placeholders:**
- `{{user_name}}` - Customer's name
- `{{order_id}}` - Order number
- `{{order_date}}` - Order date
- `{{order_items}}` - HTML for order items (see example below)
- `{{subtotal}}` - Subtotal amount
- `{{shipping}}` - Shipping cost
- `{{discount}}` - Discount amount (optional)
- `{{discount_code}}` - Discount code used (optional)
- `{{total_amount}}` - Total order amount
- `{{delivery_address}}` - Full delivery address
- `{{tracking_url}}` - Order tracking URL

**Order Items Example:**
```html
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 16px;">
    <tr>
        <td style="width: 70%; padding: 8px 0;">
            <p style="margin: 0 0 4px; font-size: 15px; font-weight: 600; color: #2E5C55;">Ashwagandha Powder (100g)</p>
            <p style="margin: 0; font-size: 13px; color: #8A9A95;">Quantity: 2</p>
        </td>
        <td style="width: 30%; text-align: right; padding: 8px 0;">
            <p style="margin: 0; font-size: 15px; font-weight: 600; color: #2E5C55;">₹999.00</p>
        </td>
    </tr>
</table>
```

**Features:**
- Order summary with itemized list
- Subtotal, shipping, discount breakdown
- Delivery address display
- Track order CTA button
- Ayurvedic wellness message

---

### 3. Order Delivery & Feedback Email (`order_delivery_feedback_email.html`)
**Purpose:** Delivery confirmation and feedback request

**Placeholders:**
- `{{user_name}}` - Customer's name
- `{{order_id}}` - Order number
- `{{delivery_date}}` - Delivery date
- `{{order_items_summary}}` - Simple text list of items
- `{{feedback_url}}` - Feedback form URL

**Order Items Summary Example:**
```html
• Ashwagandha Powder (100g) x 2<br>
• Tulsi Capsules (60 count) x 1<br>
• Neem Powder (50g) x 1
```

**Features:**
- Delivery confirmation message
- Feedback request with star rating visual
- Ayurvedic care tips
- Wellness resources links
- Social media follow section
- Referral program promotion

---

### 4. Order Cancellation Email (`order_cancellation_email.html`)
**Purpose:** Notifying user about order cancellation

**Placeholders:**
- `{{user_name}}` - Customer's name
- `{{order_id}}` - Order number
- `{{cancellation_reason}}` - Reason for cancellation
- `{{order_items_summary}}` - Summary of cancelled items
- `{{total_amount}}` - Refund amount to be processed

**Features:**
- Clear cancellation status
- Refund initiation notice
- Product discovery link

---

### 5. Payment Refunded Email (`payment_refunded_email.html`)
**Purpose:** Confirming that refund has been processed

**Placeholders:**
- `{{user_name}}` - Customer's name
- `{{order_id}}` - Order number
- `{{refund_amount}}` - Exact amount refunded
- `{{transaction_id}}` - Payment gateway transaction reference

**Features:**
- Transactional transparency
- Bank processing timeline info
- Support contact link

---

## Design System

**Colors:**
- Primary: `#2E5C55` (Deep Herbal Green)
- Primary Light: `#3E7A70`
- Primary Dark: `#1F403B`
- Secondary: `#F4F9F4` (Off-white/Mist)
- Secondary Dark: `#E1EBE1`
- Tertiary: `#D4AF37` (Classic Gold)
- Tertiary Light: `#E5C55E`

**Fonts:**
- Sans-serif: `Outfit` (Google Fonts)
- Serif: `Playfair Display` (Google Fonts)

**Logo:**
- Use `cid:logo` for embedded logo image
- Logo file: `logo.png` (600x600px)

---

## Email Client Compatibility

These templates are optimized for:
- ✅ Gmail (Web & Mobile)
- ✅ Zoho Mail
- ✅ Outlook
- ✅ Apple Mail
- ✅ Most modern email clients

**Technical Details:**
- Table-based layout (not flexbox/grid)
- Inline CSS only
- Maximum width: 600px
- No JavaScript or animations
- Web-safe fonts with fallbacks

---

## Usage with Python/FastAPI

### Example: Sending OTP Email

```python
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib

def send_otp_email(user_email, user_name, otp_code):
    # Read template
    with open('email_templates/otp_email.html', 'r') as f:
        html_template = f.read()
    
    # Replace placeholders
    html_content = html_template.replace('{{user_name}}', user_name)
    html_content = html_content.replace('{{otp_code}}', otp_code)
    
    # Create message
    msg = MIMEMultipart('related')
    msg['Subject'] = 'Verify Your Email - Prashayan'
    msg['From'] = 'noreply@prashayan.com'
    msg['To'] = user_email
    
    # Attach HTML
    msg.attach(MIMEText(html_content, 'html'))
    
    # Attach logo
    with open('email_templates/logo.png', 'rb') as f:
        logo = MIMEImage(f.read())
        logo.add_header('Content-ID', '<logo>')
        msg.attach(logo)
    
    # Send via Zoho SMTP
    with smtplib.SMTP('smtp.zoho.com', 587) as server:
        server.starttls()
        server.login('your-email@prashayan.com', 'your-password')
        server.send_message(msg)
```

---

## Testing

1. **Browser Testing:**
   - Open HTML files directly in browser to verify design
   - Check at 600px width for email client simulation

2. **Email Testing:**
   - Send test emails to Gmail and Zoho accounts
   - Verify rendering on desktop and mobile
   - Test all dynamic placeholders with sample data

3. **Link Testing:**
   - Verify all CTA buttons link correctly
   - Test social media links
   - Check footer links

---

## Notes

- Logo is embedded using `cid:logo` to ensure it displays in all email clients
- All CSS is inline for maximum compatibility
- Templates use table-based layouts as flexbox/grid are not well-supported in email clients
- Google Fonts are loaded from CDN but have fallbacks to web-safe fonts
- Maximum width is 600px for optimal rendering across devices

---

## Support

For questions or issues with these templates, contact the development team.

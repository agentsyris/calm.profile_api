# Calendly Webhook Integration

Post-Calendly webhook that automatically sends follow-up emails after 15-min intro calls.

## 🎯 Functionality

**Triggers:** Only for 15-min intro call events
**Action:** Sends plain text follow-up email
**Email Content:** Minimal, direct call-to-action for calm.profile application

## 📧 Email Details

**Subject:** "ready to start your calm.sys journey?"

**Body (Plain Text):**

```
thanks for the intro call. if you're ready, apply with calm.profile — it's a $495 application fully credited to your $2,950 sprint. 3–5 day diagnostic, 30-min debrief, 5x roi guarantee.

apply here: https://calmprofile.vercel.app

—
syrıs.
systematic solutions for modern chaos
```

## 🔧 Technical Implementation

### Webhook Endpoint

- **URL:** `/webhooks/calendly`
- **Method:** POST
- **Content-Type:** application/json

### Event Filtering

- **Event Types:** `invitee.created`, `event_scheduled`
- **Event Name Filter:** Must contain "15" and "min" (case-insensitive)
- **Purpose:** Only triggers for 15-min intro calls, not 30-min debrief calls

### Email Service Integration

- **Primary:** Postmark (if `POSTMARK_API_TOKEN` configured)
- **Fallback:** Resend (if `RESEND_API_KEY` configured)
- **From:** agent@syris.studio
- **Format:** Plain text only (minimal, professional)

## 🚀 Setup Instructions

### 1. Environment Variables

```bash
# Email service (choose one)
POSTMARK_API_TOKEN=your_postmark_token
# OR
RESEND_API_KEY=your_resend_key
```

### 2. Calendly Webhook Configuration

1. Go to Calendly Integrations → Webhooks
2. Add new webhook endpoint: `https://your-domain.com/webhooks/calendly`
3. Select events: `invitee.created` and `event_scheduled`
4. Test with sample payload

### 3. Test the Integration

```bash
# Run test script
python test_calendly_webhook.py
```

## 📊 Webhook Payload Structure

### Sample Payload (15-min intro call)

```json
{
  "event": "invitee.created",
  "payload": {
    "invitee": {
      "email": "user@example.com",
      "name": "John Doe"
    },
    "event_type": {
      "name": "15-min intro call",
      "slug": "15min"
    },
    "event": {
      "start_time": "2024-01-15T10:00:00.000000Z",
      "end_time": "2024-01-15T10:15:00.000000Z"
    }
  }
}
```

### Response Format

```json
{
  "received": true,
  "event_type": "invitee.created",
  "email_sent": true,
  "invitee_email": "user@example.com"
}
```

## 🔍 Logging & Monitoring

### Log Messages

- **Webhook Received:** `calendly webhook received: {event_type}`
- **Email Sent:** `intro call follow-up sent to {email}`
- **Email Failed:** `failed to send intro call follow-up to {email}`
- **Error:** `calendly webhook processing failed: {error}`

### Error Handling

- **Invalid Payload:** Returns 400 with error message
- **Email Service Down:** Logs warning, returns success
- **Processing Error:** Returns 500 with error details

## ✅ Acceptance Criteria

✅ **Fires only for 15-min intro event type** - Event name filtering implemented
✅ **Plain, minimal email body** - Simple text format, no HTML
✅ **Correct subject line** - "ready to start your calm.sys journey?"
✅ **Application flow link** - Points to https://calmprofile.vercel.app
✅ **Professional formatting** - Clean, branded signature

## 🧪 Testing

### Manual Testing

1. Book a 15-min intro call in Calendly
2. Check webhook logs for successful processing
3. Verify email delivery to invitee
4. Test with 30-min call (should not trigger email)

### Automated Testing

```bash
# Test 15-min intro call
python test_calendly_webhook.py

# Test non-intro call (should not send email)
# Modify test script to use 30-min event name
```

## 🔗 Related Files

- `app.py` - Webhook handler and email functions
- `test_calendly_webhook.py` - Test script
- `email-templates/intro-call-followup.html` - HTML version (not used)

## 📝 Notes

- **Plain Text Only:** Intentionally minimal for better deliverability
- **Event Filtering:** Prevents emails for debrief calls or other event types
- **Fallback Support:** Works with both Postmark and Resend
- **Error Resilience:** Continues processing even if email fails
- **Logging:** Comprehensive logging for debugging and monitoring

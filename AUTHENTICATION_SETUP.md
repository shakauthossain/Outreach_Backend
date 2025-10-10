# Authentication Setup for Screenshot Capture

## Problem
The `/speed/{lead_id}` page requires authentication. When Playwright tries to capture screenshots, it gets redirected to the login page and captures that instead of the actual speed analysis page.

## Solution
Updated the `capture_recommendations_screenshot()` function to automatically handle login before capturing screenshots.

## Setup Instructions

### Step 1: Add Credentials to .env
Add these lines to your `.env` file:

```bash
# Frontend Authentication for Screenshot Capture
FRONTEND_LOGIN_EMAIL=your-email@example.com
FRONTEND_LOGIN_PASSWORD=your-password
```

**Replace with your actual credentials** that work on `https://outreach.hellonotionhive.com`

### Step 2: Verify Login Form Selectors
The function uses these default selectors to find login form fields:
- Email field: `input[type="email"], input[name="email"], input[name="username"]`
- Password field: `input[type="password"], input[name="password"]`
- Submit button: `button[type="submit"], button:has-text("Login"), button:has-text("Sign in")`

**If your login form is different**, you need to update the selectors in `pagespeed.py`.

To find the correct selectors:
1. Open `https://outreach.hellonotionhive.com/login` in your browser
2. Right-click on the email input → Inspect
3. Note the `name`, `id`, or other attributes
4. Update the selectors in the function

### Step 3: Test the Login
Run the test script to verify authentication works:

```bash
python test_recommendations_screenshot.py
```

You should see:
```
🔐 Login required, attempting authentication...
✅ Login successful
📍 Navigating to: https://outreach.hellonotionhive.com/speed/850
✓ Found element with selector: [class*='fix']
✅ Captured recommendations screenshot
```

## How It Works

### Authentication Flow
1. **Navigate to speed page**: `https://outreach.hellonotionhive.com/speed/{lead_id}`
2. **Check if redirected**: Looks for `/login` in URL or "login" in page title
3. **If login required**:
   - Fill email field with `FRONTEND_LOGIN_EMAIL`
   - Fill password field with `FRONTEND_LOGIN_PASSWORD`
   - Click submit button
   - Wait for navigation to complete
   - Navigate back to the speed page
4. **Capture screenshot**: Proceed with screenshot capture

### Session Persistence
The function uses Playwright's `context` to maintain the session:
```python
context = browser.new_context(viewport={"width": 1920, "height": 1080})
page = context.new_page()
```

This ensures the login session is maintained throughout the screenshot capture process.

## Troubleshooting

### Issue: Still capturing login page
**Cause**: Login form selectors might be incorrect

**Solution**: 
1. Check your login page HTML structure
2. Update the selectors in `capture_recommendations_screenshot()`:

```python
# Example: If your form uses different attributes
page.fill('#email', FRONTEND_LOGIN_EMAIL)  # By ID
page.fill('#password', FRONTEND_LOGIN_PASSWORD)
page.click('#login-button')
```

### Issue: Login credentials not found
**Error**: `❌ No login credentials found`

**Solution**: Make sure you added the credentials to `.env`:
```bash
FRONTEND_LOGIN_EMAIL=actual-email@domain.com
FRONTEND_LOGIN_PASSWORD=actual-password
```

### Issue: Login button not found
**Error**: `Timeout exceeded while waiting for button`

**Solution**: Check what text your login button has:
```python
# Try different button texts
page.click('button:has-text("Submit")')
page.click('button:has-text("Log In")')
page.click('button:has-text("Enter")')
```

### Issue: Two-Factor Authentication (2FA)
**Problem**: If your frontend uses 2FA, automated login won't work

**Solutions**:
1. **Disable 2FA for the automation account** (create a separate user)
2. **Use cookie-based authentication**: Save cookies after manual login
3. **Use JWT token**: Store a long-lived token and inject it

#### Option 2: Cookie-Based Authentication
```python
# After manual login once, save cookies
context.storage_state(path="auth.json")

# In future runs, load the saved state
context = browser.new_context(storage_state="auth.json")
```

#### Option 3: JWT Token Authentication
```python
# Set authorization header or localStorage token
page.add_init_script(f"""
    localStorage.setItem('token', '{your_jwt_token}');
""")
```

### Issue: Login takes too long
**Error**: `Timeout exceeded`

**Solution**: Increase timeout values:
```python
page.wait_for_load_state("networkidle", timeout=20000)  # Increase to 20s
```

## Alternative: Public Speed Page

If authentication is too complex, consider creating a public route for screenshots:

### Backend (main.py)
```python
@app.get("/public/speed/{lead_id}")
async def public_speed_page(lead_id: int):
    # Return speed data without auth requirement
    # This endpoint is ONLY for screenshot capture
    pass
```

Then update the frontend URL:
```python
speed_page_url = f"{FRONTEND_URL}/public/speed/{lead_id}"
```

## Security Notes

⚠️ **Important Security Considerations**:

1. **Store credentials securely**: Never commit `.env` file to git
2. **Use a dedicated account**: Create a separate user with read-only access
3. **Rotate passwords regularly**: Change the automation account password periodically
4. **Monitor access logs**: Check for unusual login patterns
5. **Consider IP whitelisting**: Restrict the automation account to your server IP

## Best Practice: Service Account

Create a dedicated service account for automation:
1. Email: `automation@notionhive.com` or `screenshots@notionhive.com`
2. Limited permissions (read-only access to speed data)
3. Separate password from your personal account
4. No 2FA requirement

This way, if credentials are compromised, the damage is limited.

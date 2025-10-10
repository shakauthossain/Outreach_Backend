# ✅ Recommendations Screenshot Implementation - COMPLETE

## Summary
Successfully implemented automated screenshot capture of the recommendations/diagnostics section from your frontend speed analysis page (`https://outreach.hellonotionhive.com/speed/{lead_id}`).

## What Was Done

### 1. Database Changes
- ✅ Added `recommendations_screenshot_url` column to `leads` table
- ✅ Updated SQLAlchemy model (`LeadDB`) in `database.py`
- ✅ Updated Pydantic model (`Lead`) in `models.py`
- ✅ Created and ran migration script

### 2. Screenshot Capture Function
- ✅ Created `capture_recommendations_screenshot()` function in `pagespeed.py`
- ✅ Uses Playwright to navigate to frontend pages
- ✅ Intelligently tries multiple selectors to find the recommendations section
- ✅ Falls back to full-page screenshot if specific section not found
- ✅ Saves screenshots to `static/{domain}/{domain}-recommendations.png`
- ✅ Returns public URL: `https://result.hellonotionhive.com/{domain}-recommendations.png`

### 3. Integration
- ✅ Updated `test_all_unspeeded_leads()` to capture screenshots after speed tests
- ✅ Updated `refresh_speed_for_lead()` to capture screenshots when refreshing
- ✅ Both functions automatically save the screenshot URL to the database

### 4. Testing
- ✅ Created test script (`test_recommendations_screenshot.py`)
- ✅ Successfully tested on lead ID 850 (Storyline)
- ✅ Screenshot saved: 227KB PNG file
- ✅ URL saved to database

## How It Works

### Workflow
1. **Run PageSpeed Tests**: Get performance scores for desktop & mobile
2. **Save to Database**: Commit the speed data
3. **Capture Screenshot**:
   - Navigate to `https://outreach.hellonotionhive.com/speed/{lead_id}`
   - Wait for page to load
   - Try multiple selectors to find the recommendations section:
     - `text=What Can We Fix`
     - `text=What This Means`
     - `text=Performance Metrics`
     - `text=Recommendations`
     - `text=Diagnostics`
     - `[class*='recommendation']`
     - `[class*='diagnostic']`
     - `[class*='fix']` ← **This worked for your site!**
   - Take screenshot of the section (or full page if not found)
4. **Save Screenshot**: Store file in `static/` directory
5. **Update Database**: Save the public URL

### File Structure
```
static/
  storylinecommunication_com/
    storylinecommunication_com-desktop-pagespeed.png
    storylinecommunication_com-mobile-pagespeed.png
    storylinecommunication_com-recommendations.png  ← NEW!
```

## Usage

### Automatic (Recommended)
When you run your speed tests, screenshots are automatically captured:
```python
# Via API endpoint
POST /testspeed  # Tests all leads

# Or refresh single lead
POST /refresh-speed/{lead_id}
```

### Manual Testing
```bash
# Test on a single lead
python test_recommendations_screenshot.py
```

### Accessing Screenshots
The URLs are stored in the database and can be retrieved via your API:
```python
# Example lead data will now include:
{
  "id": 850,
  "company": "Storyline - Creative Agency",
  "website_url": "https://storylinecommunication.com",
  "website_speed_mobile": 68,
  "recommendations_screenshot_url": "https://result.hellonotionhive.com/storylinecommunication_com-recommendations.png"
}
```

## Configuration

### Frontend URL
Default: `https://outreach.hellonotionhive.com`
Change in `pagespeed.py`:
```python
FRONTEND_URL = "https://your-frontend-url.com"
```

### Screenshot Settings
In `capture_recommendations_screenshot()` function, you can adjust:
- **Viewport size**: `viewport={"width": 1920, "height": 1080}`
- **Timeouts**: `timeout=30000` (30 seconds)
- **Wait time**: `time.sleep(2)` (2 seconds after page load)
- **Selectors**: Add/modify in `selectors_to_try` list

### Custom Selectors
If you want to target a specific section more precisely, update the selector list:
```python
selectors_to_try = [
    ".your-custom-class",  # Add your own
    "#your-custom-id",
    "[data-testid='your-test-id']",
    # ... existing selectors
]
```

## Troubleshooting

### Screenshot is blank or wrong section
- Open https://outreach.hellonotionhive.com/speed/{lead_id} in browser
- Inspect the element containing the recommendations
- Add a more specific selector to the `selectors_to_try` list

### Timeout errors
- Increase timeout values in the function
- Check if frontend is slow to load
- Verify frontend URL is correct

### Screenshot too large
- Reduce viewport size
- Capture specific section instead of full page
- Compress images post-capture

## Files Created/Modified

### Modified:
- `database.py` - Added column definition
- `models.py` - Added field to Pydantic model
- `pagespeed.py` - Added screenshot capture function and integration

### Created:
- `migrate_add_recommendations_column.py` - Database migration script
- `test_recommendations_screenshot.py` - Test script
- `RECOMMENDATIONS_SCREENSHOT_README.md` - This documentation

## Next Steps

1. **Test on more leads**: Run `/testspeed` to process all leads
2. **Display in frontend**: Update your frontend to show the recommendations screenshot
3. **Use in emails**: Include the screenshot URL in your generated emails
4. **Monitor performance**: Check if screenshot capture adds significant time to the process

## Performance Notes

- Each screenshot capture takes approximately 5-10 seconds
- Playwright runs in headless mode (no GUI)
- Screenshots are ~200-300KB each
- Process runs synchronously (blocks until complete)

### Optimization Ideas (Future):
- Move screenshot capture to Celery background task
- Capture screenshots in batch async mode
- Add retry logic for failed captures
- Compress images automatically

## Success! 🎉

The implementation is complete and tested. Screenshots are now automatically captured whenever you run speed tests on your leads!

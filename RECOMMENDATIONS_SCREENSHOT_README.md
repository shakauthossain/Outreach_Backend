# Recommendations Screenshot Implementation

## Overview
Added functionality to capture a screenshot of the "What Can We Fix to Make Your Site Faster?" section from the frontend speed details page and store it in the database.

## Changes Made

### 1. Database Schema (`database.py`)
Added a new column to store the screenshot URL:
```python
recommendations_screenshot_url = Column(String, nullable=True)
```

### 2. Pydantic Model (`models.py`)
Added the field to the Lead model:
```python
recommendations_screenshot_url: Optional[str] = None
```

### 3. Screenshot Capture Function (`pagespeed.py`)
Created a new function `capture_recommendations_screenshot()` that:
- Uses Playwright to navigate to `https://outreach.hellonotionhive.com/speed/{lead_id}`
- Waits for the "What Can We Fix" section to load
- Captures a screenshot of that specific section
- Saves it to `static/{domain}/{domain}-recommendations.png`
- Returns the public URL: `https://result.hellonotionhive.com/{domain}-recommendations.png`

### 4. Integration
Updated both speed test functions to automatically capture recommendations screenshots:
- `test_all_unspeeded_leads()` - Bulk speed testing
- `refresh_speed_for_lead()` - Single lead refresh

The workflow is:
1. Run pagespeed tests (desktop & mobile)
2. Commit the speed data to database
3. Capture recommendations screenshot from frontend
4. Save screenshot URL to database

## How It Works

1. **After pagespeed data is saved**, the system:
   - Navigates to your frontend page at `/speed/{lead_id}`
   - Waits for the recommendations section to render
   - Takes a screenshot of the specific section
   - Saves it in the `static` directory

2. **File Storage**:
   - Path: `static/{sanitized_domain}/{sanitized_domain}-recommendations.png`
   - Public URL: `https://result.hellonotionhive.com/{sanitized_domain}-recommendations.png`

3. **Database Storage**:
   - The URL is saved in the `recommendations_screenshot_url` field
   - Can be accessed via the API alongside other lead data

## Usage

### Automatic Capture
When you run `/testspeed` endpoint or refresh a lead's speed:
```python
# This will now automatically capture recommendations screenshot
/api/testspeed  # Bulk test all leads
/api/refresh-speed/{lead_id}  # Refresh single lead
```

### Manual Testing
Run the test script:
```bash
python test_recommendations_screenshot.py
```

## Important Notes

### Frontend Selector
The current implementation uses:
```python
page.locator("text=What Can We Fix").locator("..").locator("..")
```

**You may need to adjust this selector** based on your actual HTML structure. To find the right selector:
1. Open your frontend page in a browser
2. Open DevTools (F12)
3. Find the container element that wraps the "What Can We Fix" section
4. Update the selector in `capture_recommendations_screenshot()` function

Example alternative selectors:
```python
# By class name
page.locator(".recommendations-section")

# By ID
page.locator("#recommendations")

# By data attribute
page.locator("[data-testid='recommendations']")

# By more specific text + parent
page.locator("text=What Can We Fix to Make Your Site Faster?").locator("xpath=ancestor::div[@class='section']")
```

### Troubleshooting

1. **Screenshot not capturing**: 
   - Check if the frontend page is accessible at `https://outreach.hellonotionhive.com`
   - Verify the selector is correct for your HTML structure
   - Check browser console logs

2. **Timeout errors**:
   - Increase the timeout values in the function
   - Check if the frontend takes longer to load

3. **Empty screenshots**:
   - The section might not be visible in the viewport
   - Try scrolling to the element before capturing:
     ```python
     recommendations_section.scroll_into_view_if_needed()
     ```

## Database Migration
Since you're adding a new column, make sure to:
1. Restart your application to create the new column
2. Or run a migration if you're using a migration tool

The column will be created automatically on the next app start since you have:
```python
Base.metadata.create_all(bind=engine)
```

## Next Steps
1. Test with a single lead using the test script
2. Verify the screenshot captures the right section
3. Adjust the selector if needed
4. Run on all leads via `/testspeed` endpoint

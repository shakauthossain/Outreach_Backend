# Recommendations Screenshot Implementation

## Overview
This implementation captures a screenshot of the "What Can We Fix to Make Your Site Faster?" section from your frontend speed analysis page and stores it in the database.

## Changes Made

### 1. Database Schema Update (`database.py`)
Added a new column to the `LeadDB` model:
```python
recommendations_screenshot_url = Column(String, nullable=True)
```

### 2. Pydantic Model Update (`models.py`)
Added the corresponding field to the `Lead` model:
```python
recommendations_screenshot_url: Optional[str] = None
```

### 3. New Screenshot Capture Function (`pagespeed.py`)
Created `capture_recommendations_screenshot()` function that:
- Uses Playwright to navigate to `https://outreach.hellonotionhive.com/speed/{lead_id}`
- Waits for the page to load completely
- Locates the "What Can We Fix to Make Your Site Faster?" section
- Takes a screenshot of just that section
- Saves it to the `static/{domain}/` directory
- Returns the public URL: `https://result.hellonotionhive.com/{domain}-recommendations.png`

### 4. Integration into Existing Workflows
Updated both functions to capture the recommendations screenshot:
- `test_all_unspeeded_leads()` - Bulk testing all leads
- `refresh_speed_for_lead()` - Refreshing a single lead

## How It Works

1. **PageSpeed Analysis**: First, the function fetches PageSpeed scores and screenshots (desktop & mobile)
2. **Data Commit**: Commits the PageSpeed data to the database
3. **Screenshot Capture**: Calls `capture_recommendations_screenshot()` with the lead ID
4. **Browser Automation**: Playwright opens the frontend page in headless mode
5. **Element Selection**: Finds the recommendations section by looking for the text "What Can We Fix to Make Your Site Faster?"
6. **Screenshot**: Captures only that section as a PNG image
7. **Storage**: Saves to `static/{sanitized_domain}/{sanitized_domain}-recommendations.png`
8. **URL Generation**: Returns the public URL for the screenshot
9. **Database Update**: Stores the URL in `recommendations_screenshot_url` field

## Prerequisites

The following are already installed in your project:
- `playwright` (in requirements.txt)
- Playwright browsers (need to be installed with `playwright install`)

## Installation Steps

Before using this feature, you need to install Playwright browsers:

```bash
# Activate your virtual environment
source "/media/shakaut/Essentials/Office Work/Notionhive/Python_Venv/outreach/bin/activate"

# Install Playwright browsers
playwright install chromium
```

## Usage

### Automatic Capture
The screenshots are automatically captured when you:
1. Run bulk speed tests via `/testspeed` endpoint
2. Refresh speed for a specific lead

### Accessing the Screenshots
- The screenshot URLs are stored in the `recommendations_screenshot_url` field
- You can display them in your frontend by fetching the lead data
- Example URL format: `https://result.hellonotionhive.com/example_com-recommendations.png`

## Important Notes

### Frontend HTML Structure
The function looks for text "What Can We Fix to Make Your Site Faster?" to locate the section. If your frontend HTML structure changes, you may need to update the selector in the `capture_recommendations_screenshot()` function:

```python
# Current selector
page.wait_for_selector('text=What Can We Fix to Make Your Site Faster?', timeout=15000)
recommendations_section = page.locator('text=What Can We Fix to Make Your Site Faster?').locator('..')
```

You can customize the selector to:
- Use a specific CSS class: `page.locator('.recommendations-section')`
- Use an ID: `page.locator('#recommendations')`
- Use a data attribute: `page.locator('[data-section="recommendations"]')`

### Timeout Settings
- Page load timeout: 30 seconds
- Element wait timeout: 15 seconds
- Rendering delay: 2 seconds

Adjust these if needed based on your page performance.

### Error Handling
If screenshot capture fails, the function:
- Prints an error message to the console
- Returns `None`
- Continues processing without breaking the workflow
- The `recommendations_screenshot_url` field remains `NULL` in the database

## Troubleshooting

### Screenshot Not Captured
1. **Check if Playwright browsers are installed**: Run `playwright install chromium`
2. **Verify frontend is accessible**: Make sure `https://outreach.hellonotionhive.com` is running
3. **Check console output**: Look for error messages in the terminal
4. **Verify HTML structure**: The selector might need adjustment if the frontend changed

### Authentication Required
If your frontend requires authentication to view the speed details page:
1. You'll need to add authentication to the Playwright script
2. Options:
   - Use cookies/tokens in the browser context
   - Navigate to login page first
   - Use API authentication headers

### Slow Performance
If screenshot capture is too slow:
1. Reduce wait times in the function
2. Consider making it an async background task
3. Use Celery to process screenshots asynchronously

## Future Enhancements

Potential improvements:
1. **Async Processing**: Use Celery to capture screenshots in background
2. **Retry Logic**: Implement retries for failed captures
3. **Multiple Sections**: Capture different sections separately
4. **Full Page**: Option to capture the entire page instead of just one section
5. **Authentication**: Add support for authenticated pages
6. **Custom Selectors**: Make the selector configurable per lead or globally

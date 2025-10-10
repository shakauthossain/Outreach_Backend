# Export Feature Update - Recommendations Screenshot URL

## Summary
Added the `recommendations_screenshot_url` field and other missing fields to the CSV export functionality in both backend and frontend.

---

## Changes Made

### 1. Backend (`main.py`)

**File:** `/media/shakaut/Essentials/Office Work/Notionhive/Client Work/NH Agent/nh-outreach-agent/main.py`

**Updated:** `DEFAULT_EXPORT_COLUMNS` list

**Added Fields:**
```python
DEFAULT_EXPORT_COLUMNS = [
    "id", "first_name", "last_name", "email",
    "company", "title", "website_url", "linkedin_url",
    "website_speed_web", "website_speed_mobile",          # ✅ Speed test scores
    "screenshot_url_web", "screenshot_url_mobile",        # ✅ Desktop & Mobile screenshots
    "recommendations_screenshot_url",                      # ✅ NEW: Recommendations screenshot
    "accessibility_score", "seo_score", "best_practices_score",  # ✅ PageSpeed scores
    "punchline1", "punchline2", "punchline3"              # ✅ Marketing punchlines
]
```

---

### 2. Frontend (`CsvDownload.tsx`)

**File:** `/media/shakaut/Essentials/Office Work/Notionhive/Client Work/NH Agent/Frontend/src/components/CsvDownload.tsx`

**Updated:** `AVAILABLE_COLUMNS` array

**Added Fields:**
- ✅ `id` - Lead ID
- ✅ `screenshot_url_mobile` - Mobile screenshot URL
- ✅ `recommendations_screenshot_url` - **Recommendations screenshot URL** (NEW)
- ✅ `accessibility_score` - Accessibility score
- ✅ `seo_score` - SEO score
- ✅ `best_practices_score` - Best practices score
- ✅ `generated_email` - AI-generated email
- ✅ `final_email` - Final email content
- ✅ `sent_to_salesrobot` - Sales robot integration status

**Updated Labels:**
- `screenshot_url_web` → "Screenshot URL (Desktop)" (clarified)
- `screenshot_url_mobile` → "Screenshot URL (Mobile)" (clarified)

---

## How to Use

### For Users (Frontend):

1. Click the **"Download CSV"** button in the leads table
2. A dialog will open showing all available columns
3. Look for **"Recommendations Screenshot URL"** in the list
4. Check/uncheck the fields you want to export
5. Click **"Download"** to get your CSV file

### For Developers:

**Backend endpoints remain the same:**
- `GET /download-csv?columns=field1,field2,field3` - Download all leads with selected columns
- `POST /download-csv-selected` - Download selected leads with chosen columns

**Example API call:**
```bash
# Download with recommendations screenshot URL
curl "http://localhost:8000/download-csv?columns=email,company,recommendations_screenshot_url"

# Or for selected leads
curl -X POST http://localhost:8000/download-csv-selected \
  -H "Content-Type: application/json" \
  -d '{
    "lead_ids": [1, 2, 3],
    "columns": "email,company,recommendations_screenshot_url"
  }'
```

---

## Available Screenshot Fields in Export

| Field Name | Description | Example URL |
|------------|-------------|-------------|
| `screenshot_url_web` | Desktop PageSpeed screenshot | `https://result.hellonotionhive.com/example_com_desktop.png` |
| `screenshot_url_mobile` | Mobile PageSpeed screenshot | `https://result.hellonotionhive.com/example_com_mobile.png` |
| `recommendations_screenshot_url` | Recommendations Card screenshot | `https://result.hellonotionhive.com/example_com-recommendations.png` |

---

## What's Next?

✅ Users can now export the recommendations screenshot URL along with other lead data
✅ All PageSpeed-related fields are available for export
✅ Frontend UI updated with clear labels for all screenshot types

**To capture recommendations screenshots for existing leads:**
```bash
# Capture for all leads with speed data
python test_capture_recommendations_bulk.py

# Or via API
curl -X POST http://localhost:8000/capture-recommendations-all
```

---

## Files Modified

1. ✅ `main.py` - Backend export columns
2. ✅ `CsvDownload.tsx` - Frontend export UI

## Files Created

1. ✅ `background_recommendations.py` - Bulk recommendations capture logic
2. ✅ `test_capture_recommendations_bulk.py` - Test script for bulk capture
3. ✅ `EXPORT_UPDATE_SUMMARY.md` - This documentation

---

**Last Updated:** October 10, 2025
**Status:** ✅ Complete and Ready to Use

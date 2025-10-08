# Enhanced Punchline Generation - Usage Guide

## 🚀 Quick Start

Your punchline generation system has been enhanced with comprehensive tracking, retry logic, and error handling. Here's how to use it:

## 📋 Available Endpoints

### 1. Single Lead Processing
```bash
POST /process-punchlines-lead/{lead_id}
```
**Features:**
- ✅ Automatic duplicate checking (skips if punchlines exist)
- ✅ 5-retry system with smart error handling
- ✅ Real-time progress logging
- ✅ 2-second rate limiting after success

**Response Example:**
```json
{
  "lead_id": 123,
  "status": "success", 
  "punchlines_count": 3
}
```

### 2. Bulk Processing
```bash
POST /process-punchlines-all
```
**Features:**
- ✅ Processes all leads with websites
- ✅ Skip optimization for existing punchlines
- ✅ Comprehensive completion statistics
- ✅ Per-lead retry logic

**Response Example:**
```json
{
  "total_leads": 150,
  "processed": 142,
  "skipped": 5,
  "errors": 3,
  "success_rate": "97.9%"
}
```

## 🔧 Backend Logging

### What You'll See in Logs

#### Single Lead Success
```
Lead 123: Processing punchlines (attempt 1/6)
Lead 123: Generating punchlines for company: TechCorp
Evidence items found: 8
Lead 123: Successfully generated 3 punchlines
Waiting 2 seconds (rate limiting)...
```

#### Retry with Rate Limit Error
```
Lead 456: Processing punchlines (attempt 1/6)  
Lead 456: Rate limit/quota exceeded error: Quota exceeded
Lead 456: Retrying in 60 seconds...
Lead 456: Processing punchlines (attempt 2/6)
Lead 456: Successfully generated 3 punchlines
```

#### Bulk Processing Summary
```
Starting bulk punchline processing: 145 leads to process out of 150 total
Processing lead 201 (1/150)
Lead 201: Already has punchlines, skipping
Processing lead 202 (2/150)  
Lead 202: Successfully generated 3 punchlines
...
Bulk processing completed: 142 processed, 5 skipped, 3 errors
```

## 🎯 Frontend Features

### Enhanced Status Messages
- **Progress Updates**: Every 30 seconds during long jobs
- **Detailed Completion**: Shows metrics like "142 processed, 5 skipped, 3 errors (97.9% success rate)"
- **Real-time Feedback**: Live status updates with retry information

### Job Tracking
The frontend will automatically show:
- ⏳ "Processing... Job running for 60s. Please wait while we generate punchlines..."
- ✅ "Completed: 142 processed, 5 skipped, 3 errors (97.9% success rate)"
- ❌ Clear error messages with retry information

## 🛠️ Error Handling

### Error Categories & Retry Strategies

| Error Type | Detection | Retry Strategy | Example |
|------------|-----------|----------------|---------|
| **Rate Limit** | "rate limit", "quota exceeded" | 60s, 120s, 180s... | `Quota exceeded for gemini api` |
| **Token Limit** | "token" + "limit/exceeded" | 2s, 4s, 8s, 16s, 32s | `Token limit exceeded in request` |
| **Authentication** | "authentication", "api key" | No retry (immediate fail) | `Invalid API key` |
| **General** | All other errors | 2s, 4s, 8s, 16s, 32s | `Network timeout` |

### Max Retry Logic
- **5 attempts total** per lead (no additional retries beyond 5 attempts)
- **Smart delays** based on error type
- **Automatic failure** after max retries exceeded
- **Continue processing** other leads even if one fails

## 📊 Performance Features

### Duplicate Prevention  
- Automatically skips leads that already have all 3 punchlines
- Reduces API calls and processing time
- Clear logging when skipping

### Rate Limiting
- **2-second mandatory delay** after each successful generation
- Prevents hitting Gemini API rate limits
- Compliant with API usage guidelines

### Bulk Optimization
- Processes leads in sequence with individual retry logic
- Collects comprehensive statistics
- Continues processing even when individual leads fail

## 🔍 Monitoring & Debugging

### Key Metrics to Track
1. **Success Rate**: Percentage of leads successfully processed
2. **Skip Rate**: Percentage of leads skipped (already had punchlines)
3. **Error Patterns**: Most common error types
4. **Processing Time**: Average time per lead
5. **Retry Frequency**: How often retries are needed

### Common Issues & Solutions

#### High Rate Limit Errors
- **Cause**: Too many concurrent requests
- **Solution**: System automatically handles with 60s delays
- **Prevention**: The 2s delays should prevent this

#### Token Limit Errors
- **Cause**: Individual requests too large
- **Solution**: System retries with exponential backoff
- **Prevention**: Evidence is automatically filtered

#### Authentication Errors
- **Cause**: Invalid/expired Gemini API key
- **Solution**: Check environment variables, no retries attempted
- **Prevention**: Validate API key before bulk operations

## 🚦 Best Practices

### When to Use Single vs Bulk Processing
- **Single Lead**: Testing, urgent individual updates, debugging
- **Bulk Processing**: Regular batch updates, initial data population

### Monitoring Recommendations
1. **Watch Logs**: Monitor for error patterns during bulk operations
2. **Check Success Rates**: Aim for >95% success rate in bulk processing
3. **Track API Usage**: Monitor Gemini API quotas and limits
4. **Schedule Wisely**: Run bulk operations during off-peak hours

### Troubleshooting Steps
1. **Check Lead Data**: Ensure leads have valid website URLs
2. **Verify API Key**: Test single lead processing first
3. **Monitor Resources**: Check system resources during bulk operations
4. **Review Logs**: Look for specific error patterns

## 📈 Expected Performance

### Timing Estimates
- **Single Lead**: 5-15 seconds (including 2s delay)
- **Bulk Processing**: ~10-20 seconds per lead
- **100 Leads**: ~20-35 minutes (with retries and delays)
- **1000 Leads**: ~3-6 hours (depending on errors/retries)

### Success Rates
- **Normal Operations**: 95-99% success rate
- **High Load**: 90-95% success rate  
- **API Issues**: 80-90% success rate (with retries)

## 🎉 Ready to Use!

Your enhanced punchline generation system is now ready for production use with:

✅ **Comprehensive error handling** - 5 retry attempts with smart delays  
✅ **Progress tracking** - Real-time logging and frontend updates  
✅ **Duplicate prevention** - Automatic skipping of existing punchlines  
✅ **Rate limiting** - 2-second delays to respect API limits  
✅ **Bulk optimization** - Efficient processing with detailed statistics  

The system will automatically handle edge cases, retry failures, and provide detailed feedback on all operations.
# Data Retention and Deletion Policy

**Effective Date:** December 25, 2025  
**Last Updated:** December 25, 2025  
**Version:** 1.0

## Overview

This document outlines Junior AI Legal Assistant's data retention, storage, and deletion policies in compliance with applicable data protection regulations including GDPR, Indian IT Act 2000, and Digital Personal Data Protection Act (DPDP) 2023.

## Scope

This policy applies to all personal and case-related data processed by Junior, including:
- User account information
- Legal case documents and files
- Chat conversations and AI interactions
- Uploaded documents (PDFs, audio recordings)
- Search queries and research history
- System logs and analytics

## Data Categories and Retention Periods

### 1. User Account Data
**Data Type:** Email, authentication tokens, user preferences  
**Retention Period:** Duration of account + 30 days after deletion request  
**Legal Basis:** Contract performance, user consent  
**Deletion Trigger:** User account deletion request

### 2. Legal Case Documents
**Data Type:** Case files, FIRs, evidence, witness statements, court documents  
**Retention Period:** 7 years after case closure (as per Indian Evidence Act)  
**Legal Basis:** Legal obligation, legitimate interest  
**Deletion Trigger:** User-initiated deletion OR automatic after retention period  
**Exception:** Documents under litigation hold are retained until legal proceedings conclude

### 3. Chat Conversations
**Data Type:** User queries, AI-generated responses, conversation history  
**Retention Period:** 
- Active sessions: Until session end or 24 hours of inactivity
- Historical conversations: 90 days from last interaction
**Legal Basis:** User consent, service provision  
**Deletion Trigger:** User deletion request, automatic purge after 90 days  
**Storage Location:** Browser localStorage (client-side), temporary server cache

### 4. Uploaded Documents
**Data Type:** PDFs, audio files, images  
**Retention Period:** 
- Temporary uploads: 24 hours (auto-deleted)
- Case-attached documents: Same as case retention (7 years)
**Legal Basis:** User consent, service provision  
**Deletion Trigger:** Automatic after 24 hours OR case deletion  
**Storage Location:** `uploads/` directory (server-side), Supabase storage

### 5. Audio Recordings
**Data Type:** Transcribed audio, raw audio files  
**Retention Period:** 
- Raw audio: Deleted immediately after transcription
- Transcriptions: Same as chat conversations (90 days)
**Legal Basis:** User consent  
**Deletion Trigger:** Immediate post-processing, user deletion request

### 6. Search and Research History
**Data Type:** Search queries, web research results, legal citations  
**Retention Period:** 180 days from query date  
**Legal Basis:** Service improvement, user consent  
**Deletion Trigger:** Automatic purge after 180 days, user request

### 7. System Logs
**Data Type:** Error logs, access logs, API request logs  
**Retention Period:** 90 days  
**Legal Basis:** Legitimate interest (security, debugging)  
**Deletion Trigger:** Automatic log rotation after 90 days  
**PII Handling:** Logs are sanitized to remove PII

### 8. Analytics and Usage Data
**Data Type:** Aggregated usage statistics, feature usage metrics  
**Retention Period:** 2 years  
**Legal Basis:** Legitimate interest (service improvement)  
**Deletion Trigger:** Automatic purge after 2 years  
**Note:** Analytics data is anonymized and cannot be linked to individuals

## Data Deletion Mechanisms

### Immediate Deletion
- Temporary files after processing
- Session tokens after logout
- Cached responses (configurable TTL)

### Scheduled Deletion
Automated cron job runs daily at 02:00 UTC to purge:
- Expired chat conversations (>90 days)
- Old search history (>180 days)
- Temporary uploads (>24 hours)
- Rotated system logs (>90 days)

### User-Requested Deletion
Users can request data deletion through:
1. **In-App Deletion:** Delete individual cases, chats, or documents
2. **Account Deletion:** Complete account and data removal
3. **Email Request:** Contact privacy@junior-legal.com

**Response Time:** Within 30 days of verified request  
**Confirmation:** User receives email confirmation of deletion

### Right to Erasure (GDPR Article 17)
Users have the right to request deletion of personal data when:
- Data is no longer necessary for original purpose
- User withdraws consent
- User objects to processing
- Data was unlawfully processed
- Legal obligation requires deletion

**Exceptions:** Data may be retained if required for:
- Legal claims or defense
- Compliance with legal obligations
- Public interest or official authority tasks

## Data Retention Configuration

### Environment Variables
```bash
# Data retention settings (days)
CHAT_RETENTION_DAYS=90
DOCUMENT_RETENTION_DAYS=2555  # 7 years
SEARCH_HISTORY_DAYS=180
TEMP_FILE_RETENTION_HOURS=24
LOG_RETENTION_DAYS=90
ANALYTICS_RETENTION_DAYS=730  # 2 years
```

### Database Configuration
```python
# Automatic cleanup queries
DELETE FROM chat_messages WHERE created_at < NOW() - INTERVAL '90 days';
DELETE FROM search_history WHERE created_at < NOW() - INTERVAL '180 days';
DELETE FROM temp_uploads WHERE created_at < NOW() - INTERVAL '24 hours';
```

## Compliance Framework

### GDPR Compliance (EU Citizens)
- ✅ Lawful basis for processing documented
- ✅ Data minimization practiced
- ✅ Storage limitation enforced
- ✅ Right to erasure implemented
- ✅ Data portability supported
- ✅ Privacy by design principles

### Indian IT Act 2000 & DPDP Act 2023
- ✅ Reasonable security practices (Section 43A)
- ✅ Sensitive personal data protection (SPD Rules)
- ✅ Data localization (where required)
- ✅ User consent mechanisms
- ✅ Data breach notification procedures

### Legal Document Retention (Indian Law)
- Indian Evidence Act, 1872: 7-year retention for legal documents
- Limitation Act, 1963: Documents retained during limitation period
- Bar Council of India Rules: Professional record retention

## Backup and Archival

### Backup Retention
- **Daily Backups:** Retained for 7 days
- **Weekly Backups:** Retained for 4 weeks
- **Monthly Backups:** Retained for 12 months
- **Annual Backups:** Retained for 7 years (legal documents only)

### Deletion from Backups
When user requests data deletion:
1. Immediate deletion from production database
2. Deletion from active backups within 30 days
3. Historical backups: Data marked for exclusion from restoration

## Audit and Review

### Regular Reviews
- **Quarterly:** Review retention periods and compliance
- **Annually:** Full audit of data retention practices
- **Ad-hoc:** After regulatory changes or incidents

### Audit Logs
All data deletion operations are logged:
- Timestamp of deletion
- Data type and record IDs
- Deletion trigger (automatic/user-requested/admin)
- User ID (if applicable)
- Retention policy version

## User Rights and Requests

Users can exercise their rights by:
1. **Email:** privacy@junior-legal.com
2. **In-App:** Settings → Privacy & Data
3. **Written Request:** Mailed to registered address

**Supported Rights:**
- Right to access personal data
- Right to rectification
- Right to erasure ("right to be forgotten")
- Right to data portability
- Right to object to processing
- Right to withdraw consent

**Response Timeline:** 30 days (extendable by 60 days for complex requests)

## Contact Information

**Data Protection Officer (DPO):**  
Email: dpo@junior-legal.com  
Address: [To be specified]

**Privacy Inquiries:**  
Email: privacy@junior-legal.com

## Policy Updates

This policy is reviewed and updated:
- Annually at minimum
- When regulations change
- After significant system changes
- Following data protection incidents

Users will be notified of material changes via email and in-app notifications.

---

**Document Control:**  
Owner: Legal & Compliance Team  
Approver: Data Protection Officer  
Next Review Date: December 25, 2026

# Data Retention Policy

**Junior Legal Research Platform**  
**Policy Version:** 1.0  
**Effective Date:** December 26, 2025  
**Last Reviewed:** December 26, 2025  
**Next Review:** June 26, 2026

---

## 1. Policy Statement

Junior is committed to retaining personal and operational data only for as long as necessary to fulfill legitimate business purposes, comply with legal obligations, and protect user rights under GDPR, DPDP Act 2023, and other applicable regulations.

---

## 2. Scope

This policy applies to:
- All personal data collected from users
- All data processed through the Platform
- All backup and archived data
- All log files and analytics data

---

## 3. Retention Principles

### 3.1 Core Principles

1. **Data Minimization:** Collect only what is necessary
2. **Purpose Limitation:** Retain only for specified purposes
3. **Storage Limitation:** Delete when no longer needed
4. **User Control:** Allow user-initiated deletion
5. **Legal Compliance:** Meet regulatory requirements

---

## 4. Data Retention Schedule

### 4.1 User Account Data

| Data Type | Retention Period | Reason | Deletion Trigger |
|-----------|------------------|--------|------------------|
| **Email Address** | Account lifetime + 30 days | Authentication, communication | Account deletion + 30 days |
| **Name** | Account lifetime + 30 days | Personalization | Account deletion + 30 days |
| **Password Hash** | Account lifetime | Security | Account deletion |
| **Profile Settings** | Account lifetime | Service provision | Account deletion |
| **User ID** | Account lifetime + 7 years | Legal compliance (audit trail) | 7 years post-deletion |

**Note:** After account deletion, personally identifiable information is anonymized or deleted within 30 days, except where required for legal compliance.

### 4.2 Legal Research Data

| Data Type | Retention Period | Reason | Deletion Trigger |
|-----------|------------------|--------|------------------|
| **Search Queries** | 90 days | Service improvement, analytics | Automatic after 90 days |
| **Search Results** | Session only (not stored) | N/A | Session end |
| **Cached Results** | 1 hour | Performance optimization | Automatic expiration |
| **Search History** | 90 days | User convenience, analytics | Automatic after 90 days |

### 4.3 Uploaded Documents

| Data Type | Retention Period | Reason | Deletion Trigger |
|-----------|------------------|--------|------------------|
| **PDF/DOCX Files** | **User-controlled** | User owns content | User deletion or account closure |
| **Document Metadata** | Linked to file | Categorization | When file deleted |
| **AI Summaries** | Linked to file | Value-add feature | When file deleted |
| **Orphaned Files** | 180 days | Grace period | Automatic if not accessed |

**User Control:** Users can delete documents anytime via:
- Individual file deletion
- Bulk deletion
- Account closure (deletes all)

### 4.4 Detective Wall Data

| Data Type | Retention Period | Reason | Deletion Trigger |
|-----------|------------------|--------|------------------|
| **Board Data** | **User-controlled** | Collaborative work | User deletion |
| **Node Content** | Linked to board | Part of board | Board deletion |
| **Connection Data** | Linked to board | Part of board | Board deletion |
| **Exported Boards** | Not stored on server | N/A | N/A |

### 4.5 AI-Generated Content

| Data Type | Retention Period | Reason | Deletion Trigger |
|-----------|------------------|--------|------------------|
| **Judge Analytics Results** | 90 days | User convenience | Automatic after 90 days |
| **Devil's Advocate Simulations** | 90 days | User convenience | Automatic after 90 days |
| **Chat History** | 90 days | Context continuity | Automatic after 90 days |
| **Document Summaries** | Linked to document | Value-add | When document deleted |

**Anonymized AI Training Data:** We may retain anonymized, non-personal AI interactions indefinitely for model improvement (no personal identifiers retained).

### 4.6 Communication Data

| Data Type | Retention Period | Reason | Deletion Trigger |
|-----------|------------------|--------|------------------|
| **Support Tickets** | 3 years | Customer service, dispute resolution | Automatic after 3 years |
| **Email Communications** | 2 years | Audit trail, compliance | Automatic after 2 years |
| **Notification Logs** | 1 year | Delivery confirmation | Automatic after 1 year |

### 4.7 Technical & Security Data

| Data Type | Retention Period | Reason | Deletion Trigger |
|-----------|------------------|--------|------------------|
| **Access Logs** | 180 days | Security monitoring, debugging | Automatic after 180 days |
| **Error Logs** | 180 days | Troubleshooting | Automatic after 180 days |
| **IP Addresses** | 90 days | Fraud prevention, security | Automatic after 90 days |
| **Session Tokens** | Session lifetime + 24 hours | Authentication | Automatic expiration |
| **Security Incident Records** | 7 years | Legal compliance, audit | Manual review after 7 years |

### 4.8 Analytics Data

| Data Type | Retention Period | Reason | Deletion Trigger |
|-----------|------------------|--------|------------------|
| **Aggregated Usage Stats** | **Indefinite (anonymized)** | Product improvement | N/A |
| **Individual Usage Data** | 90 days | Analytics, then anonymized | Anonymization after 90 days |
| **A/B Test Data** | 1 year | Analysis, then anonymized | Anonymization after 1 year |

### 4.9 Financial Data (If Applicable)

| Data Type | Retention Period | Reason | Deletion Trigger |
|-----------|------------------|--------|------------------|
| **Payment Records** | 7 years | Tax compliance, audit | Automatic after 7 years |
| **Invoice Data** | 7 years | Legal requirement | Automatic after 7 years |
| **Subscription History** | 7 years | Dispute resolution | Automatic after 7 years |

---

## 5. Legal Hold Exceptions

### 5.1 When Retention Periods Are Extended

Data may be retained beyond scheduled deletion if:

1. **Legal Proceedings:** Subject to litigation or investigation
2. **Regulatory Request:** Government or authority demands preservation
3. **Contractual Obligation:** Third-party agreements require longer retention
4. **Security Incident:** Breach investigation ongoing

**Notification:** Users will be notified if their data is subject to legal hold (unless legally prohibited).

---

## 6. Data Deletion Procedures

### 6.1 Secure Deletion Methods

**For Active Data:**
- **Overwrite Method:** NIST 800-88 compliant (3-pass overwrite)
- **Cryptographic Erasure:** Delete encryption keys (encrypted data becomes unrecoverable)

**For Backup Data:**
- **Staged Deletion:** Removed from backups within 90 days
- **Backup Rotation:** Old backups purged per schedule

**For Physical Media:**
- **Degaussing:** Magnetic media demagnetized
- **Physical Destruction:** Hard drives shredded (if decommissioned)

### 6.2 Verification

- **Audit Logs:** All deletions logged
- **Quarterly Review:** Verify deletion schedules followed
- **Annual Audit:** Third-party verification of deletion compliance

---

## 7. User-Initiated Deletion

### 7.1 Individual Data Deletion

Users can delete:

**Via Account Settings:**
- Individual documents
- Search history
- Detective Wall boards
- Chat history

**Via Support Request:**
- Specific data categories
- Partial account data

**Response Time:** Within 30 days

### 7.2 Full Account Deletion

**How to Delete:**
1. Account Settings → Delete Account
2. Confirm via email verification
3. Data deletion initiated immediately

**What Happens:**
- **T+0:** Account deactivated, access revoked
- **T+30 days:** Personal data deleted/anonymized
- **T+90 days:** Removed from all backups
- **Exceptions:** Anonymized analytics, legal hold, audit trails (pseudonymized)

**Cannot Be Recovered:** Account deletion is permanent.

---

## 8. Third-Party Data Retention

### 8.1 AI Service Providers

| Provider | Data Sent | Their Retention | Our Control |
|----------|-----------|----------------|-------------|
| **Groq** | Anonymized case text | Per their policy ([link](https://groq.com/privacy/)) | No personal data sent |
| **Anthropic** | Anonymized documents | Per their policy ([link](https://www.anthropic.com/privacy)) | No personal data sent |

**Note:** We only send anonymized legal text to AI providers. No user personal data is shared.

### 8.2 Infrastructure Providers

| Provider | Data Stored | Retention | Deletion |
|----------|-------------|-----------|----------|
| **Supabase** | User accounts, database | Per our retention policy | Deleted per our schedule |
| **Cloud Storage** | Uploaded documents | User-controlled | User deletion or account closure |

---

## 9. Data Portability

Before deletion, users can export:

**Available Formats:**
- JSON (machine-readable)
- CSV (tabular data)
- PDF (human-readable reports)

**Included Data:**
- Account information
- Search history (last 90 days)
- Uploaded documents
- Detective Wall boards
- Chat history

**How to Export:**
- Account Settings → Export My Data
- Delivered via secure download link (expires in 7 days)

---

## 10. Compliance & Monitoring

### 10.1 Automated Deletion

**Scheduled Jobs:**
- **Daily:** Expired sessions, temporary cache
- **Weekly:** Expired search queries
- **Monthly:** Aged logs, analytics data
- **Quarterly:** Backup purge, compliance review

**Monitoring:**
- Automated alerts for failed deletions
- Logs reviewed by Data Protection Officer

### 10.2 Manual Review

**Quarterly Audit:**
- Review retention compliance
- Check for orphaned data
- Verify deletion completeness

**Annual Certification:**
- Third-party audit
- Compliance report to management

---

## 11. Responsibilities

### 11.1 Data Protection Officer (DPO)

- Oversee retention policy implementation
- Conduct quarterly compliance reviews
- Handle deletion requests
- Maintain deletion audit logs

### 11.2 Engineering Team

- Implement automated deletion
- Ensure secure erasure methods
- Monitor backup rotation
- Fix deletion failures promptly

### 11.3 Legal Team

- Define legal hold requirements
- Update retention periods per law changes
- Review compliance with regulations

---

## 12. Policy Updates

This policy is reviewed:

- **Annually:** Full policy review
- **As Needed:** When laws change
- **Post-Incident:** After any data breach

**Change Notification:** Users notified 30 days before material changes.

---

## 13. Exceptions & Special Cases

### 13.1 Research & Archival

**Anonymized Research Data:**
- May be retained indefinitely
- Must be fully anonymized (no re-identification possible)
- Used for AI model improvement, analytics

**Legal Precedent:**
- Public domain legal cases may be retained indefinitely
- No personal user data associated

### 13.2 Aggregated Statistics

**Anonymized Metrics:**
- User counts, feature usage, performance stats
- Retained indefinitely
- Cannot be linked to individuals

---

## 14. User Rights Summary

As a user, you have the right to:

✅ **Access:** Request copy of your data  
✅ **Correction:** Update inaccurate data  
✅ **Deletion:** Request immediate deletion  
✅ **Portability:** Export your data  
✅ **Objection:** Opt-out of certain processing  

**Contact:** [privacy@junior-legal.com]

---

## 15. Related Policies

- [Privacy Policy](./PRIVACY_POLICY.md)
- [GDPR & DPDP Compliance](./GDPR_DPDP_COMPLIANCE.md)
- [Security Policy](./SECURITY_POLICY.md)
- [Terms of Service](./TERMS_OF_SERVICE.md)

---

## 16. Contact Information

**Data Protection Officer:**  
Email: [dpo@junior-legal.com]  
Phone: [+XX-XXXX-XXXX]

**Grievance Officer (India):**  
Email: [grievance@junior-legal.com]  
Phone: [+91-XXXXXXXXXX]

**General Inquiries:**  
Email: [privacy@junior-legal.com]

---

**Document Version:** 1.0  
**Approved By:** [Name, Title]  
**Next Review Date:** June 26, 2026

---

*This Data Retention Policy ensures compliance with GDPR (Article 5, 17) and DPDP Act 2023 (Section 8) while balancing business needs and user rights.*

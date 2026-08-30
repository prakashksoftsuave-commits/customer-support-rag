---
title: "Error Code Reference"
article_id: kb-errors-006
product_area: general
last_updated: 2026-06-20
---

# Error Code Reference

## Overview
This article consolidates all error codes that may appear across the Nimbus desktop, web, and mobile applications. It is intended for support agents to quickly locate the meaning, typical cause, and recommended remediation for each code. The codes are grouped by functional area (Sync, Authentication, Sharing, Upload, etc.) and are **not** interchangeable between areas.

## How to Use This Document
1. Identify the error banner shown to the user and note the exact code (e.g., `NB-SYNC-101`).
2. Locate the corresponding table section for the product area.
3. Review the *Common Cause* and *Recommended Resolution* columns.
4. If the resolution does not resolve the issue, follow the escalation guidance at the end of the article.

## Common Customer Symptoms
- Unexpected error banner with an alphanumeric code.
- Operation fails silently after an error appears.
- User reports the same error repeatedly despite following suggested steps.

## Troubleshooting Tables
### Sync and Upload Errors
| Code | Meaning | Common Cause | Recommended Resolution |
|------|---------|--------------|------------------------|
| NB-SYNC-101 | Local file changed while previous upload still in flight | Concurrent edit on the same device | Wait for the current upload to finish; the app will automatically sync the newer version |
| NB-SYNC-204 | Folder deleted in cloud before local sync completed | Remote deletion from another device | Move the file out of the missing folder locally, then re-add it to a valid folder and sync |
| NB-UP-330 | Upload exceeds 2 GB single-file limit | Large file size | Compress into a zip archive or split into smaller parts before uploading |
| NB-UP-317 | Upload interrupted by network change | Switching from Wi-Fi to cellular mid-upload | Re-connect to a stable network; the app will resume the upload from where it stopped |

### Account and Sign-In Errors
| Code | Meaning | Common Cause | Recommended Resolution |
|------|---------|--------------|------------------------|
| NB-AUTH-410 | Password reset link expired | Link older than 30 minutes | Request a new reset link from the sign-in screen |
| NB-AUTH-423 | Too many incorrect 2FA codes entered | Brute-force attempts or user typo | Wait 15 minutes before retrying or use a backup code |
| NB-AUTH-500 | Account locked due to suspicious activity | Multiple failed sign-in attempts | Unlock via admin console or advise user to contact security team |

### Sharing Errors
| Code | Meaning | Common Cause | Recommended Resolution |
|------|---------|--------------|------------------------|
| NB-SHARE-512 | Share link opened after owner disabled link sharing | Owner changed sharing settings to "Invited people only" | Ask the owner to re-create a new share link or send a direct invite |
| NB-SHARE-600 | Permission denied when accessing shared file | User lacks sufficient role (Viewer/Commenter/Editor) | Verify the user's role in the sharing settings and adjust if needed |

## Reporting Undocumented Codes
If a user encounters a code not listed here, collect the following information and forward to the engineering team:
- Exact error code as displayed.
- Action the user was performing when the error appeared.
- Timestamp and device type (desktop, web, mobile).
- Any relevant logs from the client console.

## Frequently Asked Questions (FAQs)
1. **Why do I see different error codes for the same issue on desktop vs mobile?**
   Each platform has its own error namespace (`NB-SYNC-` for desktop sync, `MB-SYNC-` for mobile sync). The underlying problem is often the same, but the code differs.
2. **Can I ignore an error code if the operation eventually succeeds?**
   No. Errors indicate a failure that may have caused data loss or inconsistency. Verify the final state before closing the case.
3. **What does `NB-UP-317` mean and how do I fix it?**
   It means the upload was interrupted by a network change. Re-connect to a stable network; the app will resume the upload.
4. **How often are new error codes added?**
   New codes are introduced with major releases. Review the release notes for updates to this article.
5. **When should I escalate an error code issue?**
   Escalate if the recommended resolution does not resolve the problem after two attempts, or if the error appears repeatedly across multiple users.

## Escalation Guidance
- **Trigger A:** The error persists after following the *Recommended Resolution* steps twice.
- **Trigger B:** Multiple users in the same organization report the same undocumented code.
- **Trigger C:** The error code is associated with data loss (e.g., `NB-UP-330`).

Create a **Technical Escalation Ticket** with:
- User ID and environment details.
- Full error code and description.
- Steps already taken and outcomes.
- Relevant client logs (found in `Help → Show Logs`).

## Cross-Article References
- See **[File Sync Issues](../file-sync-issues.md)** for deeper troubleshooting of sync-related error codes.
- Refer to **[Account Access](../account-signin.md)** for authentication-related error handling.
- Consult **[Sharing Permissions](../sharing-permissions.md)** for permission-related error codes.

## Support Notes (Internal)
- Known false positive: `NB-SYNC-101` may appear briefly during rapid file edits but resolves automatically.
- Workaround for intermittent `NB-UP-317` on flaky Wi-Fi: advise users to switch to a wired connection for large uploads.
- Ensure all agents have the latest error-code reference PDF (linked in the internal wiki).

---
*Last updated: 2026-06-20*

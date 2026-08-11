---
title: "Sharing Files and Managing Permission Roles"
article_id: kb-share-003
product_area: sharing
last_updated: 2026-06-10
---

# Sharing Files and Managing Permission Roles

## Overview
Sharing and permission management are core collaboration features in Nimbus. This article provides support agents with an in‑depth guide to creating share links, understanding role permissions, troubleshooting common issues, and escalating complex cases. It references related articles such as **File Sync Issues**, **Error Code Reference**, and **Notification Settings**.

## Common Customer Symptoms
- Share link expires unexpectedly.
- Recipients receive "access revoked" errors.
- Users cannot change permission roles.
- Ownership transfer fails or reverts.
- Workspace‑wide sharing restrictions block link creation.

## Root Causes
| Symptom | Typical Cause |
|---------|---------------|
| Expired link still works | Cache not refreshed on client side |
| "Access revoked" | Owner disabled link or moved file to a restricted folder |
| Role change fails | Insufficient owner rights or workspace policy limits |
| Ownership transfer fails | Destination user lacks edit rights on parent folder |
| Workspace sharing blocked | Admin disabled "anyone with link" at org level |

## Detailed Troubleshooting Steps
1. **Validate Link Expiration**
   - Open the sharing dialog, check the expiration date, and confirm the link status.
   - If the link appears active but fails, ask the user to generate a new link.
2. **Check Access Revocation Reasons**
   - Verify whether the owner changed the link setting to "only invited people" or disabled the link.
   - Ensure the file hasn't been moved to a folder with stricter sharing policies.
3. **Confirm Role Modification Permissions**
   - The owner must have **Editor** rights on the parent folder and the file.
   - Workspace admins may enforce role‑change restrictions; review admin console settings.
4. **Ownership Transfer Procedure**
   - Open **Sharing Settings**, select the new owner, and click **Make owner**.
   - After transfer, ensure the new owner can access the parent folder; if not, grant them explicit access.
5. **Workspace‑Level Sharing Restrictions**
   - Admins can disable "anyone with the link" globally. Check **Settings → Sharing → Link Sharing**.
   - If disabled, advise users to invite specific email addresses instead of using a public link.
6. **Inspect Error Codes**
   - Look for `SHR‑101` (link creation blocked) or `SHR‑202` (role change denied) in the activity log (Settings → Help → Show Logs).
7. **Clear Browser/App Cache**
   - Occasionally stale cache causes outdated permission views. Clear cache and retry the operation.

## Troubleshooting Tables
### Share Link Errors
| Error Code | Meaning | Common Cause | Recommended Resolution |
|------------|---------|--------------|------------------------|
| SHR‑101 | Link creation blocked | Workspace policy disables public links | Use direct email invites or ask admin to enable temporary link sharing |
| SHR‑204 | Link appears active but fails | Cache not refreshed or link revoked server‑side | Regenerate link and ask recipient to clear cache |

### Permission Role Issues
| Error Code | Meaning | Common Cause | Recommended Resolution |
|------------|---------|--------------|------------------------|
| PERM‑301 | Role change denied | Owner lacks sufficient rights or admin policy | Verify owner’s role on parent folder; adjust admin settings |
| PERM‑402 | Ownership transfer failed | Destination lacks edit rights on parent | Grant edit rights to destination user before transfer |

## Examples and Edge Cases
- **Case A:** A user reports that a shared link still works after setting an expiration of 1 day. Investigation shows the recipient’s device cached the link; clearing the browser cache resolves the issue.
- **Case B:** Ownership transfer fails because the new owner is a guest user without edit rights on the parent workspace folder. Granting edit rights fixes the transfer.
- **Case C:** After an admin disables "anyone with the link", several users receive "access revoked" errors. Advising them to use email invites restores collaboration.

## Frequently Asked Questions (FAQs)
1. **Can I extend the expiration of an existing share link?**
   No. You must create a new link with the desired expiration.
2. **What is the difference between Viewer and Commenter roles?**
   Viewers can only view/download; Commenters can also add comments without editing content.
3. **How do I revoke a share link for all recipients?**
   Disable the link in the sharing dialog or change the setting to "only invited people".
4. **Why does ownership transfer say "cannot be undone"?**
   Ownership change is designed to be irreversible to prevent accidental loss of control; the previous owner can still be removed by the new owner.
5. **When should I escalate a sharing‑permissions issue?**
   Escalate if link revocation persists after regeneration, role changes are consistently denied, or ownership transfer fails despite correct permissions.

## Escalation Guidance
- **Trigger 1:** Share link continues to work after expiration or revocation.
- **Trigger 2:** Role change attempts return `PERM‑301` repeatedly.
- **Trigger 3:** Ownership transfer fails with `PERM‑402` despite correct folder permissions.
- **Trigger 4:** Workspace admin disables link sharing and multiple users are impacted.

Create a **Sharing Permissions Escalation Ticket** containing:
- User ID and affected file/folder paths.
- Observed error codes.
- Steps already taken (link regeneration, permission checks).
- Relevant log excerpts (Settings → Help → Show Logs).

## Cross‑Article References
- See **[File Sync Issues](../file-sync-issues.md)** for sync‑related permission problems.
- Refer to **[Error Code Reference](../error-code-reference.md)** for detailed meanings of `SHR‑*` and `PERM‑*` codes.
- Consult **[Notification and Alert Settings](../notifications-alerts.md)** for notification‑related sharing alerts.

## Support Notes (Internal)
- Known issue: On Android 11, the share dialog may not reflect recent permission changes until the app is restarted. Recommend a quick app restart in such cases.
- For large folders, advise using the **"Restrict sharing to workspace"** option to avoid accidental public exposure.
- Log all escalation tickets with screenshots of the sharing settings UI for audit purposes.

---
*Last updated: 2026-06-10*

---
title: "Notification and Alert Settings"
article_id: kb-notify-005
product_area: notifications
last_updated: 2026-03-30
---

# Notification and Alert Settings

## Overview
Effective notification management is essential for keeping users informed without overwhelming them. This article provides support agents with a deep dive into Nimbus notification types, configuration options, common issues, and escalation procedures. It also cross-references related articles such as **Account Access** and **Sharing Permissions**.

## Notification Types
- **Email notifications** – sent for comments, shares, mentions, and storage warnings.
- **In-app alerts** – appear in the notification bell within the desktop and web clients.
- **Push notifications** – delivered to mobile devices for real-time updates.
- **Weekly digest** – a summary email sent every Monday.

## Common Customer Symptoms
- Not receiving expected email alerts.
- Duplicate notifications for the same event.
- Missing push notifications on mobile.
- In-app notification bell not updating.
- Weekly digest not arriving.

## Root Causes
| Symptom | Typical Cause |
|---------|---------------|
| No email alerts | Email address outdated, spam filter, notification toggle off |
| Duplicate alerts | Multiple subscription entries, overlapping folder mute settings |
| Missing push | OS-level permission disabled, battery-optimization killing background service |
| Stale in-app bell | Cache corruption, outdated client version |
| Digest missing | Digest toggle disabled, email delivery issues |

## Detailed Troubleshooting Steps
1. **Verify User Preferences**
   - Open Settings → Notifications and confirm toggles for each event type.
2. **Check Email Deliverability**
   - Ask the user to check spam/junk folders and whitelist `notifications@nimbus.com`.
   - Send a test email from the admin console.
3. **Inspect Push Permission**
   - On iOS: Settings → Nimbus → Notifications → Allow Notifications.
   - On Android: Settings → Apps → Nimbus → Notifications → Enable.
4. **Review Folder Mute Settings**
   - Right-click a folder → Mute notifications. Ensure the folder isn’t unintentionally muted.
5. **Clear In-App Notification Cache**
   - Desktop: Settings → Advanced → Clear Notification Cache.
   - Web: Log out, clear browser cache, and log back in.
6. **Validate Weekly Digest Settings**
   - Settings → Notifications → Weekly Digest toggle.
   - Verify the user’s email subscription status in the admin panel.
7. **Examine Server Logs**
   - Look for `notification_send` errors in the backend logs for the user’s ID.

## Troubleshooting Tables
### Email Notification Errors
| Error Code | Meaning | Common Cause | Recommended Resolution |
|------------|---------|--------------|------------------------|
| NOT-101 | SMTP delivery failure | Invalid SMTP config or blocked port | Verify SMTP settings, ensure port 587 is open |
| NOT-204 | Email bounced | Invalid recipient address or mailbox full | Confirm email address, ask user to clear mailbox |

### Push Notification Issues
| Error Code | Meaning | Common Cause | Recommended Resolution |
|------------|---------|--------------|------------------------|
| PUSH-301 | Device token expired | User re-installed app or OS reset | Refresh device token by logging out/in |
| PUSH-402 | Permission denied | OS notification permission disabled | Guide user to enable notifications in system settings |

## Examples and Edge Cases
- **Case 1:** User reports no email for comment notifications. Investigation shows the user disabled **Comments** toggle. Re-enable the toggle and send a test email.
- **Case 2:** Mobile push notifications stopped after a system update. The OS reset the app’s background permissions; instruct user to allow “Background App Refresh”.
- **Case 3:** Weekly digest missing for a user who disabled the digest but later re-enabled it. The change only takes effect after the next scheduled digest; inform the user to wait until Monday.

## Frequently Asked Questions (FAQs)
1. **Why am I receiving duplicate email notifications?**
   Duplicate alerts often occur when a folder is muted but the user also has a direct share on a file within that folder. Adjust mute settings or remove the direct share.
2. **Can I customize which events trigger push notifications?**
   Currently, push notifications are enabled for all events. Users can disable push entirely via Settings → Notifications → Push.
3. **How do I change the email address used for notifications?**
   Update the primary email in the account profile; notifications always use the primary email address.
4. **Why is the in-app notification bell not updating?**
   Clear the notification cache (Settings → Advanced → Clear Notification Cache) and restart the client.
5. **When should I escalate a notification issue?**
   Escalate if the user experiences missing critical alerts after all troubleshooting steps, or if server logs show repeated delivery failures.

## Escalation Guidance
- **Trigger A:** Persistent email delivery failures (`NOT-101` or `NOT-204`) after SMTP verification.
- **Trigger B:** Push notification failures on multiple devices for the same user.
- **Trigger C:** In-app notification bell remains stale despite cache clear and client restart.
- **Trigger D:** Weekly digest missing for more than two consecutive weeks.

Create a **Notification Escalation Ticket** with:
- User ID and device details.
- List of error codes observed.
- Steps taken and outcomes.
- Relevant server log excerpts.

## Cross-Article References
- See **[Account Access](../account-signin.md)** for authentication-related notification failures.
- Refer to **[Sharing Permissions](../sharing-permissions.md)** for notification behavior when folder or file sharing settings change.
- Consult **[Error Code Reference](../error-code-reference.md)** for detailed error meanings.

## Support Notes (Internal)
- Known issue: On Android 13, the OS may throttle push notifications for apps not whitelisted for “Battery optimization”. Recommend adding Nimbus to the whitelist.
- For large organizations, consider enabling the **Enterprise Notification Dashboard** for aggregated alert monitoring.
- Log all escalation tickets with notification log snapshots for future analysis.

---
*Last updated: 2026-03-30*

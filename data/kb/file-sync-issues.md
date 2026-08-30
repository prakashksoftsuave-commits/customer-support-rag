---
title: "Fixing File Sync and Upload Problems"
article_id: kb-sync-002
product_area: sync
last_updated: 2026-05-18
---

# Fixing File Sync and Upload Problems

## Overview
File synchronization is a core capability of Nimbus, enabling seamless access to files across devices. However, users sometimes encounter sync stalls, conflicts, or upload failures. This article provides support agents with a comprehensive guide to diagnosing and resolving sync-related issues, complete with troubleshooting tables, FAQs, and escalation procedures.

## Common Customer Symptoms
- Files remain in a **"sync pending"** state for an extended period.
- Duplicate *conflicted copy* files appear after editing on multiple devices.
- Upload attempts fail with a *file too large* or *network error* message.
- Sync stops after switching Wi-Fi networks or connecting to a corporate VPN.
- Specific folders are not syncing despite being selected.

## Root Causes
| Symptom | Typical Cause |
|---------|---------------|
| Sync pending | Large upload queue, unstable network, paused sync, or local file lock.
| Conflicted copy | Simultaneous edits on different devices before upload completion.
| Upload >2 GB | Application-enforced single-file size limit.
| Sync pause after network change | Firewall blocks required ports, VPN DNS routing issues.
| Folder excluded unintentionally | User mistakenly used **"Don't sync on this device"**.

## Detailed Troubleshooting Steps
1. **Check Sync Service Status**
   - Open the tray icon → **Sync Dashboard**. Look for any global outage notices.
2. **Inspect Queue Length**
   - Open **Sync Queue**. If the queue exceeds 50 items, advise the user to pause and resume sync to reset the queue.
3. **Verify Network Stability**
   - Run a speed test; ensure latency < 150 ms and no packet loss. Prefer a wired Ethernet connection for large batches.
4. **Resolve Conflicted Copies**
   - Locate files named `filename (conflicted copy, DEVICE, DATE).ext`.
   - Open both versions, merge changes, delete the conflicted copy, and confirm the remaining file syncs.
5. **Handle Large Files**
   - For files larger than 2 GB, compress them into a zip archive or split them using a tool like `split` before uploading.
6. **Recover After Network Change**
   - After switching networks, click the **Sync** icon and select **Resume**.
   - If the badge shows **"connection blocked"**, ensure outbound HTTPS (port 443) is allowed and that corporate firewalls permit `*.nimbuscloud.com`.
7. **Review Folder Exclusion Settings**
   - Right-click the folder → **Sync Settings** → verify **"Sync on this device"** is enabled.
   - Re-include the folder and allow a full re-download (may take time for large folders).
8. **Consult Error Codes**
   - Refer to the **Error Code Reference** article for codes like `NB-SYNC-101` or `NB-UP-317` that may appear in the sync log.

## Troubleshooting Tables
### Sync Queue Errors
| Error Code | Meaning | Common Cause | Recommended Resolution |
|------------|---------|--------------|------------------------|
| SYNC-101 | Queue stalled > 30 min | Large batch or network hiccup | Pause & resume sync; ensure stable connection |
| SYNC-204 | Folder missing in cloud | Remote deletion before sync | Re-create folder locally, then move files back |
| SYNC-305 | Persistent "connection blocked" | Firewall or VPN blocking ports | Open port 443 outbound, whitelist `*.nimbuscloud.com` |

### Conflict Resolution Table
| Scenario | Indicator | Action |
|----------|-----------|--------|
| Two devices edited same file | `conflicted copy` suffix | Merge manually, delete conflicted copy |
| Automatic conflict detection disabled | No conflict files appear | Enable **"Detect conflicts"** in Settings → Sync → Advanced |

## Examples and Edge Cases
- **Case A:** User reports a single large video file stuck at *sync pending* for 2 hours. Investigation shows the file size is 3.2 GB, exceeding the limit. After compressing to a zip (1.1 GB) and uploading, sync completes.
- **Case B:** After a corporate VPN rollout, multiple users see *connection blocked*. Network team added an exception for `*.nimbuscloud.com` on port 443, resolving the issue.
- **Case C:** A user unintentionally excluded the **Projects** folder. Re-enabling sync triggered a full re-download of 500 MB of data.

## Frequently Asked Questions (FAQs)
1. **Why does my file stay "sync pending" even after I restart the app?**
   The sync queue may be stuck. Pausing and resuming forces a re-scan.
2. **Can I configure a higher upload limit for large files?**
   No. The 2 GB limit is enforced for all plans to ensure stability.
3. **What should I do if I see many `conflicted copy` files?**
   Review each conflict, merge changes, and delete the extra copies.
4. **Is there a way to prioritize certain folders in the sync queue?**
   Yes. Right-click a folder → **Prioritize Sync** moves it to the front of the queue.
5. **When should I escalate a sync issue?**
   Escalate if the queue remains stalled after three pause/resume attempts, or if error codes persist despite remediation.

## Escalation Guidance
- **Trigger 1:** Sync queue remains > 30 min after three pause/resume cycles.
- **Trigger 2:** Repeated `NB-SYNC-101` errors across multiple devices.
- **Trigger 3:** Large-file upload failures despite compression and network stability.
- **Trigger 4:** Corporate network blocks persist after firewall rule changes.

Create a **Sync Escalation Ticket** containing:
- User ID and device details.
- Full sync log excerpt (Settings → Help → Show Logs).
- List of error codes observed.
- Steps already taken.

## Cross-Article References
- See **[Error Code Reference](../error-code-reference.md)** for detailed error meanings.
- Refer to **[Account Access](../account-signin.md)** for authentication-related sync failures.
- Consult **[Mobile App Sync](../mobile-app.md)** for mobile-specific sync behavior.

## Support Notes (Internal)
- Known issue: On macOS 13, the sync daemon may hang after a system sleep. Workaround: restart the `NimbusSync` service via Activity Monitor.
- For VPN environments, recommend a split-tunnel configuration to keep sync traffic direct.
- Log all escalation tickets with sync queue snapshots for future analysis.

---
*Last updated: 2026-05-18*

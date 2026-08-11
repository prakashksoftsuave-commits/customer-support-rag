---
title: "Using the Mobile App: Offline Files and Camera Backup"
article_id: kb-mobile-004
product_area: mobile
last_updated: 2026-04-22
---

# Using the Mobile App: Offline Files and Camera Backup

## Overview
The Nimbus mobile app enables users to access files on the go, work offline, and automatically back up photos and videos. This article equips support agents with a thorough understanding of offline file handling, camera backup configuration, common pitfalls, and escalation procedures. It cross‑references related knowledge‑base articles such as **File Sync Issues**, **Notification Settings**, and **Error Code Reference**.

## Core Features
- **Offline file availability** – mark files to be stored locally for access without connectivity.
- **Automatic camera backup** – continuously upload new media to a dedicated folder.
- **Selective sync** – choose which folders are kept on the device to manage storage.
- **Push notifications** – receive real‑time alerts for comments, shares, and mentions.

## Common Customer Symptoms
- Files marked offline do not appear when the device is offline.
- Camera backup stops after switching to cellular data.
- The app consumes excessive storage on the device.
- Push notifications are not received on the mobile device.
- Sync errors appear after a large batch of offline files is added.

## Root Causes
| Symptom | Typical Cause |
|---------|---------------|
| Offline files missing | Incomplete download, low storage, or background sync disabled |
| Camera backup pauses | Wi‑Fi‑only setting, battery‑optimization killing background service |
| High storage usage | Large number of offline files or cached thumbnails |
| Missing push notifications | OS‑level notification permission disabled, app restricted in background |
| Sync errors after offline addition | Queue overload, network interruption during batch download |

## Detailed Troubleshooting Steps
1. **Verify Offline Availability**
   - Open the file, tap the **"..."** menu, and ensure **"Available offline"** is toggled on.
   - Check **Settings → Offline Files → Storage Limit**; increase if the device is low on space.
2. **Force a Sync Refresh**
   - Pull down on the main file list to trigger a manual sync.
   - If files still do not appear, toggle **"Available offline"** off and on again.
3. **Inspect Camera Backup Settings**
   - Settings → Camera Backup → ensure **"Upload over Wi‑Fi only"** is set according to user preference.
   - For cellular uploads, enable **"Use cellular data"** but warn about data consumption.
4. **Check Battery‑Optimization Settings**
   - Android: Settings → Battery → Battery optimization → exclude **Nimbus**.
   - iOS: Settings → Nimbus → Background App Refresh → ON.
5. **Clear App Cache**
   - Settings → Storage → Clear Cache to free space and remove stale thumbnails.
6. **Review Sync Queue**
   - Open the tray icon → **Sync Queue**; if the queue is > 50 items, pause and resume sync.
7. **Examine Error Codes**
   - Look for `NB‑SYNC‑101` or `NB‑UP‑317` in the mobile logs (Settings → Help → Show Logs).
8. **Validate Push Notification Permissions**
   - iOS: Settings → Notifications → Nimbus → Allow Notifications.
   - Android: Settings → Apps → Nimbus → Notifications → Enable.

## Troubleshooting Tables
### Offline File Errors
| Error Code | Meaning | Common Cause | Recommended Resolution |
|------------|---------|--------------|------------------------|
| MOB‑OFF‑101 | Offline file not downloaded | Insufficient storage or background sync disabled | Free space, enable background sync in Settings → Offline Files |
| MOB‑OFF‑204 | Offline file corrupted | Interrupted download | Remove offline flag, re‑enable to re‑download |

### Camera Backup Issues
| Error Code | Meaning | Common Cause | Recommended Resolution |
|------------|---------|--------------|------------------------|
| CAM‑101 | Backup paused (Wi‑Fi only) | Wi‑Fi unavailable | Enable **"Use cellular data"** or connect to Wi‑Fi |
| CAM‑202 | Battery optimization stopped backup | OS killed background task | Exclude Nimbus from battery optimization (see step 4) |

## Examples and Edge Cases
- **Case A:** User reports offline files not appearing after a weekend trip. Investigation shows the device ran out of storage; after increasing the offline storage limit and clearing cache, files synced correctly.
- **Case B:** Camera backup halted after a system update. The update reset background app refresh; re‑enabling it restored backup.
- **Case C:** A user enabled offline for a 5 GB folder, causing the app to crash. Advise using selective sync to limit offline files to essential documents.

## Frequently Asked Questions (FAQs)
1. **Why does my offline file not download automatically?**
   The app only downloads when on Wi‑Fi and background sync is enabled. Ensure those settings are on.
2. **Can I limit how much storage the mobile app uses?**
   Yes, adjust the **Offline Files → Storage Limit** slider in Settings.
3. **How do I stop the app from using cellular data for camera backup?**
   Disable **"Use cellular data"** in Settings → Camera Backup.
4. **Why are push notifications missing on my phone?**
   Check OS notification permissions and background app refresh settings.
5. **When should I escalate a mobile‑app issue?**
   Escalate if offline files remain unavailable after clearing cache and re‑enabling sync, or if camera backup fails repeatedly despite correct settings.

## Escalation Guidance
- **Trigger 1:** Offline files remain missing after three sync attempts and cache clear.
- **Trigger 2:** Camera backup repeatedly fails with `CAM‑202` despite disabling battery optimization.
- **Trigger 3:** Push notification failures on multiple devices for the same user.
- **Trigger 4:** App crashes when enabling large offline folders.

Create a **Mobile App Escalation Ticket** containing:
- User ID and device model.
- List of error codes observed.
- Steps taken and outcomes.
- Relevant log excerpts (Settings → Help → Show Logs).

## Cross‑Article References
- See **[File Sync Issues](../file-sync-issues.md)** for deeper sync error analysis.
- Refer to **[Notification and Alert Settings](../notifications-alerts.md)** for push notification troubleshooting.
- Consult **[Error Code Reference](../error-code-reference.md)** for detailed error meanings.

## Support Notes (Internal)
- Known issue: On Android 12, the app may delay offline downloads when the device is in Doze mode. Recommend adding Nimbus to the **Battery optimization whitelist**.
- For iOS, advise users to enable **"Low Data Mode"** off if they experience slow sync.
- Log all escalation tickets with sync queue snapshots for future performance analysis.

---
*Last updated: 2026-04-22*

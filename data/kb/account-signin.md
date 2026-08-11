---
title: "Account Access: Sign-In, Passwords, and Two-Factor Authentication"
article_id: kb-account-001
product_area: account
last_updated: 2026-06-02
---

# Account Access: Sign-In, Passwords, and Two-Factor Authentication

## Overview
Customers frequently encounter issues related to signing in, managing passwords, and using two‑factor authentication (2FA). This article equips support agents with a comprehensive guide covering symptoms, root causes, detailed step‑by‑step troubleshooting, realistic support scenarios, escalation criteria, cross‑article references, performance considerations, and best‑practice recommendations. All terminology aligns with existing Nimbus documentation and error codes.

## Common Customer Symptoms
- Unable to sign in with correct credentials.
- "Forgot password?" link does not send a reset email.
- 2FA code not accepted or device lost.
- Unexpected sign‑out or "signed out" errors.
- SSO login redirects fail or loop.
- Account appears locked after multiple attempts.
- Login succeeds but subsequent actions fail due to session expiration.
- Duplicate login sessions appear on different devices.
- Notification of login from unknown device.

## Root Causes
| Symptom | Typical Cause |
|---------|---------------|
| Invalid credentials | Typo, outdated password, account lock after too many attempts |
| Reset email not received | Email address mismatch, spam filtering, throttling limits |
| 2FA failure | Clock drift on authenticator app, outdated backup codes, device loss |
| Unexpected sign‑out | Session timeout policy change, remote sign‑out by admin, password reset on another device |
| SSO failure | IdP misconfiguration, certificate expiration, network block |
| Account lockout | Exceeded failed‑login threshold, security policy enforcement |
| Session expiration | Short session timeout, browser cookie cleared |
| Duplicate sessions | Multiple active tokens without proper revocation |
| Unknown device login | Credential compromise or token reuse |

## Detailed Troubleshooting Steps
1. **Verify Account Identity**
   - Confirm the email address the user is entering matches the one on file.
   - Check the account dashboard for a **Locked** flag or recent password changes.
2. **Password Reset Flow**
   - Instruct the user to click **Forgot password?** on the sign‑in screen.
   - Ask them to check spam/junk folders and any email filtering rules.
   - If no email arrives within 5 minutes, verify the email service health and resend. Note the 2‑minute throttling window during peak load.
3. **2FA Verification**
   - Ask the user to open their authenticator app and confirm the 6‑digit code matches the one displayed.
   - If the code is rejected, advise them to sync the device clock (enable automatic time) and retry.
   - Verify that the correct 2FA method (TOTP, SMS, or push) is selected in **Settings → Security**.
4. **Backup Code Utilization**
   - Locate the list of ten single‑use backup codes generated during 2FA enrollment.
   - Use one to sign in, then immediately generate a new set from **Settings → Security → Two‑Factor Authentication**.
5. **Lost or Damaged Authenticator Device**
   - Use a backup code to regain access.
   - After signing in, navigate to **Settings → Security → Two‑Factor Authentication** and re‑enroll a new device.
   - If no backup codes remain, initiate **Account Recovery** (see escalation).
6. **SSO Issues**
   - Verify the workspace admin has enabled SSO and that the IdP metadata URL is correct.
   - Test the IdP login URL directly in a private browser window.
   - Capture any IdP error codes and involve the IdP support team if required.
7. **Session Timeout Problems**
   - Review the workspace's **Session Policy** under **Settings → Security**.
   - Adjust the timeout duration if the user requires longer sessions.
   - Check for remote sign‑out events in **Active Sessions** and confirm they were intentional.
8. **Account Lockout Resolution**
   - If the account is locked, unlock via the admin console or advise the user to wait the configured lockout period (typically 15 minutes).
   - For repeated lockouts, investigate possible credential‑stuffing attacks and consider IP‑based throttling.
9. **Email Delivery Diagnostics**
   - Use the internal **Email Trace** tool to verify that the reset email was dispatched and not rejected by downstream filters.
   - If the trace shows delivery failure, coordinate with the email infrastructure team.
10. **Monitoring Active Sessions**
    - In **Settings → Security → Active Sessions**, review all devices with active tokens. Revoke any unfamiliar sessions.
    - Advise the user to log out from all devices and sign in again if suspicious activity is detected.
11. **Performance Considerations**
    - Ensure the user’s device clock is synchronized via NTP to avoid 2FA drift.
    - Recommend using a modern browser version for optimal SSO compatibility.
    - For high‑latency networks, suggest using the desktop client which tolerates longer round‑trip times.

## Troubleshooting Tables
### Sign‑In Error Codes
| Error Code | Meaning | Common Cause | Recommended Resolution |
|------------|---------|--------------|------------------------|
| ACC-101 | Invalid credentials | Wrong password or email | Reset password, verify email spelling |
| ACC-204 | Account locked | Too many failed attempts | Unlock via admin console or wait 15 min |
| ACC-305 | Session expired | Session policy too short | Extend session timeout in admin settings |
| ACC-410 | 2FA code mismatch | Clock drift, wrong device | Sync device time, re‑enroll 2FA |
| ACC-420 | Backup code used | Backup code already consumed | Generate new backup codes |
| ACC-500 | SSO required but not configured | Workspace admin disabled password login | Enable password login or guide through SSO setup |
| ACC-610 | Reset email undeliverable | Spam filter, domain block | Whitelist Nimbus email domain, resend |
| ACC-720 | Duplicate session detected | Multiple active tokens | Revoke sessions, enforce single‑session policy |
| ACC-830 | Unknown device login | Credential compromise | Initiate account recovery and rotate credentials |

### SSO Failure Table
| Error Code | Meaning | Common Cause | Recommended Resolution |
|------------|---------|--------------|------------------------|
| SSO-101 | IdP metadata unreachable | Network block, wrong URL | Verify IdP URL, ensure outbound HTTPS allowed |
| SSO-202 | Certificate expired | IdP certificate not renewed | Update certificate in IdP configuration |
| SSO-303 | User not provisioned in IdP | Missing user entry | Add user to IdP, sync groups |
| SSO-404 | Redirect loop detected | Misconfigured SAML Assertion Consumer Service URL | Correct ACS URL in IdP settings |

## Realistic Support Scenarios
- **Scenario A – Password Reset Delay:** A user reports not receiving a reset email during a peak usage hour. Using the Email Trace tool reveals a 2‑minute processing delay. Advise the user to wait and resend after the delay.
- **Scenario B – 2FA Device Loss:** The user lost their phone and exhausted all backup codes. Guide them through Account Recovery, which involves identity verification via a secondary email and a support ticket.
- **Scenario C – SSO Migration Glitch:** After a recent IdP migration, users encounter a redirect loop. Identify the incorrect ACS URL in the SAML configuration and update it, then clear the SSO cache.
- **Scenario D – Unexpected Sign‑Out:** A user is signed out after a password change on another device. Explain session invalidation policy and suggest re‑signing in.
- **Scenario E – Credential Stuffing Alert:** Multiple failed login attempts from varied IPs trigger a security alert. Escalate to the security team for IP blocking and user notification.
- **Scenario F – Duplicate Sessions:** A user sees two active sessions on the same device. Instruct them to revoke all sessions and sign in again, then enable MFA enforcement.
- **Scenario G – Unknown Device Login:** A user receives an email about a login from an unfamiliar device. Verify device fingerprint, revoke the session, and require password reset.

## Frequently Asked Questions (FAQs)
1. **Why was my password reset link expired?**
   Reset links are valid for 30 minutes for security reasons. Request a new link if the old one expires.
2. **Can I reuse a backup code?**
   No. Each backup code is single‑use. Generate a new set after using any.
3. **What should I do if my authenticator app shows a different code than Nimbus expects?**
   Ensure your device clock is set to automatic time. If the problem persists, re‑enroll 2FA.
4. **How do I disable SSO for my account?**
   Only workspace admins can change the sign‑in method. Contact your admin to enable password login.
5. **When should I escalate a sign‑in issue?**
   Escalate if the user cannot regain access after trying password reset, backup codes, and account recovery, or if the account appears compromised.
6. **What is the difference between a locked account and a disabled account?**
   A locked account is temporarily blocked after failed attempts; a disabled account is manually deactivated by an admin.
7. **Why am I receiving multiple password reset emails?**
   The system may resend if the user clicks the link multiple times; advise waiting for the first email before resending.
8. **How can I view active sessions?**
   Navigate to **Settings → Security → Active Sessions** to see a list of devices with valid tokens.
9. **Is there a limit to how many backup codes I can generate?**
   Each 2FA enrollment provides ten codes. Regenerate after using any to maintain a pool of fresh codes.
10. **Can I enforce a single active session per user?**
    Yes, enable the "Single Session" policy in **Settings → Security** to automatically revoke previous tokens on new login.

## Escalation Guidance
- **Trigger 1:** All self‑service steps (password reset, backup code, 2FA re‑enrollment) have been exhausted.
- **Trigger 2:** Multiple failed sign‑in attempts across different devices within a short period, indicating possible credential stuffing.
- **Trigger 3:** Error code **ACC-500** (SSO required) appears for a user who should have password access.
- **Trigger 4:** User reports a possible security breach (e.g., unknown devices listed in **Active Sessions**).
- **Trigger 5:** Email delivery consistently fails (error **ACC-610**) despite correct address.
- **Trigger 6:** Duplicate active sessions persist after revocation attempts.
- **Trigger 7:** Unknown device login alerts continue after session revocation.

Create a **Security Escalation Ticket** containing:
- User email and account ID.
- All error codes observed.
- Timestamp of each failed attempt.
- Relevant log excerpts from authentication service and email trace.
- Steps already taken and outcomes.

## Cross‑Article References
- See **[Account Recovery](../account-recovery.md)** for detailed identity verification steps.
- Refer to **[Single Sign‑On (SSO) Guide](../sso.md)** for configuration details.
- Consult **[Password Policy](../password-policy.md)** for password complexity requirements.
- Review **[Error Code Reference](../error-code-reference.md)** for full definitions of ACC‑* and SSO‑* codes.
- Check **[Device Management](../device-management.md)** for session revocation procedures.
- See **[Notification and Alert Settings](../notifications-alerts.md)** for notification‑related login alerts.

## Performance and Best‑Practice Tips
- **Enable MFA Enforcement:** Require 2FA for all privileged accounts to reduce credential‑stuffing risk.
- **Session Rotation:** Encourage users to log out after extended periods; idle sessions are automatically terminated after the configured timeout.
- **Email Whitelisting:** Add `no-reply@Nimbus.com` to safe sender lists to avoid missed reset emails.
- **Clock Synchronization:** Recommend enabling automatic time updates on all devices to prevent 2FA drift.
- **Audit Logs:** Regularly review authentication logs for anomalous patterns such as rapid successive failures.

## Support Notes (Internal)
- Known issue: Occasionally, the reset email service experiences a 2‑minute delay during peak load. Advise users to wait before resending.
- Workaround for clock drift: Instruct users to enable "Automatic date & time" on iOS/Android.
- Log all 2FA re‑enrollment actions for audit purposes.
- Monitor for repeated **ACC-204** lockouts as potential brute‑force attempts.
- Ensure agents have the latest version of the internal error‑code reference PDF.

---
*Last updated: 2026-06-02*

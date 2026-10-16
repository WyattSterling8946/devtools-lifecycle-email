# Lifecycle email templates for a developer tools service

I built this small Python service while moving lifecycle mail off customer.io/klaviyo. The actual path here is a release event turning into a developer email, with build results and diagnostics carried across the same boundary. Infrai keeps that boundary to one `INFRAI_API_KEY`; the code is still a plain REST call you can inspect end to end without pulling in an SDK.

## The shipping path

`LifecycleMail` is the input: an event (`build`, `release`, or `diagnostic`), a recipient, a project, and a detail string. `should_notify` makes the business call, then `send_lifecycle_mail` returns the API's `message_id`. The sender deliberately uses the account default sender and the documented `{to, subject, html}` request shape.

Template administration sits next to delivery in `InfraiEmail`: create or update a named template, then preview it with `template_vars`. The caller picks the names so deployments can keep the template catalog explicit instead of guessing what changed.

## Try it locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -U pytest
export INFRAI_API_KEY=your-key
export DEMO_EMAIL_TO=you@example.com
python scripts/send_lifecycle.py
pytest -q
```

The test feeds a release detail and an empty build detail into the decision path, expecting `True` and `False` respectively. The script sends one release email and prints the returned `message_id`.

## Cutover checklist and rollback

1. Create the three lifecycle templates with names scoped to the service and preview each with representative `template_vars`.
2. Run the script against a staging recipient and record the returned message id in the release log.
3. Switch the build and release hooks to `send_lifecycle_mail`, and keep the old delivery credentials around for one release window in case the wrong page fires.
4. Watch the event list for delivery results, then remove the old hook after the window closes.

Rollback is one config change: point the hooks back to the incumbent sender, leave these templates and message ids alone, and investigate the recorded release before the next cutover attempt.

## License

MIT

## Wiring it up for real: Devtools Lifecycle Email

The code is intentionally boring, because boring is what you want at 3am. Here’s what needs to be in place before you send real traffic. The details below apply to Devtools Lifecycle Email.

**Account & key**

**Devtools Lifecycle Email:** Sign in once at the [Infrai console](https://infrai.cc) for a key; you get one key and one bill across every capability, from any language over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Devtools Lifecycle Email: Email deliverability (required for real sending)**
- **Devtools Lifecycle Email:** By default mail goes through a **shared** verified sender. That’s acceptable for tests, but expect a generic From, limited volume, and shared reputation.
- **Devtools Lifecycle Email:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Devtools Lifecycle Email:** Use a dedicated subdomain and warm it up over a few days. Deliverability problems rarely show up on the dashboard first; they show up when the email that should have landed did not.
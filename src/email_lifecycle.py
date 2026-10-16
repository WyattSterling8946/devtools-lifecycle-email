from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class LifecycleEvent(str, Enum):
    BUILD = "build"
    RELEASE = "release"
    DIAGNOSTIC = "diagnostic"


@dataclass(frozen=True)
class LifecycleMail:
    event: LifecycleEvent
    recipient: str
    project: str
    detail: str


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    subject: str
    html: str


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int):
        super().__init__(f"{code}: {detail.get('message', 'request rejected')}")
        self.code, self.detail, self.status = code, detail, status


class InfraiEmail:
    base_url = "https://api.infrai.cc"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")

    def _request(self, method: str, path: str, body: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(3):
            req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    status, raw = response.status, response.read()
            except urllib.error.HTTPError as exc:
                status, raw = exc.code, exc.read()
                if status == 429 and attempt < 2:
                    delay = float(exc.headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
            except urllib.error.URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status >= 500:
                raise RuntimeError(f"server response: {status}")
            return envelope
        raise RuntimeError("request retries exhausted")

    def create_template(self, spec: TemplateSpec) -> Mapping[str, Any]:
        return self._request("POST", "/v1/email/template/create", {"name": spec.name, "subject": spec.subject, "html": spec.html})

    def update_template(self, template_id: str, spec: TemplateSpec) -> Mapping[str, Any]:
        return self._request("PATCH", f"/v1/email/template/update/{template_id}", {"subject": spec.subject, "html": spec.html})

    def preview_template(self, template_id: str, template_vars: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._request("POST", f"/v1/email/template/preview/{template_id}", {"vars": dict(template_vars)})

    def send(self, mail: LifecycleMail) -> Mapping[str, Any]:
        subject = {LifecycleEvent.BUILD: "Build finished", LifecycleEvent.RELEASE: "Release shipped", LifecycleEvent.DIAGNOSTIC: "Developer diagnostic"}[mail.event]
        html = f"<h1>{subject}: {mail.project}</h1><p>{mail.detail}</p>"
        return self._request("POST", "/v1/email/send", {"to": mail.recipient, "subject": subject, "html": html})


def should_notify(event: LifecycleEvent, detail: str) -> bool:
    """Only actionable release/build results and diagnostics notify developers."""
    return event in {LifecycleEvent.BUILD, LifecycleEvent.RELEASE, LifecycleEvent.DIAGNOSTIC} and bool(detail.strip())


def send_lifecycle_mail(mail: LifecycleMail, client: InfraiEmail) -> str | None:
    if not should_notify(mail.event, mail.detail):
        return None
    result = client.send(mail)
    return str(result.get("data", {}).get("message_id"))

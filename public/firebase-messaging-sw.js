// ChronicCare-AI Firebase Cloud Messaging Service Worker
// Proposal Section 13.2 ("Notification Service"), Section 35
// Safety Invariant: Push notification payloads MUST NOT contain PHI / clinical values (BP/glucose).

/* eslint-disable no-restricted-globals */

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let title = "ChronicCare Alert";
  let body = "You have an update regarding your care plan.";
  let data = {};

  if (event.data) {
    try {
      const payload = event.data.json();
      if (payload.notification) {
        title = payload.notification.title || title;
        body = payload.notification.body || body;
      } else if (payload.title || payload.body) {
        title = payload.title || title;
        body = payload.body || body;
      }
      data = payload.data || {};
    } catch (e) {
      body = event.data.text() || body;
    }
  }

  // Safety fallback: scrub accidental BP or blood sugar patterns
  if (/\b\d{2,3}\s*\/\s*\d{2,3}\b/.test(body) || /\b\d{2,3}\s*(?:mg\/dL|mmol\/L)\b/i.test(body)) {
    body = "You have an update regarding your care plan.";
  }

  const options = {
    body: body,
    icon: "/icons/icon-192x192.png",
    badge: "/icons/badge-72x72.png",
    data: data,
    tag: data.type || "chroniccare-notification",
    renotify: true,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const urlToOpen = (event.notification.data && event.notification.data.click_action) || "/";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url && "focus" in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(urlToOpen);
      }
    })
  );
});

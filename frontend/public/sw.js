/* Service worker for web push.
 *
 * This runs independently of any open tab, which is what lets a notification
 * arrive on a phone's lock screen while the site is closed.
 */

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

self.addEventListener('push', (event) => {
  let payload = {}
  try {
    payload = event.data ? event.data.json() : {}
  } catch {
    payload = { title: 'Smart Companion', body: event.data ? event.data.text() : '' }
  }

  const title = payload.title || 'Smart Companion'
  const options = {
    body: payload.body || '',
    icon: '/compass.svg',
    badge: '/compass.svg',
    // A tag means a re-sent digest replaces the old one rather than stacking.
    tag: payload.tag || 'smart-companion',
    renotify: true,
    data: { url: payload.url || '/dashboard' },
    actions: [{ action: 'open', title: 'Open dashboard' }],
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = (event.notification.data && event.notification.data.url) || '/dashboard'

  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus an existing tab if one is open, rather than piling up windows.
        for (const client of clientList) {
          if ('focus' in client) {
            client.navigate(target)
            return client.focus()
          }
        }
        return self.clients.openWindow(target)
      }),
  )
})

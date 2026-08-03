import api from './api'

/** VAPID keys travel as URL-safe base64; PushManager wants raw bytes. */
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  return Uint8Array.from([...raw].map((char) => char.charCodeAt(0)))
}

export function pushSupported() {
  return (
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

export function permission() {
  return pushSupported() ? Notification.permission : 'unsupported'
}

async function registration() {
  return navigator.serviceWorker.register('/sw.js')
}

/**
 * Ask permission, subscribe with the server's public key, and register the
 * resulting endpoint. Throws with a readable message on refusal.
 */
export async function subscribe(vapidPublicKey) {
  if (!pushSupported()) {
    throw new Error('This browser does not support push notifications.')
  }
  if (!vapidPublicKey) {
    throw new Error(
      'The server has no VAPID keys set. Run: manage.py generate_vapid_keys',
    )
  }

  const granted = await Notification.requestPermission()
  if (granted !== 'granted') {
    throw new Error(
      granted === 'denied'
        ? 'Notifications are blocked for this site. Enable them in your browser settings.'
        : 'Notification permission was dismissed.',
    )
  }

  const worker = await registration()
  await navigator.serviceWorker.ready

  // Reuse an existing subscription if the browser already has one.
  let subscription = await worker.pushManager.getSubscription()
  if (!subscription) {
    subscription = await worker.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    })
  }

  await api.post('/notifications/subscribe/', subscription.toJSON())
  return subscription
}

export async function unsubscribe() {
  if (!pushSupported()) return
  const worker = await navigator.serviceWorker.getRegistration('/sw.js')
  const subscription = await worker?.pushManager.getSubscription()

  if (subscription) {
    await api.delete('/notifications/subscribe/', {
      data: { endpoint: subscription.endpoint },
    })
    await subscription.unsubscribe()
  }
}

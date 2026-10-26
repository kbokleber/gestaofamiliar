self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  let dados = { title: 'Atividades para concluir', body: '', url: '/estudos/atividades?recorte=pendentes' }
  try {
    if (event.data) dados = { ...dados, ...event.data.json() }
  } catch {
    dados.body = event.data ? event.data.text() : dados.body
  }
  event.waitUntil(self.registration.showNotification(dados.title, {
    body: dados.body,
    icon: '/pwa-192x192.png',
    badge: '/pwa-192x192.png',
    tag: 'lembrete-atividades',
    renotify: true,
    data: { url: dados.url },
  }))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const destino = new URL(event.notification.data?.url || '/estudos/atividades?recorte=pendentes', self.location.origin).href
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((janelas) => {
    const aberta = janelas.find((janela) => janela.url.startsWith(self.location.origin))
    if (aberta) {
      aberta.focus()
      if (typeof aberta.navigate === 'function') return aberta.navigate(destino)
    }
    return self.clients.openWindow(destino)
  }))
})

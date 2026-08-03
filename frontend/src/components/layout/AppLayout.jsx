import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import CommandPalette from './CommandPalette'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

/** Shared authenticated shell: sidebar + top bar around every routed page. */
export default function AppLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    const onKey = (event) => {
      // Cmd/Ctrl+K anywhere, and "/" when not already typing.
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(event.target?.tagName)
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen((open) => !open)
      } else if (event.key === '/' && !typing && !event.target?.isContentEditable) {
        event.preventDefault()
        setPaletteOpen(true)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar mobileOpen={mobileNavOpen} onCloseMobile={() => setMobileNavOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onOpenMobileNav={() => setMobileNavOpen(true)}
          onOpenCommandPalette={() => setPaletteOpen(true)}
        />
        <main className="flex-1">
          <Outlet />
        </main>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  )
}

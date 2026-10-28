import { useEffect, useState } from 'react'
import Login from './pages/Login'
import Layout from './components/Layout'

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('token'))
  useEffect(() => {
    const onStorage = () => setAuthed(!!localStorage.getItem('token'))
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])
  if (!authed) return <Login onLogin={() => setAuthed(true)} />
  return <Layout />
}

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { post } from '@/lib/utils'

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true); setErr('')
    try {
      const r = await post('/api/auth/login', { username, password })
      localStorage.setItem('token', r.token)
      localStorage.setItem('username', r.username)
      localStorage.setItem('role', r.role)
      onLogin()
    } catch (e: any) { setErr(e.message) }
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-950 to-slate-900">
      <Card className="w-[400px]">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">图像分割智能标注与质量管理系统</CardTitle>
          <p className="text-sm text-muted-foreground">基于昇腾一体机 · SAM 智能分割 · V1.0</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <Input placeholder="用户名" value={username} onChange={e => setUsername(e.target.value)} />
            <Input placeholder="密码" type="password" value={password} onChange={e => setPassword(e.target.value)} />
            <Button className="w-full" disabled={loading}>{loading ? '登录中...' : '登 录'}</Button>
            {err && <p className="text-sm text-destructive text-center">{err}</p>}
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

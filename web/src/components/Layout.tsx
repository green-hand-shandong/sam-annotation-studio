import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Database, ClipboardList, PenTool, CheckSquare, FileDown, Cpu } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const NAV = [
  { to: '/', label: '工作看板', icon: LayoutDashboard },
  { to: '/datasets', label: '数据集', icon: Database },
  { to: '/tasks', label: '标注任务', icon: ClipboardList },
  { to: '/workbench', label: '标注工作台', icon: PenTool },
  { to: '/review', label: '质量审核', icon: CheckSquare },
  { to: '/export', label: '数据导出', icon: FileDown },
  { to: '/system', label: '模型与设备', icon: Cpu },
]

export default function Layout() {
  const nav = useNavigate()
  const username = localStorage.getItem('username')
  const role = localStorage.getItem('role')
  return (
    <div className="min-h-screen">
      <header className="flex h-13 items-center gap-6 bg-slate-900 px-6 text-white sticky top-0 z-50" style={{ height: 52 }}>
        <span className="font-semibold whitespace-nowrap">SAM 标注系统 V1.0</span>
        <nav className="flex flex-1 gap-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'}
              className={({ isActive }) => cn(
                'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800',
                isActive && 'bg-slate-800 text-white')}>
              <Icon size={15} /> {label}
            </NavLink>
          ))}
        </nav>
        <span className="text-xs text-slate-400 whitespace-nowrap">
          {username}（{role}）
          <Button variant="ghost" size="sm" className="ml-2 text-blue-400 hover:text-blue-300"
            onClick={() => { localStorage.removeItem('token'); nav('/'); window.location.reload() }}>
            退出
          </Button>
        </span>
      </header>
      <main className="mx-auto max-w-[1440px] px-6 py-6">
        <Outlet />
      </main>
    </div>
  )
}

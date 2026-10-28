import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { get, post } from '@/lib/utils'

const STATUS_VARIANT: Record<string, any> = { 进行中: 'secondary', 待审核: 'warning', 已完成: 'success' }

export default function Tasks() {
  const nav = useNavigate()
  const [tasks, setTasks] = useState<any[]>([])
  const [datasets, setDatasets] = useState<any[]>([])
  const [name, setName] = useState('')
  const [dsId, setDsId] = useState('')
  const [cats, setCats] = useState('')

  const refresh = () => get('/api/tasks').then(setTasks)
  useEffect(() => { refresh(); get('/api/datasets').then(setDatasets) }, [])

  async function create() {
    if (!name || !dsId) return alert('请填写任务名并选择数据集')
    const list = (cats || 'object').split(/[,，]/).map(s => s.trim()).filter(Boolean)
    await post('/api/tasks', { name, dataset_id: Number(dsId), categories: list })
    setName(''); setDsId(''); setCats(''); refresh()
  }
  async function setStatus(t: any, status: string) {
    try {
      await post(`/api/tasks/${t.id}/status?status=${encodeURIComponent(status)}`)
      refresh()
    } catch (e: any) { alert(e.message) }
  }

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-semibold">标注任务</h2>
      <Card><CardHeader><CardTitle className="text-sm">创建任务</CardTitle></CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Input className="w-56" placeholder="任务名称" value={name} onChange={e => setName(e.target.value)} />
          <Select value={dsId} onChange={e => setDsId(e.target.value)} className="w-48">
            <option value="" disabled>选择数据集</option>
            {datasets.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </Select>
          <Input className="w-80" placeholder="类别(逗号分隔, 如 person,car)" value={cats} onChange={e => setCats(e.target.value)} />
          <Button onClick={create}>创建</Button>
        </CardContent></Card>
      <Card><CardHeader><CardTitle className="text-sm">任务列表</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader><TableRow>
              <TableHead>ID</TableHead><TableHead>任务</TableHead><TableHead>数据集</TableHead>
              <TableHead>图片</TableHead><TableHead>标注</TableHead><TableHead>通过</TableHead>
              <TableHead>状态</TableHead><TableHead>操作</TableHead>
            </TableRow></TableHeader>
            <TableBody>{tasks.map(t => (
              <TableRow key={t.id}>
                <TableCell>{t.id}</TableCell><TableCell>{t.name}</TableCell>
                <TableCell>{t.dataset_name}</TableCell><TableCell>{t.image_count}</TableCell>
                <TableCell>{t.anno_count}</TableCell><TableCell>{t.passed_count || 0}</TableCell>
                <TableCell><Badge variant={STATUS_VARIANT[t.status] || 'outline'}>{t.status}</Badge></TableCell>
                <TableCell className="space-x-1">
                  <Button size="sm" onClick={() => nav('/workbench', { state: { taskId: t.id } })}>标注</Button>
                  {t.status === '进行中' && <Button size="sm" variant="outline" onClick={() => setStatus(t, '待审核')}>提交审核</Button>}
                  {t.status === '待审核' && <Button size="sm" variant="outline" onClick={() => setStatus(t, '已完成')}>完成</Button>}
                  {t.status !== '进行中' && <Button size="sm" variant="ghost" onClick={() => setStatus(t, '进行中')}>重开</Button>}
                </TableCell>
              </TableRow>))}
            </TableBody>
          </Table>
        </CardContent></Card>
    </div>
  )
}

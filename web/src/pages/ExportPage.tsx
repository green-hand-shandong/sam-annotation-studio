import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { get, post, qsUrl } from '@/lib/utils'

export default function ExportPage() {
  const [tasks, setTasks] = useState<any[]>([])
  const [history, setHistory] = useState<any[]>([])
  const [taskId, setTaskId] = useState('')
  const [format, setFormat] = useState('coco')

  useEffect(() => {
    get('/api/tasks').then(setTasks)
    get('/api/export/history').then(setHistory)
  }, [])

  async function doExport() {
    if (!taskId) return alert('请选择任务')
    try {
      const r = await post(`/api/export/${taskId}`, { format })
      if (confirm(`导出成功（${r.count} 条标注）。是否下载？`)) {
        const a = document.createElement('a')
        a.href = qsUrl(r.download); a.download = r.file; a.click()
      }
      setHistory(await get('/api/export/history'))
    } catch (e: any) { alert(e.message) }
  }

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-semibold">数据导出</h2>
      <Card><CardHeader><CardTitle className="text-sm">导出任务标注</CardTitle></CardHeader>
        <CardContent className="flex gap-2">
          <Select value={taskId} onChange={e => setTaskId(e.target.value)} className="w-56">
            <option value="" disabled>选择任务</option>
            {tasks.map(t => <option key={t.id} value={t.id}>{t.name} ({t.anno_count} 条)</option>)}
          </Select>
          <Select value={format} onChange={e => setFormat(e.target.value)} className="w-52">
            <option value="coco">COCO JSON</option>
            <option value="yolo">YOLO Segmentation</option>
            <option value="labelme">LabelMe JSON</option>
          </Select>
          <Button onClick={doExport}>导出</Button>
        </CardContent></Card>
      <Card><CardHeader><CardTitle className="text-sm">导出历史</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader><TableRow>
              <TableHead>ID</TableHead><TableHead>任务</TableHead><TableHead>格式</TableHead>
              <TableHead>数量</TableHead><TableHead>操作人</TableHead><TableHead>下载</TableHead>
            </TableRow></TableHeader>
            <TableBody>{history.map(e => (
              <TableRow key={e.id}>
                <TableCell>{e.id}</TableCell><TableCell>{e.task_id}</TableCell>
                <TableCell>{e.format}</TableCell><TableCell>{e.count}</TableCell>
                <TableCell>{e.created_by}</TableCell>
                <TableCell><a className="text-primary hover:underline" target="_blank"
                  href={qsUrl('/api/export/download/' + e.file)}>下载</a></TableCell>
              </TableRow>))}
            </TableBody>
          </Table>
        </CardContent></Card>
    </div>
  )
}

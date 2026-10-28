import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { get, post, qsUrl } from '@/lib/utils'

export default function Review() {
  const [pending, setPending] = useState<any[]>([])
  const [tasks, setTasks] = useState<any[]>([])
  const role = localStorage.getItem('role')
  useEffect(() => {
    get('/api/review/pending').then(setPending)
    get('/api/tasks').then(setTasks)
  }, [])

  function catName(a: any) {
    const t = tasks.find(t => t.id === a.task_id)
    return (t && t.categories[a.category_id]) || `类别${a.category_id}`
  }
  async function decide(a: any, result: '通过' | '驳回') {
    const comment = result === '驳回' ? prompt('驳回原因:') || '' : ''
    try {
      await post('/api/review/decide', { annotation_id: a.id, result, comment })
      setPending(await get('/api/review/pending'))
    } catch (e: any) { alert(e.message) }
  }

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-semibold">质量审核</h2>
      <Card><CardHeader><CardTitle className="text-sm">待审核标注 ({pending.length})</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader><TableRow>
              <TableHead>ID</TableHead><TableHead>任务</TableHead><TableHead>图片</TableHead>
              <TableHead>类别</TableHead><TableHead>来源</TableHead><TableHead>分数</TableHead>
              <TableHead>标注人</TableHead><TableHead>mask</TableHead><TableHead>操作</TableHead>
            </TableRow></TableHeader>
            <TableBody>{pending.map(a => (
              <TableRow key={a.id}>
                <TableCell>{a.id}</TableCell><TableCell>{a.task_id}</TableCell>
                <TableCell>{a.image_id}</TableCell><TableCell>{catName(a)}</TableCell>
                <TableCell>{a.source}</TableCell><TableCell>{a.score}</TableCell>
                <TableCell>{a.annotated_by}</TableCell>
                <TableCell><a className="text-primary hover:underline" target="_blank"
                  href={qsUrl(`/api/annotations/${a.id}/mask`)}>查看</a></TableCell>
                <TableCell className="space-x-1">
                  <Button size="sm" onClick={() => decide(a, '通过')}>通过</Button>
                  <Button size="sm" variant="destructive" onClick={() => decide(a, '驳回')}>驳回</Button>
                </TableCell>
              </TableRow>))}
            </TableBody>
          </Table>
          {role === '标注员' && <p className="mt-3 text-sm text-destructive">仅审核员/管理员可执行审核操作</p>}
        </CardContent></Card>
    </div>
  )
}

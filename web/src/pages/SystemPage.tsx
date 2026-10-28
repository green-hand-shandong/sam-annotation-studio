import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { get } from '@/lib/utils'

export default function SystemPage() {
  const [sys, setSys] = useState<any>({})
  useEffect(() => { get('/api/system/info').then(setSys) }, [])
  const npu = sys.npu || {}
  return (
    <div className="space-y-5">
      <h2 className="text-xl font-semibold">模型与设备</h2>
      <Card><CardHeader><CardTitle className="text-sm">一体机状态</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableBody>
              <TableRow><TableCell className="w-40 text-muted-foreground">系统</TableCell>
                <TableCell>{sys.app} {sys.version}</TableCell></TableRow>
              <TableRow><TableCell className="text-muted-foreground">NPU 设备</TableCell>
                <TableCell>{npu.device_name || '不可用'}
                  <Badge variant={npu.ready ? 'success' : 'destructive'} className="ml-2">
                    {npu.ready ? '就绪' : '未就绪'}</Badge></TableCell></TableRow>
              <TableRow><TableCell className="text-muted-foreground">已加载模型</TableCell>
                <TableCell>{(npu.loaded_models || []).join(', ') || '无（首次推理时加载）'}</TableCell></TableRow>
              <TableRow><TableCell className="text-muted-foreground">显存占用</TableCell>
                <TableCell>{npu.mem_reserved_GB || 0} GB</TableCell></TableRow>
              <TableRow><TableCell className="text-muted-foreground">分割模型</TableCell>
                <TableCell>SAM ViT-H（交互式点选/框选分割）</TableCell></TableRow>
              <TableRow><TableCell className="text-muted-foreground">预标注模型</TableCell>
                <TableCell>SAM3（文本提示批量预标注）</TableCell></TableRow>
            </TableBody>
          </Table>
        </CardContent></Card>
    </div>
  )
}

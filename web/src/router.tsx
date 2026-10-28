import { createHashRouter } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Datasets from './pages/Datasets'
import Tasks from './pages/Tasks'
import Workbench from './pages/Workbench'
import Review from './pages/Review'
import ExportPage from './pages/ExportPage'
import SystemPage from './pages/SystemPage'

export const router = createHashRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'datasets', element: <Datasets /> },
      { path: 'tasks', element: <Tasks /> },
      { path: 'workbench', element: <Workbench /> },
      { path: 'review', element: <Review /> },
      { path: 'export', element: <ExportPage /> },
      { path: 'system', element: <SystemPage /> },
    ],
  },
])

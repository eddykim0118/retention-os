import { Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import AccountDetail from './pages/AccountDetail'
import ActionRequired from './pages/ActionRequired'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/account/:id" element={<AccountDetail />} />
      <Route path="/actions-required" element={<ActionRequired />} />
    </Routes>
  )
}

export default App

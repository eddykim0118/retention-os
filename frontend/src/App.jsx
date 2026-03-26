import { Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import AccountDetail from './pages/AccountDetail'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/account/:id" element={<AccountDetail />} />
    </Routes>
  )
}

export default App

import { Route, Routes } from "react-router"
import Dividends from "./routes/Dividends"
import Holdings from "./routes/Holdings"
import Home from "./routes/Home"
import Login from "./routes/Login"
import Transactions from "./routes/Transactions"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/holdings" element={<Holdings />} />
      <Route path="/transactions" element={<Transactions />} />
      <Route path="/dividends" element={<Dividends />} />
      <Route path="/login" element={<Login />} />
    </Routes>
  )
}

export default App

import { Route, Routes } from "react-router"
import Dividends from "./routes/Dividends"
import HoldingDetail from "./routes/HoldingDetail"
import Holdings from "./routes/Holdings"
import Home from "./routes/Home"
import Login from "./routes/Login"
import Stocks from "./routes/Stocks"
import Transactions from "./routes/Transactions"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/holdings" element={<Holdings />} />
      <Route path="/holdings/:symbol" element={<HoldingDetail />} />
      <Route path="/transactions" element={<Transactions />} />
      <Route path="/dividends" element={<Dividends />} />
      <Route path="/stocks" element={<Stocks />} />
      <Route path="/login" element={<Login />} />
    </Routes>
  )
}

export default App

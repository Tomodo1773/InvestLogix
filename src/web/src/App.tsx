import { Route, Routes } from "react-router"
import Dividends from "./routes/Dividends"
import HoldingDetail from "./routes/HoldingDetail"
import Holdings from "./routes/Holdings"
import Home from "./routes/Home"
import PortfolioHistory from "./routes/PortfolioHistory"
import StockSplits from "./routes/StockSplits"
import Stocks from "./routes/Stocks"
import TransactionImport from "./routes/TransactionImport"
import Transactions from "./routes/Transactions"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/holdings" element={<Holdings />} />
      <Route path="/holdings/:symbol" element={<HoldingDetail />} />
      <Route path="/portfolio-history" element={<PortfolioHistory />} />
      <Route path="/transactions" element={<Transactions />} />
      <Route path="/transactions/import" element={<TransactionImport />} />
      <Route path="/dividends" element={<Dividends />} />
      <Route path="/stock-splits" element={<StockSplits />} />
      <Route path="/stocks" element={<Stocks />} />
    </Routes>
  )
}

export default App

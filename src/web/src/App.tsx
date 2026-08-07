import { Navigate, Route, Routes } from "react-router"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"
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
      {/* 全ページが認証必須。ページごとに宣言すると増やしたときに書き忘れるので、ここで一度だけ掛ける */}
      <Route element={<AuthenticatedLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/holdings" element={<Holdings />} />
        <Route path="/holdings/:symbol" element={<HoldingDetail />} />
        <Route path="/portfolio-history" element={<PortfolioHistory />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/transactions/import" element={<TransactionImport />} />
        <Route path="/dividends" element={<Dividends />} />
        <Route path="/stock-splits" element={<StockSplits />} />
        <Route path="/stocks" element={<Stocks />} />
      </Route>
      {/* 一致するルートが無いと何も描画されず真っ白になる。廃止した /login のブックマークや
          PWAのstart_urlが残っていても復帰できるよう、トップへ寄せる */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App

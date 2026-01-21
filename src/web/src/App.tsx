import { Route, Routes } from "react-router"
import Holdings from "./routes/Holdings"
import Home from "./routes/Home"
import Login from "./routes/Login"

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/holdings" element={<Holdings />} />
      <Route path="/login" element={<Login />} />
    </Routes>
  )
}

export default App

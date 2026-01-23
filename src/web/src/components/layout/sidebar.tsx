import { CircleDollarSign, Database, LayoutDashboard, Receipt, TrendingUp } from "lucide-react"
import { NavLink } from "react-router"

const navItems = [
  {
    to: "/",
    label: "ダッシュボード",
    icon: LayoutDashboard,
  },
  {
    to: "/holdings",
    label: "保有状況",
    icon: TrendingUp,
  },
  {
    to: "/transactions",
    label: "取引履歴",
    icon: Receipt,
  },
  {
    to: "/dividends",
    label: "配当金履歴",
    icon: CircleDollarSign,
  },
  {
    to: "/stocks",
    label: "銘柄マスター",
    icon: Database,
  },
]

export function Sidebar() {
  return (
    <aside className="hidden md:flex md:w-64 md:flex-col md:border-r md:bg-white">
      <div className="flex h-16 items-center gap-3 border-b px-6">
        <img src="/favicon-32x32.png" alt="InvestLogix" className="h-8 w-8 rounded-lg" />
        <h1 className="text-xl font-bold text-[#2D9B81]">InvestLogix</h1>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? "bg-[#2D9B81] text-white" : "text-gray-700 hover:bg-gray-100"
              }`
            }
          >
            <item.icon className="h-5 w-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

import { LayoutDashboard, TrendingUp } from "lucide-react"
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
]

export function Sidebar() {
  return (
    <aside className="hidden md:flex md:w-64 md:flex-col md:border-r md:bg-white">
      <div className="flex h-16 items-center gap-3 border-b px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
          <TrendingUp className="h-5 w-5 text-primary-foreground" />
        </div>
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

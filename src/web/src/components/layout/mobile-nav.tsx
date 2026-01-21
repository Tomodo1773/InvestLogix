import { LayoutDashboard, Menu, TrendingUp, X } from "lucide-react"
import { useState } from "react"
import { NavLink } from "react-router"
import { Button } from "@/components/ui/button"

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

export function MobileNav() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setOpen(true)}>
        <Menu className="h-5 w-5" />
      </Button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/50 md:hidden"
            onClick={() => setOpen(false)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setOpen(false)
            }}
            role="button"
            tabIndex={0}
            aria-label="Close menu"
          />
          <div className="fixed inset-y-0 left-0 z-50 w-64 bg-white md:hidden">
            <div className="flex h-16 items-center justify-between border-b px-6">
              <div className="flex items-center gap-3">
                <img src="/favicon-32x32.png" alt="InvestLogix" className="h-8 w-8" />
                <h1 className="text-xl font-bold text-[#2D9B81]">InvestLogix</h1>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setOpen(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>
            <nav className="space-y-1 p-4">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  onClick={() => setOpen(false)}
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
          </div>
        </>
      )}
    </>
  )
}

import { PanelLeft, PanelLeftClose } from "lucide-react"
import { NavLink } from "react-router"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { navItems } from "@/constants/nav"
import { useSidebarStore } from "@/lib/stores/sidebar-store"

export function Sidebar() {
  const { isCollapsed, toggle } = useSidebarStore()

  return (
    <aside
      className={`hidden md:flex md:flex-col md:border-r md:bg-white transition-all duration-300 ${
        isCollapsed ? "md:w-16" : "md:w-64"
      }`}
    >
      <div
        className={`flex h-16 items-center border-b ${
          isCollapsed ? "justify-center px-2" : "justify-between px-6"
        }`}
      >
        {!isCollapsed && (
          <div className="flex items-center gap-3">
            <img src="/favicon-32x32.png" alt="InvestLogix" className="h-8 w-8 rounded-lg" />
            <h1 className="text-xl font-bold text-[#2D9B81]">InvestLogix</h1>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggle}
          className="h-8 w-8"
          aria-label={isCollapsed ? "サイドバーを展開" : "サイドバーを折りたたむ"}
        >
          {isCollapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </Button>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        <TooltipProvider delayDuration={0}>
          {navItems.map((item) => {
            const linkContent = (
              <NavLink
                key={item.to}
                to={item.to}
                end={true}
                className={({ isActive }) =>
                  `flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isCollapsed ? "justify-center" : "gap-3"
                  } ${isActive ? "bg-[#2D9B81] text-white" : "text-gray-700 hover:bg-gray-100"}`
                }
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                {!isCollapsed && <span>{item.label}</span>}
              </NavLink>
            )

            if (isCollapsed) {
              return (
                <Tooltip key={item.to}>
                  <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                </Tooltip>
              )
            }

            return linkContent
          })}
        </TooltipProvider>
      </nav>
    </aside>
  )
}

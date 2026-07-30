import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react"
import { useState } from "react"

type SortDirection = "asc" | "desc"

interface UseTableSortOptions<T extends string> {
  defaultSortKey: T
  defaultSortDirection?: SortDirection
}

export function useTableSort<T extends string>(options: UseTableSortOptions<T>) {
  const { defaultSortKey, defaultSortDirection = "desc" } = options

  const [sortKey, setSortKey] = useState<T>(defaultSortKey)
  const [sortDirection, setSortDirection] = useState<SortDirection>(defaultSortDirection)

  const handleSort = (key: T) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortKey(key)
      setSortDirection(defaultSortDirection)
    }
  }

  const getSortIcon = (key: T) => {
    if (sortKey !== key) {
      return <ArrowUpDown className="ml-1 h-4 w-4" />
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="ml-1 h-4 w-4" />
    ) : (
      <ArrowDown className="ml-1 h-4 w-4" />
    )
  }

  return {
    sortKey,
    sortDirection,
    handleSort,
    getSortIcon,
  }
}

import {
  CircleDollarSign,
  Database,
  FileUp,
  History,
  LayoutDashboard,
  Receipt,
  Scissors,
  TrendingUp,
} from "lucide-react"

export const navItems = [
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
    to: "/portfolio-history",
    label: "資産推移",
    icon: History,
  },
  {
    to: "/transactions",
    label: "取引履歴",
    icon: Receipt,
  },
  {
    to: "/transactions/import",
    label: "CSVインポート",
    icon: FileUp,
  },
  {
    to: "/dividends",
    label: "配当金履歴",
    icon: CircleDollarSign,
  },
  {
    to: "/stock-splits",
    // 閲覧のみの「〜履歴」と区別するため、登録もできるこのページは「履歴」を付けない
    label: "株式分割",
    icon: Scissors,
  },
  {
    to: "/stocks",
    label: "銘柄マスター",
    icon: Database,
  },
]

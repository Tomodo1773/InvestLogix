import { Dashboard } from "@/components/dashboard/dashboard"
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout"

export default function Home() {
  return (
    <AuthenticatedLayout>
      <Dashboard />
    </AuthenticatedLayout>
  )
}

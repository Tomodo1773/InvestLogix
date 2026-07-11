import { useEffect, useMemo, useState } from "react"

interface UsePaginationResult<T> {
  currentPage: number
  totalPages: number
  paginatedData: T[]
  handlePageChange: (page: number) => void
  hasNextPage: boolean
  hasPreviousPage: boolean
}

interface UsePaginationOptions {
  scrollToTop?: boolean
}

export function usePagination<T>(
  data: T[] | undefined,
  pageSize: number,
  { scrollToTop = true }: UsePaginationOptions = {}
): UsePaginationResult<T> {
  const [currentPage, setCurrentPage] = useState(1)

  // データが undefined の場合は空配列として扱う
  const safeData = data ?? []

  // 総ページ数を計算
  const totalPages = Math.max(1, Math.ceil(safeData.length / pageSize))

  // データ件数が変わった際、現在ページが範囲外なら1ページ目に戻る
  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(1)
    }
  }, [currentPage, totalPages])

  // 現在のページのデータをスライス
  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize
    const endIndex = startIndex + pageSize
    return safeData.slice(startIndex, endIndex)
  }, [safeData, currentPage, pageSize])

  // ページ変更ハンドラー
  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page)
      if (scrollToTop) {
        window.scrollTo(0, 0)
      }
    }
  }

  // 前後のページが存在するかどうか
  const hasNextPage = currentPage < totalPages
  const hasPreviousPage = currentPage > 1

  return {
    currentPage,
    totalPages,
    paginatedData,
    handlePageChange,
    hasNextPage,
    hasPreviousPage,
  }
}

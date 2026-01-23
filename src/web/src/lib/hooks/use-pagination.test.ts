import { act, renderHook } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { usePagination } from "./use-pagination"

// window.scrollToのモック
const scrollToMock = vi.fn()

beforeEach(() => {
  Object.defineProperty(window, "scrollTo", {
    value: scrollToMock,
    writable: true,
  })
})

afterEach(() => {
  scrollToMock.mockClear()
})

describe("usePagination", () => {
  const testData = Array.from({ length: 25 }, (_, i) => ({ id: i + 1 }))

  it("データを正しくページ分割できる", () => {
    const { result } = renderHook(() => usePagination(testData, 10))
    expect(result.current.paginatedData).toHaveLength(10)
    expect(result.current.paginatedData[0]).toEqual({ id: 1 })
  })

  it("currentPageの初期値が1であること", () => {
    const { result } = renderHook(() => usePagination(testData, 10))
    expect(result.current.currentPage).toBe(1)
  })

  it("totalPagesが正しく計算されること", () => {
    const { result } = renderHook(() => usePagination(testData, 10))
    expect(result.current.totalPages).toBe(3) // 25件 / 10件 = 3ページ
  })

  it("paginatedDataが現在ページのデータのみを含むこと", () => {
    const { result } = renderHook(() => usePagination(testData, 10))

    expect(result.current.paginatedData).toHaveLength(10)
    expect(result.current.paginatedData[0]).toEqual({ id: 1 })
    expect(result.current.paginatedData[9]).toEqual({ id: 10 })
  })

  it("handlePageChangeでページを切り替えられること", () => {
    const { result } = renderHook(() => usePagination(testData, 10))

    act(() => {
      result.current.handlePageChange(2)
    })

    expect(result.current.currentPage).toBe(2)
    expect(result.current.paginatedData).toHaveLength(10)
    expect(result.current.paginatedData[0]).toEqual({ id: 11 })
    expect(scrollToMock).toHaveBeenCalledWith(0, 0)
  })

  it("hasNextPage / hasPreviousPageが正しく判定されること", () => {
    const { result } = renderHook(() => usePagination(testData, 10))

    // 1ページ目
    expect(result.current.hasNextPage).toBe(true)
    expect(result.current.hasPreviousPage).toBe(false)

    // 2ページ目に移動
    act(() => {
      result.current.handlePageChange(2)
    })
    expect(result.current.hasNextPage).toBe(true)
    expect(result.current.hasPreviousPage).toBe(true)

    // 3ページ目に移動
    act(() => {
      result.current.handlePageChange(3)
    })
    expect(result.current.hasNextPage).toBe(false)
    expect(result.current.hasPreviousPage).toBe(true)
  })

  it("undefinedの場合に空配列を返すこと", () => {
    const { result } = renderHook(() => usePagination(undefined, 10))
    expect(result.current.paginatedData).toEqual([])
    expect(result.current.totalPages).toBe(1)
  })

  it("ページ範囲外へのアクセスを防止できること", () => {
    const { result } = renderHook(() => usePagination(testData, 10))

    // 範囲外のページ番号を指定しても変更されない
    act(() => {
      result.current.handlePageChange(10)
    })
    expect(result.current.currentPage).toBe(1)

    act(() => {
      result.current.handlePageChange(0)
    })
    expect(result.current.currentPage).toBe(1)

    act(() => {
      result.current.handlePageChange(-1)
    })
    expect(result.current.currentPage).toBe(1)
  })
})

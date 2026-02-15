import { renderHook } from "@testing-library/react"
import { act } from "react"
import { describe, expect, it } from "vitest"
import { useTableSort } from "./use-table-sort"

type TestSortKey = "name" | "age" | "email"

describe("useTableSort", () => {
  it("デフォルト値で初期化されること", () => {
    const { result } = renderHook(() =>
      useTableSort<TestSortKey>({
        defaultSortKey: "name",
        defaultSortDirection: "asc",
      })
    )

    expect(result.current.sortKey).toBe("name")
    expect(result.current.sortDirection).toBe("asc")
  })

  it("デフォルト方向を省略した場合descになること", () => {
    const { result } = renderHook(() =>
      useTableSort<TestSortKey>({
        defaultSortKey: "name",
      })
    )

    expect(result.current.sortDirection).toBe("desc")
  })

  it("同じキーでソートを切り替えると方向が反転すること", () => {
    const { result } = renderHook(() =>
      useTableSort<TestSortKey>({
        defaultSortKey: "name",
        defaultSortDirection: "asc",
      })
    )

    expect(result.current.sortDirection).toBe("asc")

    // 同じキーでソート
    act(() => {
      result.current.handleSort("name")
    })

    expect(result.current.sortKey).toBe("name")
    expect(result.current.sortDirection).toBe("desc")

    // もう一度同じキーでソート
    act(() => {
      result.current.handleSort("name")
    })

    expect(result.current.sortKey).toBe("name")
    expect(result.current.sortDirection).toBe("asc")
  })

  it("異なるキーでソートするとデフォルト方向にリセットされること", () => {
    const { result } = renderHook(() =>
      useTableSort<TestSortKey>({
        defaultSortKey: "name",
        defaultSortDirection: "desc",
      })
    )

    expect(result.current.sortKey).toBe("name")
    expect(result.current.sortDirection).toBe("desc")

    // 異なるキーでソート
    act(() => {
      result.current.handleSort("age")
    })

    expect(result.current.sortKey).toBe("age")
    expect(result.current.sortDirection).toBe("desc") // デフォルト方向にリセット
  })

  it("getSortIconが現在のソート状態に応じたアイコンを返すこと", () => {
    const { result } = renderHook(() =>
      useTableSort<TestSortKey>({
        defaultSortKey: "name",
        defaultSortDirection: "asc",
      })
    )

    // 選択中のキーで昇順の場合、ArrowUpを返す
    const nameIconAsc = result.current.getSortIcon("name")
    expect(nameIconAsc.type.displayName).toBe("ArrowUp")

    // 選択されていないキーの場合、ArrowUpDownを返す
    const ageIcon = result.current.getSortIcon("age")
    expect(ageIcon.type.displayName).toBe("ArrowUpDown")

    // ソート方向を降順に変更
    act(() => {
      result.current.handleSort("name")
    })

    // 選択中のキーで降順の場合、ArrowDownを返す
    const nameIconDesc = result.current.getSortIcon("name")
    expect(nameIconDesc.type.displayName).toBe("ArrowDown")
  })
})

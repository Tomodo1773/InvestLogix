import { beforeEach, describe, expect, it } from "vitest"
import { useSidebarStore } from "./sidebar-store"

describe("useSidebarStore", () => {
  beforeEach(() => {
    // テスト間で状態をリセット
    useSidebarStore.setState({
      isCollapsed: false,
    })
    // localStorage をクリア
    localStorage.clear()
  })

  it("初期状態でisCollapsedがfalseであること", () => {
    const state = useSidebarStore.getState()
    expect(state.isCollapsed).toBe(false)
  })

  it("toggle()で状態が切り替わること", () => {
    // 初期状態を確認
    expect(useSidebarStore.getState().isCollapsed).toBe(false)

    // トグル実行
    useSidebarStore.getState().toggle()
    expect(useSidebarStore.getState().isCollapsed).toBe(true)

    // 再度トグル実行
    useSidebarStore.getState().toggle()
    expect(useSidebarStore.getState().isCollapsed).toBe(false)
  })

  it("複数回toggle()しても正しく動作すること", () => {
    const { toggle } = useSidebarStore.getState()

    // false -> true -> false -> true
    toggle()
    expect(useSidebarStore.getState().isCollapsed).toBe(true)

    toggle()
    expect(useSidebarStore.getState().isCollapsed).toBe(false)

    toggle()
    expect(useSidebarStore.getState().isCollapsed).toBe(true)
  })

  it("状態がlocalStorageに永続化されること", () => {
    // トグルして状態を変更
    useSidebarStore.getState().toggle()
    expect(useSidebarStore.getState().isCollapsed).toBe(true)

    // localStorageに保存されていることを確認
    const stored = localStorage.getItem("sidebar-storage")
    expect(stored).toBeTruthy()

    // 保存された値を確認
    const parsedStored = JSON.parse(stored!)
    expect(parsedStored.state.isCollapsed).toBe(true)
  })
})

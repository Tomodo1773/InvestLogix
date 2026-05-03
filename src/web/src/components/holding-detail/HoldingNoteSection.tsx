import { Pencil } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { updateHoldingNote } from "@/lib/api/client"

const NOTE_MAX_LENGTH = 2000

interface HoldingNoteSectionProps {
  symbol: string
  note: string | null
  isLoading: boolean
  onSaved: () => void
}

export function HoldingNoteSection({ symbol, note, isLoading, onSaved }: HoldingNoteSectionProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [draft, setDraft] = useState(note ?? "")
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const startEdit = () => {
    setDraft(note ?? "")
    setError(null)
    setIsEditing(true)
  }

  const cancelEdit = () => {
    setIsEditing(false)
    setError(null)
  }

  const handleSave = async () => {
    setIsSaving(true)
    setError(null)
    try {
      const trimmed = draft.trim()
      await updateHoldingNote(symbol, trimmed === "" ? null : draft)
      setIsEditing(false)
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存に失敗しました")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>メモ</CardTitle>
        {!isEditing && !isLoading && (
          <Button variant="outline" size="sm" onClick={startEdit}>
            <Pencil className="h-4 w-4 mr-1" />
            編集
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="h-20 w-full animate-pulse rounded bg-muted" />
        ) : isEditing ? (
          <div className="space-y-2">
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              maxLength={NOTE_MAX_LENGTH}
              rows={6}
              placeholder="この銘柄を買っている理由や注目ポイントなど"
              disabled={isSaving}
            />
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>
                {draft.length} / {NOTE_MAX_LENGTH}
              </span>
              {error && <span className="text-destructive">{error}</span>}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={cancelEdit} disabled={isSaving}>
                キャンセル
              </Button>
              <Button size="sm" onClick={handleSave} disabled={isSaving}>
                保存
              </Button>
            </div>
          </div>
        ) : note ? (
          <p className="whitespace-pre-wrap text-sm">{note}</p>
        ) : (
          <p className="text-sm text-muted-foreground">メモは未登録です</p>
        )}
      </CardContent>
    </Card>
  )
}

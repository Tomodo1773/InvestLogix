import { Upload } from "lucide-react"
import type * as React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface CsvUploadFormProps {
  onFileSelect: (file: File) => void
  isLoading: boolean
  inputId?: string
}

export function CsvUploadForm({ onFileSelect, isLoading, inputId = "csv-file" }: CsvUploadFormProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedFile) {
      onFileSelect(selectedFile)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor={inputId}>CSVファイル</Label>
        <Input
          id={inputId}
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          disabled={isLoading}
          className="cursor-pointer"
        />
        <p className="text-sm text-muted-foreground">
          SBI証券からエクスポートした取引履歴CSVをアップロードしてください（最大1MB）
        </p>
      </div>

      <Button type="submit" disabled={!selectedFile || isLoading} className="w-full">
        {isLoading ? (
          <>
            <Upload className="mr-2 h-4 w-4 animate-spin" />
            アップロード中...
          </>
        ) : (
          <>
            <Upload className="mr-2 h-4 w-4" />
            プレビューを表示
          </>
        )}
      </Button>
    </form>
  )
}

import { AlertCircle, CheckCircle2, Upload } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router"
import { AuthProvider } from "@/components/AuthProvider"
import { AppLayout } from "@/components/layout/app-layout"
import { CsvUploadForm } from "@/components/transactions/csv-upload-form"
import { ImportPreviewTable } from "@/components/transactions/import-preview-table"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { confirmImport, uploadCsvForPreview } from "@/lib/api/client"
import type { CsvTransactionPreview, ImportPreviewResponse } from "@/lib/api/types"
import { useAuthStore } from "@/lib/stores/auth-store"

type Step = "upload" | "preview" | "complete"

function TransactionImportContent() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const [step, setStep] = useState<Step>("upload")
  const [isLoading, setIsLoading] = useState(false)
  const [previewData, setPreviewData] = useState<ImportPreviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ created: number; failed: number; errors: string[] } | null>(null)

  const handleFileSelect = async (file: File) => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await uploadCsvForPreview(file)
      setPreviewData(response)
      setStep("preview")
    } catch (err) {
      setError(err instanceof Error ? err.message : "アップロードに失敗しました")
    } finally {
      setIsLoading(false)
    }
  }

  const handleConfirm = async () => {
    if (!previewData || previewData.new_transactions.length === 0) {
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const transactions = previewData.new_transactions.map((tx: CsvTransactionPreview) => ({
        symbol: tx.symbol,
        transaction_type: tx.transaction_type,
        quantity: tx.quantity,
        price: tx.price,
        usd_price: tx.usd_price,
        account_type: tx.account_type,
        fee: tx.fee,
        tax: tx.tax,
        transaction_date: tx.transaction_date,
      }))

      const response = await confirmImport({ transactions })
      setResult({
        created: response.created_count,
        failed: response.failed_count,
        errors: response.errors,
      })
      setStep("complete")
    } catch (err) {
      setError(err instanceof Error ? err.message : "登録に失敗しました")
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setStep("upload")
    setPreviewData(null)
    setError(null)
    setResult(null)
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">CSVインポート</h1>
          <p className="text-muted-foreground mt-2">SBI証券の取引履歴CSVから取引を一括登録します</p>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>エラー</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {step === "upload" && (
          <Card className="max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                ステップ 1: ファイル選択
              </CardTitle>
              <CardDescription>
                SBI証券からエクスポートした取引履歴CSVをアップロードしてください
              </CardDescription>
            </CardHeader>
            <CardContent>
              <CsvUploadForm onFileSelect={handleFileSelect} isLoading={isLoading} />
            </CardContent>
          </Card>
        )}

        {step === "preview" && previewData && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>ステップ 2: プレビュー確認</CardTitle>
                <CardDescription>以下の取引が登録されます。内容を確認してください。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">CSVの総取引数</p>
                    <p className="text-2xl font-bold">{previewData.csv_total_count}件</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">既存の取引数</p>
                    <p className="text-2xl font-bold">{previewData.existing_count}件</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">新規登録数</p>
                    <p className="text-2xl font-bold text-primary">{previewData.new_transactions.length}件</p>
                  </div>
                </div>

                {previewData.errors.length > 0 && (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>スキップした取引: {previewData.skipped_count}件</AlertTitle>
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1 mt-2">
                        {previewData.errors.slice(0, 5).map((err, i) => (
                          <li key={`preview-error-${i}-${err.substring(0, 20)}`} className="text-sm">
                            {err}
                          </li>
                        ))}
                        {previewData.errors.length > 5 && (
                          <li className="text-sm text-muted-foreground">
                            ... 他 {previewData.errors.length - 5}件
                          </li>
                        )}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                <ImportPreviewTable
                  transactions={previewData.new_transactions}
                  onConfirm={handleConfirm}
                  isLoading={isLoading}
                />

                <Button variant="outline" onClick={handleReset} disabled={isLoading} className="w-full">
                  キャンセル
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {step === "complete" && result && (
          <Card className="max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                ステップ 3: 完了
              </CardTitle>
              <CardDescription>取引の登録が完了しました</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div>
                  <p className="text-sm text-muted-foreground">登録成功</p>
                  <p className="text-2xl font-bold text-green-600">{result.created}件</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">登録失敗</p>
                  <p className="text-2xl font-bold text-red-600">{result.failed}件</p>
                </div>
              </div>

              {result.errors.length > 0 && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>登録に失敗した取引</AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc list-inside space-y-1 mt-2">
                      {result.errors.map((err, i) => (
                        <li key={`result-error-${i}-${err.substring(0, 20)}`} className="text-sm">
                          {err}
                        </li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              <div className="flex gap-4">
                <Button asChild className="flex-1">
                  <Link to="/transactions">取引履歴を表示</Link>
                </Button>
                <Button variant="outline" onClick={handleReset} className="flex-1">
                  続けてインポート
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  )
}

export default function TransactionImport() {
  return (
    <AuthProvider>
      <TransactionImportContent />
    </AuthProvider>
  )
}

import { AlertCircle, CheckCircle2, Upload } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router"
import { DividendImportPreviewTable } from "@/components/dividends/dividend-import-preview-table"
import { CsvUploadForm } from "@/components/transactions/csv-upload-form"
import { ImportPreviewTable } from "@/components/transactions/import-preview-table"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  confirmDividendImport,
  confirmImport,
  uploadCsvForPreview,
  uploadDividendCsvForPreview,
} from "@/lib/api/client"
import type {
  CsvDividendPreview,
  CsvTransactionPreview,
  DividendImportPreviewResponse,
  ImportPreviewResponse,
} from "@/lib/api/types"

type Step = "upload" | "preview" | "complete"

export default function TransactionImport() {
  const buildErrorItems = (errors: string[]) => {
    const counts = new Map<string, number>()
    return errors.map((message) => {
      const occurrence = (counts.get(message) ?? 0) + 1
      counts.set(message, occurrence)
      return { key: `${message}-${occurrence}`, message }
    })
  }

  // 取引履歴インポート用ステート
  const [txStep, setTxStep] = useState<Step>("upload")
  const [txIsLoading, setTxIsLoading] = useState(false)
  const [txPreviewData, setTxPreviewData] = useState<ImportPreviewResponse | null>(null)
  const [txError, setTxError] = useState<string | null>(null)
  const [txResult, setTxResult] = useState<{ created: number; failed: number; errors: string[] } | null>(null)

  // 配当金インポート用ステート
  const [divStep, setDivStep] = useState<Step>("upload")
  const [divIsLoading, setDivIsLoading] = useState(false)
  const [divPreviewData, setDivPreviewData] = useState<DividendImportPreviewResponse | null>(null)
  const [divError, setDivError] = useState<string | null>(null)
  const [divResult, setDivResult] = useState<{ created: number; failed: number; errors: string[] } | null>(
    null
  )

  // 取引履歴インポートハンドラー
  const handleTxFileSelect = async (file: File) => {
    setTxIsLoading(true)
    setTxError(null)

    try {
      const response = await uploadCsvForPreview(file)
      setTxPreviewData(response)
      setTxStep("preview")
    } catch (err) {
      setTxError(err instanceof Error ? err.message : "アップロードに失敗しました")
    } finally {
      setTxIsLoading(false)
    }
  }

  const handleTxConfirm = async () => {
    if (!txPreviewData || txPreviewData.new_transactions.length === 0) {
      return
    }

    setTxIsLoading(true)
    setTxError(null)

    try {
      const transactions = txPreviewData.new_transactions.map((tx: CsvTransactionPreview) => ({
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
      setTxResult({
        created: response.created_count,
        failed: response.failed_count,
        errors: response.errors,
      })
      setTxStep("complete")
    } catch (err) {
      setTxError(err instanceof Error ? err.message : "登録に失敗しました")
    } finally {
      setTxIsLoading(false)
    }
  }

  const handleTxReset = () => {
    setTxStep("upload")
    setTxPreviewData(null)
    setTxError(null)
    setTxResult(null)
  }

  // 配当金インポートハンドラー
  const handleDivFileSelect = async (file: File) => {
    setDivIsLoading(true)
    setDivError(null)

    try {
      const response = await uploadDividendCsvForPreview(file)
      setDivPreviewData(response)
      setDivStep("preview")
    } catch (err) {
      setDivError(err instanceof Error ? err.message : "アップロードに失敗しました")
    } finally {
      setDivIsLoading(false)
    }
  }

  const handleDivConfirm = async () => {
    if (!divPreviewData || divPreviewData.new_dividends.length === 0) {
      return
    }

    setDivIsLoading(true)
    setDivError(null)

    try {
      const dividends = divPreviewData.new_dividends.map((div: CsvDividendPreview) => ({
        symbol: div.symbol,
        payment_date: div.payment_date,
        shares_owned: div.shares_owned,
        total_amount: div.total_amount,
        tax: 0, // 提供スクリプトと同様に0として登録
        fee: 0,
      }))

      const response = await confirmDividendImport({ dividends })
      setDivResult({
        created: response.created_count,
        failed: response.failed_count,
        errors: response.errors,
      })
      setDivStep("complete")
    } catch (err) {
      setDivError(err instanceof Error ? err.message : "登録に失敗しました")
    } finally {
      setDivIsLoading(false)
    }
  }

  const handleDivReset = () => {
    setDivStep("upload")
    setDivPreviewData(null)
    setDivError(null)
    setDivResult(null)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">CSVインポート</h1>
        <p className="text-muted-foreground mt-2">SBI証券のCSVから取引履歴・配当金を一括登録します</p>
      </div>

      {/* 取引履歴インポートセクション */}
      <section className="space-y-6">
        <h2 className="text-xl font-semibold">取引履歴のインポート</h2>

        {txError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>エラー</AlertTitle>
            <AlertDescription>{txError}</AlertDescription>
          </Alert>
        )}

        {txStep === "upload" && (
          <Card className="max-w-2xl">
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
              <CsvUploadForm
                onFileSelect={handleTxFileSelect}
                isLoading={txIsLoading}
                inputId="transaction-csv-file"
              />
            </CardContent>
          </Card>
        )}

        {txStep === "preview" && txPreviewData && (
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
                    <p className="text-2xl font-bold">{txPreviewData.csv_total_count}件</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">既存の取引数</p>
                    <p className="text-2xl font-bold">{txPreviewData.existing_count}件</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">新規登録数</p>
                    <p className="text-2xl font-bold text-primary">
                      {txPreviewData.new_transactions.length}件
                    </p>
                  </div>
                </div>

                {txPreviewData.errors.length > 0 && (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>スキップした取引: {txPreviewData.skipped_count}件</AlertTitle>
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1 mt-2">
                        {buildErrorItems(txPreviewData.errors.slice(0, 5)).map((item) => (
                          <li key={item.key} className="text-sm">
                            {item.message}
                          </li>
                        ))}
                        {txPreviewData.errors.length > 5 && (
                          <li className="text-sm text-muted-foreground">
                            ... 他 {txPreviewData.errors.length - 5}件
                          </li>
                        )}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                <ImportPreviewTable
                  transactions={txPreviewData.new_transactions}
                  onConfirm={handleTxConfirm}
                  isLoading={txIsLoading}
                />

                <Button variant="outline" onClick={handleTxReset} disabled={txIsLoading} className="w-full">
                  キャンセル
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {txStep === "complete" && txResult && (
          <Card className="max-w-2xl">
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
                  <p className="text-2xl font-bold text-green-600">{txResult.created}件</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">登録失敗</p>
                  <p className="text-2xl font-bold text-red-600">{txResult.failed}件</p>
                </div>
              </div>

              {txResult.errors.length > 0 && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>登録に失敗した取引</AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc list-inside space-y-1 mt-2">
                      {buildErrorItems(txResult.errors).map((item) => (
                        <li key={item.key} className="text-sm">
                          {item.message}
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
                <Button variant="outline" onClick={handleTxReset} className="flex-1">
                  続けてインポート
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </section>

      {/* 区切り線 */}
      <hr className="my-8" />

      {/* 配当金インポートセクション */}
      <section className="space-y-6">
        <h2 className="text-xl font-semibold">配当金のインポート</h2>

        {divError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>エラー</AlertTitle>
            <AlertDescription>{divError}</AlertDescription>
          </Alert>
        )}

        {divStep === "upload" && (
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                ステップ 1: ファイル選択
              </CardTitle>
              <CardDescription>
                SBI証券からエクスポートした配当金・分配金CSVをアップロードしてください
              </CardDescription>
            </CardHeader>
            <CardContent>
              <CsvUploadForm
                onFileSelect={handleDivFileSelect}
                isLoading={divIsLoading}
                inputId="dividend-csv-file"
              />
            </CardContent>
          </Card>
        )}

        {divStep === "preview" && divPreviewData && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>ステップ 2: プレビュー確認</CardTitle>
                <CardDescription>以下の配当金が登録されます。内容を確認してください。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">CSVの総配当数</p>
                    <p className="text-2xl font-bold">{divPreviewData.csv_total_count}件</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">既存の配当数</p>
                    <p className="text-2xl font-bold">{divPreviewData.existing_count}件</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">新規登録数</p>
                    <p className="text-2xl font-bold text-primary">{divPreviewData.new_dividends.length}件</p>
                  </div>
                </div>

                {divPreviewData.errors.length > 0 && (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>スキップした配当: {divPreviewData.skipped_count}件</AlertTitle>
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1 mt-2">
                        {buildErrorItems(divPreviewData.errors.slice(0, 5)).map((item) => (
                          <li key={item.key} className="text-sm">
                            {item.message}
                          </li>
                        ))}
                        {divPreviewData.errors.length > 5 && (
                          <li className="text-sm text-muted-foreground">
                            ... 他 {divPreviewData.errors.length - 5}件
                          </li>
                        )}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                <DividendImportPreviewTable
                  dividends={divPreviewData.new_dividends}
                  onConfirm={handleDivConfirm}
                  isLoading={divIsLoading}
                />

                <Button variant="outline" onClick={handleDivReset} disabled={divIsLoading} className="w-full">
                  キャンセル
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {divStep === "complete" && divResult && (
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
                ステップ 3: 完了
              </CardTitle>
              <CardDescription>配当金の登録が完了しました</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div>
                  <p className="text-sm text-muted-foreground">登録成功</p>
                  <p className="text-2xl font-bold text-green-600">{divResult.created}件</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">登録失敗</p>
                  <p className="text-2xl font-bold text-red-600">{divResult.failed}件</p>
                </div>
              </div>

              {divResult.errors.length > 0 && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>登録に失敗した配当</AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc list-inside space-y-1 mt-2">
                      {buildErrorItems(divResult.errors).map((item) => (
                        <li key={item.key} className="text-sm">
                          {item.message}
                        </li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              <div className="flex gap-4">
                <Button asChild className="flex-1">
                  <Link to="/dividends">配当金を表示</Link>
                </Button>
                <Button variant="outline" onClick={handleDivReset} className="flex-1">
                  続けてインポート
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  )
}

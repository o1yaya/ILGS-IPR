$ErrorActionPreference = 'Stop'
$inputDoc = 'D:\wlxy\ILGS-IPR_中文_统一方法与协议修订_20261015.docx'
$outputPdf = 'D:\PycharmProjects\PythonProject\ILGS_release-main\output\manuscript\unified_ipr_20261015\render\manuscript.pdf'
New-Item -ItemType Directory -Path (Split-Path -Parent $outputPdf) -Force | Out-Null
$wordApp = $null
$wordDoc = $null
try {
    $wordApp = New-Object -ComObject Word.Application
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = 0
    $wordDoc = $wordApp.Documents.Open($inputDoc, $false, $true)
    $wordDoc.Repaginate()
    $wordDoc.ExportAsFixedFormat($outputPdf, 17)
    Write-Output "PDF: $outputPdf"
    Write-Output "Pages: $($wordDoc.ComputeStatistics(2))"
} finally {
    if ($null -ne $wordDoc) {
        $wordDoc.Close(0)
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordDoc)
    }
    if ($null -ne $wordApp) {
        try { $wordApp.Quit() } catch {
            if (-not (Test-Path -LiteralPath $outputPdf)) { throw }
        }
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordApp)
    }
}

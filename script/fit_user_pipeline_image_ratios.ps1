param(
    [string]$Source = "D:\PycharmProjects\PythonProject\ILGS_release-main\outputs\pipeline_masks_20261010\ILGS_IPR_pipeline_masks_editable.svg",
    [string]$Destination = "D:\PycharmProjects\PythonProject\ILGS_release-main\outputs\pipeline_masks_20261010\ILGS_IPR_pipeline_user_edited_ratios.svg"
)

$ErrorActionPreference = "Stop"
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$doc = New-Object System.Xml.XmlDocument
$doc.PreserveWhitespace = $true
$doc.Load($Source)
$iprBefore = $doc.SelectSingleNode('//*[@id="ipr"]').OuterXml
Add-Type -AssemblyName System.Drawing

function Get-Element([string]$Id) {
    $element = $doc.SelectSingleNode('//*[@id="' + $Id + '"]')
    if ($null -eq $element) { throw "Missing SVG element: $Id" }
    return $element
}

function Set-Number($Element, [string]$Name, [double]$Value) {
    $Element.SetAttribute($Name, $Value.ToString("0.######", $culture))
}

function Set-Box([string]$Id, [double]$X, [double]$Y, [double]$Width, [double]$Height) {
    $element = Get-Element $Id
    Set-Number $element "x" $X
    Set-Number $element "y" $Y
    Set-Number $element "width" $Width
    Set-Number $element "height" $Height
}

function Get-ImageRatio([string]$Id) {
    $element = Get-Element $Id
    $href = $element.GetAttribute("href", "http://www.w3.org/1999/xlink")
    $bytes = [Convert]::FromBase64String($href.Substring($href.IndexOf(",") + 1))
    $stream = [System.IO.MemoryStream]::new($bytes, $false)
    try {
        $bitmap = [System.Drawing.Image]::FromStream($stream)
        try { return [double]$bitmap.Width / $bitmap.Height }
        finally { $bitmap.Dispose() }
    }
    finally { $stream.Dispose() }
}

function Fit-Image([string]$Id, [double]$CenterX, [double]$CenterY, [double]$MaxWidth, [double]$MaxHeight, [string]$Frame, [string]$ClipRect) {
    $ratio = Get-ImageRatio $Id
    $width = [Math]::Min($MaxWidth, $MaxHeight * $ratio)
    $height = $width / $ratio
    $x = $CenterX - $width / 2
    $y = $CenterY - $height / 2
    Set-Box $Id $x $y $width $height
    (Get-Element $Id).SetAttribute("preserveAspectRatio", "xMidYMid meet")
    if ($Frame) { Set-Box $Frame $x $y $width $height }
    if ($ClipRect) { Set-Box $ClipRect $x $y $width $height }
    return [PSCustomObject]@{Id=$Id;X=$x;Y=$y;Width=$width;Height=$height;Ratio=$ratio}
}

$changes = @()
$changes += Fit-Image "image24" 159 188.5 204 153 "rect24" "rect4"
Set-Number (Get-Element "text25") "y" 284

# Full label coordinates are 400 x 300. Use a uniform scale for every silhouette.
Set-Box "rect25" 57 292 204 153
Set-Box "rect32" 57 292 204 153
(Get-Element "g31").SetAttribute("transform", "translate(57 292) scale(0.51)")
Set-Number (Get-Element "text32") "y" 464

$changes += Fit-Image "image32" 159 540 204 136 "rect33" "rect6"
Set-Number (Get-Element "text33") "y" 631

$changes += Fit-Image "image69" 1059 281 402 340 "" ""
$changes += Fit-Image "image78" 1385 217 122 86 "rect78" "rect7"

# The target label illustration retains its chosen 320 x 200 crop with equal x/y scale.
$targetHeight = 122.0 / 1.6
$targetY = 217 - $targetHeight / 2
Set-Box "rect81" 1629 $targetY 122 $targetHeight
Set-Box "rect88" 1629 $targetY 122 $targetHeight
(Get-Element "g87").SetAttribute("transform", "translate(1615.65625 140.75) scale(0.38125)")

$changes += Fit-Image "image89" 1368 134 80 48 "rect90" ""
$changes += Fit-Image "image92" 1425 386 130 86 "rect92" "rect9"
$changes += Fit-Image "image94" 1425 562 130 72 "rect94" "rect10"
$changes += Fit-Image "image96" 1650 386 130 86 "rect96" "rect11"
$changes += Fit-Image "image98" 1650 562 130 72 "rect98" "rect12"

# Reattach the existing horizontal feeds to the new image edges.
$languageLeft = ($changes | Where-Object Id -eq "image92").X
$rgbLeft = ($changes | Where-Object Id -eq "image96").X
$feed = Get-Element "path102"
$feed.SetAttribute("d", ($feed.GetAttribute("d") -replace 'L\s*1352,394', ('L ' + ($languageLeft - 5).ToString("0.######", $culture) + ',394')))
$feed = Get-Element "path103"
$feed.SetAttribute("d", ($feed.GetAttribute("d") -replace 'L\s*1577,394', ('L ' + ($rgbLeft - 5).ToString("0.######", $culture) + ',394')))

if ($doc.SelectSingleNode('//*[@id="ipr"]').OuterXml -cne $iprBefore) {
    throw "The protected IPR column changed. Export aborted."
}
$doc.Save($Destination)

$report = [PSCustomObject]@{
    Source = $Source
    Destination = $Destination
    ProtectedIPRColumnUnchanged = $true
    ImageFits = $changes
}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath ($Destination -replace '\.svg$', '_checks.json') -Encoding UTF8
Write-Output $Destination
Write-Output "Verified: the user-edited IPR column is unchanged."

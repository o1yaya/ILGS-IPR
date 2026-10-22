param(
    [string]$Source = "D:\PycharmProjects\PythonProject\ILGS_release-main\outputs\pipeline_masks_20261010\ILGS_IPR_pipeline_user_edited_ratios.svg",
    [string]$Destination = "D:\PycharmProjects\PythonProject\ILGS_release-main\outputs\pipeline_masks_20261010\ILGS_IPR_pipeline_compact_final.svg"
)

$ErrorActionPreference = "Stop"
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$doc = New-Object System.Xml.XmlDocument
$doc.PreserveWhitespace = $true
$doc.Load($Source)
$svgNamespace = "http://www.w3.org/2000/svg"
$iprBefore = $doc.SelectSingleNode('//*[@id="ipr"]').OuterXml

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
function Shift-Elements([string[]]$Ids, [double]$Dx) {
    foreach ($id in $Ids) {
        $element = Get-Element $id
        foreach ($attribute in @("x", "cx")) {
            if ($element.HasAttribute($attribute)) {
                Set-Number $element $attribute ([double]::Parse($element.GetAttribute($attribute), $culture) + $Dx)
            }
        }
    }
}
function Set-Path([string]$Id, [string]$D) {
    (Get-Element $Id).SetAttribute("d", $D)
}

Set-Number $doc.DocumentElement "width" 1600
$doc.DocumentElement.SetAttribute("viewBox", "0 0 1600 700")
Set-Box "rect13" 0 0 1600 700
Set-Box "rect16" 834 42 350 616
Set-Box "rect17" 1199 42 377 616

# Correct the input label frame locally; keep the IPR masks untouched.
(Get-Element "rect25").SetAttribute("rx", "4")
$backing = $doc.CreateElement("rect", $svgNamespace)
$backing.SetAttribute("id", "input-label-backing")
$backing.SetAttribute("width", "400")
$backing.SetAttribute("height", "300")
$backing.SetAttribute("fill", "#5ee0cb")
$null = (Get-Element "g31").PrependChild($backing)
$edgeRepair = $doc.CreateElement("rect", $svgNamespace)
$edgeRepair.SetAttribute("id", "input-label-top-edge-repair")
$edgeRepair.SetAttribute("width", "400")
$edgeRepair.SetAttribute("height", "6")
$edgeRepair.SetAttribute("fill", "#5ee0cb")
$null = (Get-Element "g31").AppendChild($edgeRepair)

Shift-Elements @("image69", "text70") -50
Shift-Elements @("circle22", "text23", "text24") -100
Set-Box "rect70" 848 503 322 94
Set-Box "rect71" 849 504 107 92
Set-Box "rect72" 956 504 107 92
Set-Box "rect73" 1063 504 106 92
Set-Number (Get-Element "text73") "x" 902.5
Set-Number (Get-Element "text74") "x" 1009.5
Set-Number (Get-Element "text75") "x" 1116.5
Set-Number (Get-Element "text76") "x" 902.5
Set-Number (Get-Element "text77") "x" 1009.5
Set-Number (Get-Element "text78") "x" 1116.5
(Get-Element "text78").SetAttribute("style", "font-size:9.5px")

# Identity supervision: fit three blocks into the narrower final column.
Set-Box "image78" 1216 185.884683 100 62.230634
Set-Box "rect78" 1216 185.884683 100 62.230634
Set-Box "rect7" 1216 185.884683 100 62.230634
Set-Number (Get-Element "text79") "x" 1266
Set-Number (Get-Element "text79") "y" 273
Set-Box "rect79" 1334 187 96 64
Set-Number (Get-Element "text80") "x" 1382
Set-Number (Get-Element "text81") "x" 1382
Set-Box "rect81" 1452 185.75 100 62.5
Set-Box "rect88" 1452 185.75 100 62.5
(Get-Element "g87").SetAttribute("transform", "translate(1441.0625 154.5) scale(0.3125)")
Set-Number (Get-Element "text88") "x" 1502
Set-Number (Get-Element "text88") "y" 273
Set-Path "path88" "M1316 217H1331"
Set-Path "path89" "M1452 217H1433"

Shift-Elements @("rect89", "image89", "rect90", "text90", "text91") -104
Set-Path "path91" "M1382 134V178"

# Translate the branch content uniformly, including the referenced clipping rectangles.
Shift-Elements @("text92", "image92", "rect92", "text93", "rect93", "text94", "image94", "rect94", "text95", "rect9", "rect10") -126
Shift-Elements @("text96", "image96", "rect96", "text97", "rect97", "text98", "image98", "rect98", "text99", "rect11", "rect12") -170
Set-Box "rect91" 1216 303 166 313
Set-Box "rect95" 1397 303 166 313
Set-Path "path94" "m 1299.4884,521.90033 v -7.03995"
Set-Path "path106" "m 1300.309,452.97658 v 4.84261"
Set-Path "path97" "m 1480,453.9534 v 4.84261"
Set-Path "path98" "m 1480.9768,520.81004 v -6.54661"

Set-Path "path101" "M1170 550H1188V217H1211"
Set-Path "path102" "M1188 300H1204V394H1244.515873"
Set-Path "path103" "M1204 300H1391V394H1417.666667"
Set-Number (Get-Element "text103") "y" 1176
Set-Path "path104" "M337 404H320V98H1502V177"
Set-Path "path105" "M791 428H820V626H1562V285.95856H1382V258.23715"
Shift-Elements @("rect104", "text104", "rect105", "text105") -100

if ($doc.SelectSingleNode('//*[@id="ipr"]').OuterXml -cne $iprBefore) {
    throw "The protected IPR column changed. Export aborted."
}
$doc.Save($Destination)
Write-Output $Destination
Write-Output "Canvas: 1600 x 700; protected IPR column unchanged."

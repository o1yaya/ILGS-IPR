param(
    [string]$Source = "D:\PycharmProjects\PythonProject\ILGS_release-main\outputs\pipeline_masks_20261010\ILGS_IPR_pipeline_compact_final.svg",
    [string]$Destination = "D:\PycharmProjects\PythonProject\ILGS_release-main\outputs\pipeline_masks_20261010\ILGS_IPR_pipeline_official_loss_style.svg"
)
$ErrorActionPreference = "Stop"
$culture = [System.Globalization.CultureInfo]::InvariantCulture
$doc = New-Object System.Xml.XmlDocument
$doc.PreserveWhitespace = $true
$doc.Load($Source)
$protected = @{}
foreach ($id in @("inputs", "ipr", "gaussian")) {
    $protected[$id] = $doc.SelectSingleNode('//*[@id="' + $id + '"]').OuterXml
}
function Element([string]$Id) {
    $node = $doc.SelectSingleNode('//*[@id="' + $Id + '"]')
    if ($null -eq $node) { throw "Missing SVG element $Id" }
    return $node
}
function Number($Node, [string]$Name, [double]$Value) {
    $Node.SetAttribute($Name, $Value.ToString("0.######", $culture))
}
function Box([string]$Id, [double]$X, [double]$Y, [double]$W, [double]$H) {
    $node = Element $Id
    Number $node "x" $X
    Number $node "y" $Y
    Number $node "width" $W
    Number $node "height" $H
}
function Caption([string]$Id, [double]$X, [double]$Y) {
    Number (Element $Id) "x" $X
    Number (Element $Id) "y" $Y
}
function Path([string]$Id, [string]$D) { (Element $Id).SetAttribute("d", $D) }

# Replace only the optimization presentation; retain embedded images and user edits.
foreach ($id in @("rect79", "text80", "text81", "path88", "path89", "rect91", "text92", "rect93", "text94", "path94", "rect95", "text96", "path97", "rect97", "text98", "path98", "path106")) {
    $node = Element $id
    $null = $node.ParentNode.RemoveChild($node)
}

Box "image92" 1216.515873 341 98.968254 86
Box "rect92" 1216.515873 341 98.968254 86
Box "rect9" 1216.515873 341 98.968254 86
Caption "text93" 1266 447
Box "image94" 1466 350.955 100 66.09
Box "rect94" 1466 350.955 100 66.09
Box "rect10" 1466 350.955 100 66.09
Caption "text95" 1516 447

Box "image96" 1216 510 100 75
Box "rect96" 1216 510 100 75
Box "rect11" 1216 510 100 75
Caption "text97" 1266 606
Box "image98" 1466 510 100 75
Box "rect98" 1466 510 100 75
Box "rect12" 1466 510 100 75
Caption "text99" 1516 606

$fragment = $doc.CreateDocumentFragment()
$fragment.InnerXml = @'
<g xmlns="http://www.w3.org/2000/svg" id="official-loss-glyphs">
  <g id="identity-loss-glyph">
    <rect x="1354" y="172" width="76" height="36" rx="3" fill="#ffffff" stroke="#202020" stroke-width="1.8"/>
    <text font-family="Times New Roman, serif" font-size="23" fill="#111111"><tspan x="1365" y="198" font-style="italic">L</tspan><tspan x="1379" y="204" font-size="13" font-style="normal">cls</tspan><tspan x="1395" y="184" font-size="12" font-style="normal">IPR</tspan></text>
    <path d="M1324 217H1458" fill="none" stroke="#db2634" stroke-width="2"/>
    <path d="M1317 217L1325 213V221Z M1465 217L1457 213V221Z" fill="#db2634"/>
  </g>
  <g id="language-loss-glyph">
    <rect x="1370" y="337" width="44" height="34" rx="3" fill="#ffffff" stroke="#202020" stroke-width="1.8"/>
    <text font-family="Times New Roman, serif" font-size="23" fill="#111111"><tspan x="1380" y="362" font-style="italic">L</tspan><tspan x="1394" y="368" font-size="14" font-style="normal">1</tspan></text>
    <path d="M1324 384H1458" fill="none" stroke="#db2634" stroke-width="2"/>
    <path d="M1317 384L1325 380V388Z M1465 384L1457 380V388Z" fill="#db2634"/>
  </g>
  <g id="rgb-l1-loss-glyph">
    <rect x="1370" y="498" width="44" height="32" rx="3" fill="#ffffff" stroke="#202020" stroke-width="1.8"/>
    <text font-family="Times New Roman, serif" font-size="23" fill="#111111"><tspan x="1380" y="522" font-style="italic">L</tspan><tspan x="1394" y="528" font-size="14" font-style="normal">1</tspan></text>
    <path d="M1324 536H1458" fill="none" stroke="#db2634" stroke-width="2"/>
    <path d="M1317 536L1325 532V540Z M1465 536L1457 532V540Z" fill="#db2634"/>
  </g>
  <g id="rgb-dssim-loss-glyph">
    <rect x="1347" y="546" width="90" height="32" rx="3" fill="#ffffff" stroke="#202020" stroke-width="1.8"/>
    <text font-family="Times New Roman, serif" font-size="23" fill="#111111"><tspan x="1355" y="569" font-style="italic">L</tspan><tspan x="1369" y="575" font-size="13" font-style="normal">D-SSIM</tspan></text>
    <path d="M1324 584H1458" fill="none" stroke="#db2634" stroke-width="2"/>
    <path d="M1317 584L1325 580V588Z M1465 584L1457 580V588Z" fill="#db2634"/>
  </g>
</g>
'@
foreach ($mathText in $fragment.SelectNodes('.//*[local-name()="text"]')) {
    $mathText.SetAttribute("style", "font-family:'Times New Roman',serif;font-weight:normal")
}
$null = (Element "optimization").AppendChild($fragment)

Path "path91" "M1383.9125 133.25249H1396V165"
Path "path102" "M1188 300H1204V384H1211"
Path "path103" "M1204 300V547.5H1211"
Path "path104" "M337 404H320V98H1516V177"
Path "path105" "M791 428H820V626H1570V285.95856H1447V190H1436"

foreach ($id in $protected.Keys) {
    if ((Element $id).OuterXml -cne $protected[$id]) { throw "Protected layer changed: $id" }
}
$doc.Save($Destination)
Write-Output $Destination
Write-Output "Verified: input, IPR and Gaussian layers unchanged."

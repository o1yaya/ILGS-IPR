param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$image = [System.Drawing.Bitmap]::FromFile($Source)
try {
    $crops = @{
        "clip_features.png" = [System.Drawing.Rectangle]::new(55, 527, 233, 154)
        "identity_labels.png" = [System.Drawing.Rectangle]::new(55, 334, 233, 145)
        "gaussian_field.png" = [System.Drawing.Rectangle]::new(742, 390, 270, 285)
        "language_feature.png" = [System.Drawing.Rectangle]::new(1248, 350, 145, 126)
        "outlier_mask.png" = [System.Drawing.Rectangle]::new(1784, 156, 141, 104)
        "ipr_cleanup.png" = [System.Drawing.Rectangle]::new(534, 164, 119, 96)
        "ipr_semantic.png" = [System.Drawing.Rectangle]::new(400, 314, 222, 107)
        "ipr_area.png" = [System.Drawing.Rectangle]::new(400, 480, 222, 99)
        "ipr_clean_labels.png" = [System.Drawing.Rectangle]::new(356, 625, 136, 77)
        "ipr_reliability.png" = [System.Drawing.Rectangle]::new(531, 625, 132, 77)
    }

    foreach ($name in $crops.Keys) {
        $crop = $image.Clone($crops[$name], $image.PixelFormat)
        try {
            $crop.Save(
                (Join-Path $OutputDir $name),
                [System.Drawing.Imaging.ImageFormat]::Png
            )
        }
        finally {
            $crop.Dispose()
        }
    }
}
finally {
    $image.Dispose()
}

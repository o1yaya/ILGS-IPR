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
        "blue_sofa_controlled_ilgs.png" = [System.Drawing.Rectangle]::new(1168, 485, 420, 315)
        "blue_sofa_ipr.png" = [System.Drawing.Rectangle]::new(1601, 485, 420, 315)
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

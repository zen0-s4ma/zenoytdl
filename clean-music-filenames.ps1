param(
    [Parameter(Mandatory = $true)]
    [string]$TargetDir
)

$ErrorActionPreference = "Stop"

function Normalize-Spaces {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $Text }
    $t = $Text -replace '\s+', ' '
    return $t.Trim()
}

function Clean-BaseName {
    param([string]$BaseName)

    $name = $BaseName

    $charsToDash = @(
        [char]0x2010,
        [char]0x2011,
        [char]0x2012,
        [char]0x2013,
        [char]0x2014,
        [char]0x2015
    )

    foreach ($ch in $charsToDash) {
        $name = $name.Replace([string]$ch, ' - ')
    }

    $patternsToRemove = @(
        '\[Video Oficial\]',
        '\[Official Video\]',
        '\[Official Audio\]',
        '\[Visualizer\]',
        '\[Audio Oficial\]',
        '\[Audio\]',
        '\[Letra\]',
        '\[Lyrics\]',
        '\[Lyric Video\]',
        '\(Video Oficial\)',
        '\(Official Video\)',
        '\(Official Audio\)',
        '\(Visualizer\)',
        '\(Audio Oficial\)',
        '\(Audio\)',
        '\(Letra\)',
        '\(Lyrics\)',
        '\(Lyric Video\)',
        '\(HD\)',
        '\(HQ\)',
        '\(Remastered(?: \d{4})?\)',
        '\(Remasterizado(?: \d{4})?\)',
        '\[Remastered(?: \d{4})?\]',
        '\[Remasterizado(?: \d{4})?\]',
        '\[Video Clip\]',
        '\(Video Clip\)'
    )

    foreach ($p in $patternsToRemove) {
        $name = [regex]::Replace($name, $p, '', 'IgnoreCase')
    }

    $name = [regex]::Replace($name, '\((?:Re)?coversi[oó]n\)', '', 'IgnoreCase')
    $name = [regex]::Replace($name, '\b(?:Re)?coversi[oó]n\b', '', 'IgnoreCase')
    $name = [regex]::Replace($name, '\bcover version\b', '', 'IgnoreCase')

    $name = $name -replace '\s*-\s*-\s*', ' - '
    $name = $name -replace '\s{2,}', ' '
    $name = $name -replace '\s*-\s*', ' - '

    $name = $name.Trim(" ", "-", ".", "_")

    return (Normalize-Spaces $name)
}

Get-ChildItem -LiteralPath $TargetDir -Filter *.mp3 -File | ForEach-Object {
    $oldName = $_.Name
    $base = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)
    $ext = $_.Extension

    $cleanBase = Clean-BaseName -BaseName $base

    if ([string]::IsNullOrWhiteSpace($cleanBase)) {
        Write-Host "SKIP VACIO: $oldName" -ForegroundColor DarkYellow
        return
    }

    $newName = "$cleanBase$ext"

    if ($newName -ne $oldName) {
        $destination = Join-Path $_.DirectoryName $newName
        if (Test-Path -LiteralPath $destination) {
            Write-Host "COLISION: $oldName --> $newName (ya existe)" -ForegroundColor Red
        }
        else {
            Rename-Item -LiteralPath $_.FullName -NewName $newName
            Write-Host "RENOMBRADO: $oldName  -->  $newName" -ForegroundColor Green
        }
    }
    else {
        Write-Host "OK: $oldName" -ForegroundColor Gray
    }
}
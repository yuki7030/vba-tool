# =====================================================================
# link-skills.ps1 — スキルをツール別ディレクトリへリンクする(冪等)
# 実行: powershell -ExecutionPolicy Bypass -File scripts\link-skills.ps1
#       [-Skills grilling,xlflow]   # 対象を絞る場合(省略時は LINK_SKILLS 全件)
# =====================================================================
# スキル実体は .github/skills/ に一元化し、各ツールのスキルディレクトリへは
# リンクを張る(実体をコピーすると更新が二重管理になり、片方が腐るため)。
#
# ディレクトリごとリンクせずスキル単位で張るのは、_domain-template のように
# name: 未記入のテンプレートまでスキルとして登録され、起動が不安定になるため。
param(
    [string[]]$Skills = @()
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Step($msg) { Write-Host "`n== $msg ==" -ForegroundColor Cyan }
function Info($msg) { Write-Host $msg -ForegroundColor Gray }
function Warn($msg) { Write-Host $msg -ForegroundColor Yellow }

# リンクを張るのは description のトリガ語で自動起動させたいスキルのみ。
# それ以外(vba-coding / code-review / agent-workflow 等)は AGENTS.md の
# 「詳細規約」節がパスで参照しており、該当タスク時に読み込まれるため不要。
$LINK_SKILLS = @("grilling", "grill-me", "reverse-vba", "xlflow",
                 "diagnosing-bugs", "writing-for-agents")

# リンク先ディレクトリ。.agents は xlflow init が作るため、存在する場合のみ張る。
$LINK_ROOTS = @(
    @{ Path = ".claude/skills"; Always = $true },
    @{ Path = ".agents/skills"; Always = $false }
)

function Set-SkillLink($LinkPath, $TargetPath, $RelativeTarget) {
    if (Test-Path $LinkPath) {
        $item = Get-Item $LinkPath -Force
        if ($item.LinkType) {
            Info "  skip : $LinkPath (リンク済み)"
            return
        }
        # 空ディレクトリだけ黙って置換する。中身のある実体は取り違えの可能性が
        # あるため、消さずに警告して人の判断に委ねる。
        if (Get-ChildItem $LinkPath -Force | Select-Object -First 1) {
            Warn "  SKIP : $LinkPath は中身のある実体ディレクトリ。手動で確認してください"
            return
        }
        Remove-Item $LinkPath -Force
    } else {
        New-Item -ItemType Directory -Force -Path (Split-Path $LinkPath -Parent) | Out-Null
    }
    try {
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            # Junction は管理者権限も開発者モードも不要なため Windows では優先する
            New-Item -ItemType Junction -Path $LinkPath -Value $TargetPath -ErrorAction Stop | Out-Null
        } else {
            New-Item -ItemType SymbolicLink -Path $LinkPath -Value $RelativeTarget -ErrorAction Stop | Out-Null
        }
        Info "  link : $LinkPath -> $RelativeTarget"
    } catch {
        Warn "  FAIL : $LinkPath のリンク作成に失敗: $_"
        return
    }
}

$targets = if ($Skills.Count -gt 0) { $Skills } else { $LINK_SKILLS }

Step "スキルリンク作成"
$missing = 0
foreach ($root in $LINK_ROOTS) {
    if (-not $root.Always -and -not (Test-Path $root.Path)) {
        Info "$($root.Path) は未作成のためスキップします"
        continue
    }
    Write-Host "$($root.Path):"
    foreach ($skill in $targets) {
        $source = ".github/skills/$skill"
        if (-not (Test-Path $source)) {
            Warn "  MISS : $source が見つかりません"
            $missing++
            continue
        }
        $depth = ($root.Path -split "/").Count
        $prefix = ("../" * $depth)
        Set-SkillLink "$($root.Path)/$skill" (Join-Path $RepoRoot $source) "$prefix.github/skills/$skill"
    }
}

if ($missing -gt 0) {
    Warn "`n実体の無いスキルが $missing 件あります。.github/skills/ を確認してください"
    exit 1
}
Info "`n完了。Claude Code を再起動するとスキルが認識されます"

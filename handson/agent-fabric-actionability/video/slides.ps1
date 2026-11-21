# テンプレートの pptx から、動画に挟むスライドを作って PNG に書き出す。文言は slides.json。
#   powershell -File slides.ps1 <テンプレート.pptx> <出力の pptx> <PNG を置くフォルダ> [文言の json] [PNG の幅]
# テンプレートは 1 表紙、2 区切り、3 白、4 締めの順の 4 枚。できるのは
#   表紙、白 (全体)、区切り + 白 をモジュールの数だけ、締め。PNG は 01.png から順に。
#   モジュールに items が無ければ、そのモジュールの白は作らない (イベント版 slides-booth.json)
#   overview.agenda が true なら、全体の白は番号付きのアジェンダにする
#   モジュールの items に 3 つ目 (ラボの id) があれば、ラボごとの区切り (「Lab 2-2」と名前と説明) を作る。
#   prep があれば、全体の白のあとに事前準備の区切りを作る。PNG の名前と番号の対応は index.json に書く
#   モジュールに features があれば、区切りのあとに機能ごとの「課題 → 解決」の白を作る
param([string]$Template, [string]$Out, [string]$PngDir, [string]$SpecFile = "slides.json", [int]$Width = 1920)
$ErrorActionPreference = "Stop"
# PowerPoint は相対パスを自分の作業フォルダから読むので、ここで絶対パスにする
function Abs([string]$path) { if ([IO.Path]::IsPathRooted($path)) { $path } else { Join-Path (Get-Location).Path $path } }
$Template = Abs $Template; $Out = Abs $Out; $PngDir = Abs $PngDir
$spec = Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot $SpecFile) | ConvertFrom-Json

$Navy = 0x602D03      # #032D60 (Office の RGB は BGR の順)
$Blue = 0xD27601      # #0176D3
$Gray = 0x5C5C5C
$JpFont = "Yu Gothic UI"

$pp = New-Object -ComObject PowerPoint.Application
$p = $pp.Presentations.Open($Template, $true, $false, $false)
try {
$p.SaveAs($Out)

function Set-Jp($range) { $range.Font.NameFarEast = $JpFont }

function Add-Para($tr, [string]$text, [double]$size, [int]$color, [bool]$bold, [double]$after) {
  if ($tr.Text.Length -gt 0) { $tr.InsertAfter("`r") | Out-Null }
  $r = $tr.InsertAfter($text)
  $r.Font.Size = $size; $r.Font.Color.RGB = $color; $r.Font.Bold = [int]$bold
  $r.ParagraphFormat.SpaceAfter = $after
  Set-Jp $r
}

# 白スライド: 上に見出し、下に導入の 1 文と「名前 / 説明」の組
function Fill-White($sl, $title, $lead, $items, [double]$size) {
  $t = $sl.Shapes | Where-Object { $_.Type -eq 14 } | Select-Object -First 1
  $t.TextFrame.TextRange.Text = $title
  $t.TextFrame.TextRange.Font.Color.RGB = $Navy
  Set-Jp $t.TextFrame.TextRange
  $box = $sl.Shapes.AddTextbox(1, 34, 82, 640, 300)
  $box.TextFrame.WordWrap = -1
  $tr = $box.TextFrame.TextRange
  Add-Para $tr $lead ($size + 1) $Gray $false 14
  foreach ($it in $items) {
    Add-Para $tr $it[0] $size $Blue $true 0
    Add-Para $tr $it[1] ($size - 1) $Navy $false 9
  }
}

function Set-Text($shape, [string]$text, [double]$size, [int]$color, [bool]$bold) {
  $tr = $shape.TextFrame.TextRange
  $tr.Text = $text
  $tr.Font.Size = $size; $tr.Font.Color.RGB = $color; $tr.Font.Bold = [int]$bold
  Set-Jp $tr
  $tr
}

function Set-Title($sl, [string]$title) {
  $t = $sl.Shapes | Where-Object { $_.Type -eq 14 } | Select-Object -First 1
  $t.TextFrame.TextRange.Text = $title
  $t.TextFrame.TextRange.Font.Color.RGB = $Navy
  Set-Jp $t.TextFrame.TextRange
}

# アジェンダ: 番号の丸、名前、説明を 1 行ずつ
function Fill-Agenda($sl, $title, $items) {
  Set-Title $sl $title
  for ($i = 0; $i -lt $items.Count; $i++) {
    $y = 96 + $i * 56
    $c = $sl.Shapes.AddShape(9, 40, $y, 34, 34)
    $c.Fill.ForeColor.RGB = $Blue; $c.Line.Visible = 0
    $r = Set-Text $c ("{0}" -f ($i + 1)) 16 0xFFFFFF $true
    $r.ParagraphFormat.Alignment = 2
    $n = $sl.Shapes.AddTextbox(1, 88, $y - 4, 560, 22)
    Set-Text $n $items[$i][0] 18 $Navy $true | Out-Null
    $d = $sl.Shapes.AddTextbox(1, 88, $y + 16, 560, 20)
    Set-Text $d $items[$i][1] 14 $Gray $false | Out-Null
  }
}

# 機能の紹介: 左に課題、右に解決。下に「このあと設定手順」
function Fill-Feature($sl, $f) {
  Set-Title $sl $f.name
  $boxes = @(
    @{ x = 34;  head = "課題";                   body = $f.problem;  fill = 0xE5F4FF; color = 0x017ADD },
    @{ x = 386; head = "Agent Fabric による解決"; body = $f.solution; fill = 0xFEF5EA; color = $Blue }
  )
  foreach ($b in $boxes) {
    $sh = $sl.Shapes.AddShape(5, $b.x, 92, 300, 222)
    $sh.Fill.ForeColor.RGB = $b.fill; $sh.Line.Visible = 0
    $sh.Adjustments.Item(1) = 0.06
    $tf = $sh.TextFrame
    $tf.VerticalAnchor = 1; $tf.WordWrap = -1
    $tf.MarginLeft = 18; $tf.MarginRight = 18; $tf.MarginTop = 16
    $tr = $tf.TextRange
    $tr.Text = ""
    Add-Para $tr $b.head 16 $b.color $true 10
    Add-Para $tr $b.body 18 $Navy $false 0
    $tr.ParagraphFormat.Alignment = 1
  }
  $ar = $sl.Shapes.AddShape(33, 342, 188, 36, 30)
  $ar.Fill.ForeColor.RGB = $Blue; $ar.Line.Visible = 0
  $nt = $sl.Shapes.AddTextbox(1, 34, 328, 650, 24)
  Set-Text $nt "このあと、実際の設定手順をご覧いただきます" 14 $Gray $false | Out-Null
}

$cover = $p.Slides.Item(1); $sec0 = $p.Slides.Item(2); $white0 = $p.Slides.Item(3); $thanks = $p.Slides.Item(4)

# 表紙: 日付の欄は消す。サブタイトルは slides.json の cover.subtitle が空なら欄ごと消す
$cover.Shapes.Item(3).Delete()
if ($spec.cover.subtitle) {
  $cover.Shapes.Item(2).TextFrame.TextRange.Text = $spec.cover.subtitle
  Set-Jp $cover.Shapes.Item(2).TextFrame.TextRange
} else { $cover.Shapes.Item(2).Delete() }

# ラボの区切り: モジュールの区切りと同じ配置で、見出しに「Lab 2-2  名前」、その下に説明
function New-LabSlide([string]$no, [string]$name, [string]$desc) {
  $sl = $sec0.Duplicate().Item(1)
  $sl.Shapes.Item(1).TextFrame.TextRange.Text = $(if ($name) { "$no  $name" } else { $no })
  Set-Jp $sl.Shapes.Item(1).TextFrame.TextRange
  $d = $sl.Shapes.AddTextbox(1, 62, 280, 520, 30)
  Set-Text $d $desc 16 $Blue $false | Out-Null
  $sl
}

$order = @($cover); $names = @('cover')
$ov = $white0.Duplicate().Item(1)
if ($spec.overview.agenda) { Fill-Agenda $ov $spec.overview.title $spec.overview.items }
else { Fill-White $ov $spec.overview.title $spec.overview.lead $spec.overview.items 15 }
$order += $ov; $names += 'overview'
if ($spec.prep) { $order += (New-LabSlide $spec.prep.title "" $spec.prep.desc); $names += ('lab-' + $spec.prep.id) }
foreach ($m in $spec.modules) {
  $sec = $sec0.Duplicate().Item(1)
  $sec.Shapes.Item(1).TextFrame.TextRange.Text = $m.title
  # ラボの名前は、パネルの中の見出しの下に小さく
  $sub = $sec.Shapes.AddTextbox(1, 62, 280, 520, 30)
  $sub.TextFrame.TextRange.Text = $m.labs
  $sub.TextFrame.TextRange.Font.Size = 16
  $sub.TextFrame.TextRange.Font.Color.RGB = $Blue
  Set-Jp $sub.TextFrame.TextRange
  $order += $sec; $names += $m.id
  foreach ($f in $m.features) {
    $fs = $white0.Duplicate().Item(1)
    Fill-Feature $fs $f
    $order += $fs; $names += ($m.id + '-feature')
  }
  if ($m.items) {
    $wh = $white0.Duplicate().Item(1)
    Fill-White $wh $m.title $m.lead $m.items 18
    $order += $wh; $names += ($m.id + '-white')
    foreach ($it in $m.items) {
      if ($it.Count -lt 3) { continue }
      $parts = $it[0] -split '\s{2,}', 2
      $order += (New-LabSlide $parts[0] $parts[1] $it[1]); $names += ('lab-' + $it[2])
    }
  }
}
$order += $thanks; $names += 'thanks'

# 締めの Thank you はレイアウトに 1 文字ずつ置いてあり、Avant Garde Demi SFDC が無いと
# 「Than k」と崩れる。この PC にあるフォントで 1 つの文字にし直す (出力のコピーだけ)
$tl = $thanks.CustomLayout
@($tl.Shapes | Where-Object { $_.HasTextFrame -and $_.TextFrame.TextRange.Font.Name -eq "Avant Garde Demi SFDC" }) | ForEach-Object { $_.Delete() }
$ty = $tl.Shapes.AddTextbox(1, 160, 100, 400, 210)
$ty.TextFrame.TextRange.Text = "Thank`vyou"
$ty.TextFrame.TextRange.Font.Name = "Century Gothic"
$ty.TextFrame.TextRange.Font.Bold = 1
$ty.TextFrame.TextRange.Font.Size = 96
$ty.TextFrame.TextRange.Font.Color.RGB = 0xFFFFFF
$ty.TextFrame.TextRange.ParagraphFormat.Alignment = 2
$ty.TextFrame.TextRange.ParagraphFormat.SpaceWithin = 0.85
$white0.Delete(); $sec0.Delete()
for ($i = 0; $i -lt $order.Count; $i++) { $order[$i].MoveTo($i + 1) }

# 講演用のノートは動画には要らないので消す
foreach ($s in $p.Slides) {
  foreach ($sh in $s.NotesPage.Shapes) {
    if ($sh.Type -eq 14 -and $sh.PlaceholderFormat.Type -eq 2) { $sh.TextFrame.TextRange.Text = "" }
  }
}
$p.Save()

New-Item -ItemType Directory -Force $PngDir | Out-Null
$n = 1
$index = [ordered]@{}
foreach ($s in $p.Slides) { $s.Export((Join-Path $PngDir ("{0:D2}.png" -f $n)), "PNG", $Width, [int]($Width * 9 / 16)); $index[$names[$n - 1]] = ("{0:D2}" -f $n); $n++ }
[IO.File]::WriteAllText((Join-Path $PngDir 'index.json'), ($index | ConvertTo-Json), (New-Object Text.UTF8Encoding $false))
"slides: $($n - 1)"
} finally {
  $p.Close()
  # ほかのプレゼンを開いていたら PowerPoint は閉じない
  if ($pp.Presentations.Count -eq 0) { $pp.Quit() }
}

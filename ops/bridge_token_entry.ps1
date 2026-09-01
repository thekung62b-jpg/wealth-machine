# Little Homie Bridge - secure GitHub token entry (LH-BROWSER-WEB-SEARCH-001)
#
# Opens a Windows dialog with a masked field and writes the value ONLY to the
# existing bridge credential location. The token is never echoed, logged,
# written to the repo, or placed in commands.json. It is held as a SecureString
# and the unmanaged buffer is zeroed immediately after the file write.

Add-Type -AssemblyName System.Windows.Forms, System.Drawing

$CredPath = "C:\OpenClawBridge\.github_token"

$form                 = New-Object System.Windows.Forms.Form
$form.Text            = "Little Homie Bridge GitHub Token"
$form.Size            = New-Object System.Drawing.Size(520, 210)
$form.StartPosition   = "CenterScreen"
$form.TopMost         = $true
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox     = $false
$form.MinimizeBox     = $false

$label          = New-Object System.Windows.Forms.Label
$label.Text     = "Little Homie Bridge GitHub Token`r`n" +
                  "Fine-grained - wealth-machine - Contents: Read and write"
$label.Location = New-Object System.Drawing.Point(15, 15)
$label.Size     = New-Object System.Drawing.Size(480, 40)
$form.Controls.Add($label)

$box                  = New-Object System.Windows.Forms.TextBox
$box.UseSystemPasswordChar = $true          # masked: never rendered on screen
$box.Location         = New-Object System.Drawing.Point(15, 65)
$box.Size             = New-Object System.Drawing.Size(480, 24)
$form.Controls.Add($box)

$hint          = New-Object System.Windows.Forms.Label
$hint.Text     = "Paste the token and press OK. It is stored only in $CredPath"
$hint.Location = New-Object System.Drawing.Point(15, 95)
$hint.Size     = New-Object System.Drawing.Size(480, 20)
$form.Controls.Add($hint)

$ok              = New-Object System.Windows.Forms.Button
$ok.Text         = "OK"
$ok.DialogResult = [System.Windows.Forms.DialogResult]::OK
$ok.Location     = New-Object System.Drawing.Point(300, 125)
$form.Controls.Add($ok)
$form.AcceptButton = $ok

$cancel              = New-Object System.Windows.Forms.Button
$cancel.Text         = "Cancel"
$cancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$cancel.Location     = New-Object System.Drawing.Point(400, 125)
$form.Controls.Add($cancel)
$form.CancelButton = $cancel

$form.Add_Shown({ $form.Activate(); $box.Focus() })
$result = $form.ShowDialog()

if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
    Write-Output "CANCELLED - credential unchanged"
    $form.Dispose(); exit 1
}

# Move the value into a SecureString, then clear the control immediately.
$secure = New-Object System.Security.SecureString
foreach ($c in $box.Text.ToCharArray()) { $secure.AppendChar($c) }
$secure.MakeReadOnly()
$box.Text = ""
$form.Dispose()

$dir = Split-Path -Parent $CredPath
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if ([string]::IsNullOrWhiteSpace($plain)) {
        Write-Output "EMPTY INPUT - credential unchanged"
        exit 1
    }
    Set-Content -Path $CredPath -Value $plain.Trim() -NoNewline -Encoding ascii
    $len  = $plain.Trim().Length
    $kind = if ($plain.StartsWith("github_pat_")) { "fine-grained" }
            elseif ($plain.StartsWith("ghp_"))    { "classic" }
            else                                  { "unrecognized" }
} finally {
    # zero the unmanaged buffer so the plaintext does not linger in memory
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    Remove-Variable plain -ErrorAction SilentlyContinue
}

# Restrict the file to the current user only.
icacls $CredPath /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null

# Report only non-secret facts.
Write-Output "STORED path=$CredPath length=$len kind=$kind"

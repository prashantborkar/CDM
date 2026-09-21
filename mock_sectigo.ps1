# Simple listener that mimics the Sectigo Certificate API on your laptop
$Listener = [System.Net.HttpListener]::New(); $Listener.Prefixes.Add("http://localhost:8080/sectigo/"); $Listener.Start()
Write-Host "Sectigo Mock API Engine running on http://localhost:8080/sectigo/ ..."
while ($Listener.IsListening) {
    $Context = $Listener.GetContext(); $Response = $Context.Response
    $MockCertificate = "-----BEGIN CERTIFICATE-----\nMOCK_SECTIGO_SANDBOX_CERTIFICATE_DATA_SUCCESS\n-----END CERTIFICATE-----"
    $Buffer = [System.Text.Encoding]::UTF8.GetBytes($MockCertificate)
    $Response.ContentLength64 = $Buffer.Length; $Response.OutputStream.Write($Buffer, 0, $Buffer.Length); $Response.Close()
}
